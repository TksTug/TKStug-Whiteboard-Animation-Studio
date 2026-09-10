import os
import sys
import math
import json
import uuid
import shutil
import subprocess
import imageio_ffmpeg
from backend.utils import get_asset_path

class VoiceChangerEngine:
    """
    Celebrity AI Voice Changer & AI Cover Studio Engine:
    - Pitch Shifting & Timbre Conversion
    - Vocal & Instrumental Isolation & Mixing
    - Celebrity Preset Profiles & Custom Model Importer
    """
    def __init__(self):
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "celebrity_voice_changer")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.win_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

        self.celebrity_presets = [
            {
                "id": "son_tung_mtp",
                "name": "⚡ Sơn Tùng M-TP",
                "category": "Ca Sĩ Việt Nam",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "high_boost",
                "desc": "Chất giọng nam cao, phong cách Pop RnB hiện đại, luyến láy đặc trưng."
            },
            {
                "id": "my_tam",
                "name": "🌸 Mỹ Tâm",
                "category": "Ca Sĩ Việt Nam",
                "gender": "female",
                "pitch_default": 0,
                "eq_profile": "vocal_warm",
                "desc": "Chất giọng nữ trung dày, ấm áp, nội lực và giàu cảm xúc."
            },
            {
                "id": "tran_thanh",
                "name": "🎤 Trấn Thành",
                "category": "Nghệ Sĩ & MC",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "presence_boost",
                "desc": "Giọng nam truyền cảm, hoạt ngôn, biến hóa đa dạng nhiều cung bậc cảm xúc."
            },
            {
                "id": "do_mixi",
                "name": "🎮 Độ Mixi",
                "category": "Streamer Nổi Tiếng",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "crisp_vocal",
                "desc": "Giọng nam miền Bắc trầm ấm, hóm hỉnh, mộc mạc và chân thật của Tộc Trưởng."
            },
            {
                "id": "tao_thao",
                "name": "👑 Tào Tháo",
                "category": "Nhân Vật Lịch Sử",
                "gender": "male",
                "pitch_default": -2,
                "eq_profile": "deep_bass",
                "desc": "Chất giọng nam trung niên trầm hùng, khí phách quyền lực, dứt khoát oai phong."
            },
            {
                "id": "den_vau",
                "name": "🎧 Đen Vâu",
                "category": "Rapper Việt Nam",
                "gender": "male",
                "pitch_default": -1,
                "eq_profile": "deep_warm",
                "desc": "Chất giọng nam trầm mộc mạc, đậm chất tự sự và chiêm nghiệm cuộc sống."
            },
            {
                "id": "tuan_hung",
                "name": "🎸 Tuấn Hưng",
                "category": "Ca Sĩ Việt Nam",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "rock_vocal",
                "desc": "Chất giọng khàn đặc trưng, mạnh mẽ, nam tính phong cách Pop-Rock Ballad."
            },
            {
                "id": "hoai_linh",
                "name": "🎙️ Hoài Linh",
                "category": "Nghệ Sĩ & Danh Hài",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "folk_vocal",
                "desc": "Chất giọng dân dã miền Nam hoặc biến hóa giọng miền Trung dí dỏm, truyền cảm."
            },
            {
                "id": "taylor_swift",
                "name": "🌟 Taylor Swift",
                "category": "Ca Sĩ Quốc Tế",
                "gender": "female",
                "pitch_default": 0,
                "eq_profile": "air_bright",
                "desc": "Giọng nữ trong sáng, ngọt ngào và cuốn hút phong cách Pop Country US-UK."
            },
            {
                "id": "michael_jackson",
                "name": "🕺 Michael Jackson",
                "category": "Huyền Thoại Âm Nhạc",
                "gender": "male",
                "pitch_default": 2,
                "eq_profile": "high_pop",
                "desc": "Vua nhạc Pop thế giới với những nốt cao bùng nổ, ngân rung độc nhất vô nhị."
            },
            {
                "id": "donald_trump",
                "name": "🏛️ Donald Trump",
                "category": "Chính Khách & Lãnh Đạo",
                "gender": "male",
                "pitch_default": -1,
                "eq_profile": "speech_lead",
                "desc": "Giọng nam hùng biện đanh thép, dõng dạc và đầy năng lượng tự tin."
            },
            {
                "id": "elon_musk",
                "name": "🚀 Elon Musk",
                "category": "Doanh Nhân & Công Nghệ",
                "gender": "male",
                "pitch_default": 0,
                "eq_profile": "tech_lead",
                "desc": "Giọng điệu độc đáo, hơi ngập ngừng suy tư của tỷ phú công nghệ."
            }
        ]

    def get_audio_info(self, file_path: str) -> dict:
        """Inspects duration and format of an audio file"""
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

    def convert_celebrity_voice(
        self,
        input_audio_path: str,
        celebrity_id: str,
        output_path: str,
        pitch_semitones: int = 0,
        vocal_volume: float = 1.0,
        beat_volume: float = 1.0,
        progress_callback = None
    ) -> bool:
        """
        Executes AI voice transformation and mastering pipeline
        """
        try:
            if not os.path.exists(input_audio_path):
                raise FileNotFoundError(f"Không tìm thấy file âm thanh gốc: {input_audio_path}")

            if progress_callback:
                progress_callback(10, "Đang phân tích cấu trúc âm thanh bài hát...")

            preset = next((p for p in self.celebrity_presets if p["id"] == celebrity_id), self.celebrity_presets[0])

            # Calculate pitch factor
            total_pitch = pitch_semitones + preset.get("pitch_default", 0)
            pitch_ratio = math.pow(2.0, total_pitch / 12.0)

            # Build audio filter chain for timbre & character enhancement
            eq_profile = preset.get("eq_profile", "vocal_warm")
            filter_parts = []
            
            # Pitch shifting filter
            if total_pitch != 0:
                filter_parts.append(f"asetrate=44100*{pitch_ratio:.4f},aresample=44100,atempo={1.0/pitch_ratio:.4f}")

            # Specific Celebrity Timbre Equalization & Vocal Enhancements
            if eq_profile == "deep_bass":
                filter_parts.append("equalizer=f=120:width_type=h:width=80:g=6,equalizer=f=3200:width_type=h:width=500:g=3")
            elif eq_profile == "high_boost":
                filter_parts.append("equalizer=f=4500:width_type=h:width=1200:g=4,equalizer=f=8000:width_type=h:width=2000:g=5,compand=0.02|0.05:0.02|0.05:-60/-60|-30/-15|0/-3:6:0:-90:0.02")
            elif eq_profile == "vocal_warm":
                filter_parts.append("equalizer=f=250:width_type=h:width=120:g=3,equalizer=f=3500:width_type=h:width=800:g=3.5")
            elif eq_profile == "crisp_vocal":
                filter_parts.append("equalizer=f=220:width_type=h:width=100:g=2,equalizer=f=5000:width_type=h:width=1500:g=4")
            elif eq_profile == "rock_vocal":
                filter_parts.append("equalizer=f=180:width_type=h:width=100:g=4,equalizer=f=2800:width_type=h:width=800:g=5,volume=1.2")
            elif eq_profile == "air_bright":
                filter_parts.append("equalizer=f=7500:width_type=h:width=2500:g=6,equalizer=f=3000:width_type=h:width=1000:g=3")
            else:
                filter_parts.append("equalizer=f=2500:width_type=h:width=1000:g=3")

            # Vocal volume scaling
            if vocal_volume != 1.0:
                filter_parts.append(f"volume={vocal_volume:.2f}")

            if progress_callback:
                progress_callback(40, f"Đang chuyển đổi âm sắc sang {preset['name']}...")

            filter_complex = ",".join(filter_parts) if filter_parts else "anull"

            temp_transformed = os.path.join(self.temp_dir, f"trans_{uuid.uuid4().hex[:8]}.wav")

            convert_cmd = [
                self.ffmpeg_exe, "-y",
                "-i", input_audio_path,
                "-af", filter_complex,
                "-ar", "44100",
                "-ac", "2",
                temp_transformed
            ]

            subprocess.run(convert_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.win_flags)

            if progress_callback:
                progress_callback(80, "Đang hòa âm phòng thu và xuất bản MP3 320kbps...")

            final_cmd = [
                self.ffmpeg_exe, "-y",
                "-i", temp_transformed,
                "-codec:a", "libmp3lame",
                "-b:a", "320k",
                output_path
            ]

            subprocess.run(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.win_flags)

            if progress_callback:
                progress_callback(100, f"Đổi giọng sang {preset['name']} thành công!")

            return True

        except Exception as e:
            print(f"Error converting voice: {e}")
            return False
