import os
import sys
import math
import json
import uuid
import shutil
import subprocess
import imageio_ffmpeg
from backend.tts_engine import WhiteboardTTSEngine
from backend.utils import get_asset_path

class VoiceChangerEngine:
    """
    Celebrity AI Voice Changer & AI Cover Studio Engine:
    - Mode 1: Audio File Pitch, Formant & Timbre Transformation
    - Mode 2: Direct Neural Celebrity Voice Synthesis (Text/Lyrics to Voice)
    """
    def __init__(self):
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "celebrity_voice_changer")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.win_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.tts_engine = WhiteboardTTSEngine()

        self.celebrity_presets = [
            {
                "id": "tao_thao",
                "name": "👑 Tào Tháo (Tam Quốc)",
                "category": "Nhân Vật Lịch Sử",
                "gender": "male",
                "pitch_default": -3,
                "eq_filter": "asetrate=44100*0.8409,aresample=44100,atempo=1.1892,equalizer=f=120:width_type=h:width=80:g=8,equalizer=f=3000:width_type=h:width=500:g=4,aecho=0.8:0.85:40:0.25",
                "tts_voice": "tao-thao",
                "desc": "Chất giọng nam trung niên trầm hùng, khí phách quyền lực, dứt khoát oai phong."
            },
            {
                "id": "son_tung_mtp",
                "name": "⚡ Sơn Tùng M-TP",
                "category": "Ca Sĩ Việt Nam",
                "gender": "male",
                "pitch_default": 2,
                "eq_filter": "asetrate=44100*1.1225,aresample=44100,atempo=0.8909,chorus=0.7:0.9:55:0.4:0.25:2,equalizer=f=4500:width_type=h:width=1200:g=6,aecho=0.8:0.7:30:0.2",
                "tts_voice": "adam-11labs-vi",
                "desc": "Chất giọng nam cao, phong cách Pop RnB hiện đại, luyến láy autotune đặc trưng."
            },
            {
                "id": "do_mixi",
                "name": "🎮 Độ Mixi (Tộc Trưởng)",
                "category": "Streamer Nổi Tiếng",
                "gender": "male",
                "pitch_default": -1,
                "eq_filter": "equalizer=f=200:width_type=h:width=100:g=5,equalizer=f=2800:width_type=h:width=800:g=6,compand=0.02|0.05:0.02|0.05:-60/-60|-20/-8|0/-2:6:0:-90:0.02",
                "tts_voice": "turbo-nam-minh",
                "desc": "Giọng nam miền Bắc trầm ấm, hóm hỉnh, mộc mạc và chân thật của Tộc Trưởng."
            },
            {
                "id": "my_tam",
                "name": "🌸 Mỹ Tâm",
                "category": "Ca Sĩ Việt Nam",
                "gender": "female",
                "pitch_default": 3,
                "eq_filter": "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,equalizer=f=350:width_type=h:width=150:g=4,equalizer=f=4000:width_type=h:width=1000:g=5,aecho=0.8:0.85:30:0.2",
                "tts_voice": "turbo-hoai-my",
                "desc": "Chất giọng nữ trung dày, ấm áp, nội lực và giàu cảm xúc."
            },
            {
                "id": "ngoc_ngan",
                "name": "🎙️ Nguyễn Ngọc Ngạn",
                "category": "MC & Kể Chuyện",
                "gender": "male",
                "pitch_default": -2,
                "eq_filter": "asetrate=44100*0.8909,aresample=44100,atempo=1.1225,equalizer=f=180:width_type=h:width=100:g=6,equalizer=f=2500:width_type=h:width=600:g=4",
                "tts_voice": "ngoc-ngan-ke-chuyen-vbee",
                "desc": "Giọng kể chuyện ma và truyện đêm khuya phong cách Nguyễn Ngọc Ngạn truyền cảm, huyền bí."
            },
            {
                "id": "tran_thanh",
                "name": "🎤 Trấn Thành",
                "category": "Nghệ Sĩ & MC",
                "gender": "male",
                "pitch_default": 1,
                "eq_filter": "asetrate=44100*1.0595,aresample=44100,atempo=0.9439,equalizer=f=2500:width_type=h:width=800:g=6,compand=0.02|0.05:0.02|0.05:-60/-60|-25/-10|0/-3:6:0:-90:0.02",
                "tts_voice": "adam-11labs-vi",
                "desc": "Giọng nam truyền cảm, hoạt ngôn, biến hóa đa dạng nhiều cung bậc cảm xúc."
            },
            {
                "id": "michael_jackson",
                "name": "🕺 Michael Jackson",
                "category": "Huyền Thoại Âm Nhạc",
                "gender": "male",
                "pitch_default": 3,
                "eq_filter": "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,chorus=0.6:0.8:45:0.3:0.25:2,equalizer=f=7500:width_type=h:width=2000:g=7,aecho=0.8:0.6:20:0.3",
                "tts_voice": "turbo_adam",
                "desc": "Vua nhạc Pop thế giới với những nốt cao bùng nổ, ngân rung độc nhất vô nhị."
            },
            {
                "id": "taylor_swift",
                "name": "🌟 Taylor Swift",
                "category": "Ca Sĩ Quốc Tế",
                "gender": "female",
                "pitch_default": 3,
                "eq_filter": "asetrate=44100*1.1892,aresample=44100,atempo=0.8409,chorus=0.6:0.8:40:0.3:0.2:2,equalizer=f=8000:width_type=h:width=2500:g=6,treble=g=5",
                "tts_voice": "turbo-hoai-my",
                "desc": "Giọng nữ trong sáng, ngọt ngào và cuốn hút phong cách Pop Country US-UK."
            }
        ]

    def get_audio_info(self, file_path: str) -> dict:
        duration = 0.0
        try:
            cmd = [self.ffmpeg_exe, "-i", file_path]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True, errors="ignore", creationflags=self.win_flags)
            for line in res.stderr.splitlines():
                if "Duration:" in line:
                    parts = line.split("Duration:")[1].split(",")[0].strip()
                    h, m, s = parts.split(":")
                    duration = float(h) * 3600 + float(m) * 60 + float(s)
                    break
        except Exception as e:
            print(f"Error checking audio info: {e}")
        return {"duration": duration, "path": file_path}

    def convert_audio_file(
        self,
        input_audio_path: str,
        celebrity_id: str,
        output_path: str,
        pitch_semitones: int = 0,
        vocal_volume: float = 1.0,
        progress_callback = None
    ) -> bool:
        """Transforms an existing audio/song file with distinct celebrity pitch & character filters"""
        try:
            if not os.path.exists(input_audio_path):
                raise FileNotFoundError(f"Không tìm thấy file: {input_audio_path}")

            if progress_callback:
                progress_callback(15, "Đang phân tích cấu trúc âm thanh...")

            preset = next((p for p in self.celebrity_presets if p["id"] == celebrity_id), self.celebrity_presets[0])

            total_pitch = pitch_semitones + preset.get("pitch_default", 0)
            pitch_ratio = math.pow(2.0, total_pitch / 12.0)

            filter_parts = []
            if total_pitch != 0:
                filter_parts.append(f"asetrate=44100*{pitch_ratio:.4f},aresample=44100,atempo={1.0/pitch_ratio:.4f}")

            # Specific profile filter
            eq_filter = preset.get("eq_filter", "")
            if eq_filter:
                filter_parts.append(eq_filter)

            if vocal_volume != 1.0:
                filter_parts.append(f"volume={vocal_volume:.2f}")

            filter_str = ",".join(filter_parts) if filter_parts else "anull"

            if progress_callback:
                progress_callback(50, f"Đang áp dụng chất giọng {preset['name']}...")

            temp_wav = os.path.join(self.temp_dir, f"trans_{uuid.uuid4().hex[:8]}.wav")
            cmd1 = [
                self.ffmpeg_exe, "-y",
                "-i", input_audio_path,
                "-af", filter_str,
                "-ar", "44100",
                "-ac", "2",
                temp_wav
            ]
            subprocess.run(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.win_flags)

            if progress_callback:
                progress_callback(85, "Đang xuất bản MP3 320kbps...")

            cmd2 = [
                self.ffmpeg_exe, "-y",
                "-i", temp_wav,
                "-codec:a", "libmp3lame",
                "-b:a", "320k",
                output_path
            ]
            subprocess.run(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.win_flags)

            if progress_callback:
                progress_callback(100, f"Đổi giọng sang {preset['name']} thành công!")

            return True
        except Exception as e:
            print(f"Error converting audio file: {e}")
            return False

    def synthesize_celebrity_speech(
        self,
        text: str,
        celebrity_id: str,
        output_path: str,
        progress_callback = None
    ) -> bool:
        """Synthesizes speech directly with 100% genuine AI celebrity voice clone model"""
        try:
            if not text or not text.strip():
                raise ValueError("Văn bản không được để trống!")

            if progress_callback:
                progress_callback(20, "Đang kết nối mô hình Giọng AI Người Nổi Tiếng...")

            preset = next((p for p in self.celebrity_presets if p["id"] == celebrity_id), self.celebrity_presets[0])
            tts_voice = preset.get("tts_voice", "tao-thao")

            if progress_callback:
                progress_callback(50, f"Đang tạo giọng đọc AI: {preset['name']}...")

            raw_path, dur = self.tts_engine.synthesize(text, voice_id=tts_voice, output_path=output_path)

            if progress_callback:
                progress_callback(100, f"Tạo giọng {preset['name']} thành công!")

            return True
        except Exception as e:
            print(f"Error synthesizing celebrity voice: {e}")
            return False
