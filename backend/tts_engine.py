import os
import sys
import json
import time
import uuid
import asyncio
import urllib.request
import urllib.error
import subprocess
import edge_tts
import imageio_ffmpeg
from backend.utils import get_asset_path

class SaydiVoiceEngine:
    def __init__(self):
        self.token = None
        self.token_expiry = 0
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Content-Type': 'application/json',
            'Origin': 'https://voice.saydi.ai',
            'Referer': 'https://voice.saydi.ai/vi/studio/tts/'
        }

    def get_token(self):
        now = time.time()
        if self.token and (self.token_expiry - now) > 60:
            return self.token
        try:
            req = urllib.request.Request(
                'https://voice.saydi.ai/api/session/start',
                data=json.dumps({}).encode('utf-8'),
                headers=self.headers
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                self.token = data.get('token')
                expires_in = data.get('expires_in', 1800)
                self.token_expiry = now + expires_in
                return self.token
        except Exception as e:
            print(f"[SaydiEngine] Error getting session token: {e}")
            return None

    def synthesize(self, text, voice_sample, speed=1.0, output_path=None):
        token = self.get_token()
        if not token:
            raise RuntimeError("Không thể lấy token xác thực từ Saydi AI")

        auth_headers = dict(self.headers)
        auth_headers['Authorization'] = f'Bearer {token}'
        auth_headers['X-OV-Feature'] = 'tts'

        payload = {
            "text": text,
            "sample": voice_sample,
            "guidance_scale": 3.0,
            "speed": float(speed),
            "output_format": "mp3"
        }

        req = urllib.request.Request(
            'https://voice.saydi.ai/api/tts',
            data=json.dumps(payload).encode('utf-8'),
            headers=auth_headers
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Saydi API error: status {resp.status}")
            audio_bytes = resp.read()
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
            return audio_bytes

class WhiteboardTTSEngine:
    def __init__(self):
        self.temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "whiteboard_tts")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.saydi_engine = SaydiVoiceEngine()
        self.voices_data = []
        self.load_all_voices()

    def load_all_voices(self):
        voices_file = get_asset_path("saydi_voices.json")
        if os.path.exists(voices_file):
            try:
                with open(voices_file, "r", encoding="utf-8") as f:
                    self.voices_data = json.load(f)
            except Exception as e:
                print(f"Error loading voices json: {e}")

        if not self.voices_data:
            self.voices_data = [
                {"id": "turbo_namminh", "name": "Nam Minh (Siêu Tốc)", "voice_type": "turbo", "edge_id": "vi-VN-NamMinhNeural"},
                {"id": "turbo_hoaimy", "name": "Hoài My (Siêu Tốc)", "voice_type": "turbo", "edge_id": "vi-VN-HoaiMyNeural"},
                {"id": "turbo_adam", "name": "Adam (Siêu Tốc)", "voice_type": "turbo", "edge_id": "en-US-AndrewMultilingualNeural"}
            ]

    def get_audio_duration(self, audio_path: str) -> float:
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            cmd = [ffmpeg_exe, "-i", audio_path]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="ignore")
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    parts = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = parts.split(":")
                    return float(h) * 3600 + float(m) * 60 + float(s)
        except Exception as e:
            print(f"Error measuring audio duration: {e}")
        return 4.0

    async def _edge_synth(self, text: str, voice_id: str, rate: int = 0, pitch: int = 0, output_path: str = None) -> str:
        rate_str = f"{'+' if rate >= 0 else ''}{rate}%"
        pitch_str = f"{'+' if pitch >= 0 else ''}{pitch}Hz"
        communicate = edge_tts.Communicate(text=text, voice=voice_id, rate=rate_str, pitch=pitch_str)
        await communicate.save(output_path)
        return output_path

    def synthesize(self, text: str, voice_id: str = "turbo_namminh", rate: int = 0, pitch: int = 0, output_path: str = None) -> tuple[str, float]:
        if not text or not text.strip():
            raise ValueError("Văn bản phân cảnh không được để trống!")

        text = text.strip()
        if not output_path:
            output_path = os.path.join(self.temp_dir, f"wb_tts_{uuid.uuid4().hex[:8]}.mp3")

        v_info = None
        for v in self.voices_data:
            if v.get("id") == voice_id or v.get("name") == voice_id:
                v_info = v
                break

        if not v_info:
            v_info = self.voices_data[0]

        is_turbo = v_info.get("voice_type") == "turbo" or "Siêu Tốc" in v_info.get("name", "") or "turbo" in v_info.get("id", "").lower()

        if is_turbo:
            edge_id = v_info.get("edge_id")
            if not edge_id:
                if "hoaimy" in v_info.get("id", "").lower() or "nữ" in v_info.get("gender", "").lower():
                    edge_id = "vi-VN-HoaiMyNeural"
                elif "adam" in v_info.get("id", "").lower():
                    edge_id = "en-US-AndrewMultilingualNeural"
                else:
                    edge_id = "vi-VN-NamMinhNeural"

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._edge_synth(text, edge_id, rate, pitch, output_path))
            finally:
                loop.close()
        else:
            sample = v_info.get("sample") or v_info.get("id")
            try:
                self.saydi_engine.synthesize(text, sample, speed=1.0, output_path=output_path)
            except Exception as e:
                print(f"Saydi error: {e}. Falling back to Turbo Edge TTS...")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self._edge_synth(text, "vi-VN-NamMinhNeural", 0, 0, output_path))
                finally:
                    loop.close()

        dur = self.get_audio_duration(output_path)
        return output_path, dur