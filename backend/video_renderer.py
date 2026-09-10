import os
import re
import math
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from backend.tts_engine import WhiteboardTTSEngine
from backend.scene_manager import StoryScene
from backend.artistic_sketch_engine import ArtisticSketchEngine
from backend.utils import get_asset_path

class VideoRenderer:
    def __init__(self, tts_engine: WhiteboardTTSEngine):
        self.tts_engine = tts_engine
        self.artistic_engine = ArtisticSketchEngine()
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.hand_img_path = get_asset_path(os.path.join("hands", "hand_marker.png"))
        self.marker_sfx_path = get_asset_path(os.path.join("sounds", "marker_draw.wav"))

    def render_full_story(
        self,
        scenes: list[StoryScene],
        output_video_path: str,
        resolution: tuple[int, int] = (1920, 1080),
        theme: str = "whiteboard",
        progress_callback = None
    ) -> bool:
        width, height = resolution
        fps = 30
        temp_dir = os.path.join(os.path.dirname(output_video_path), "temp_render")
        os.makedirs(temp_dir, exist_ok=True)

        scene_audio_files = []
        total_audio_duration = 0.0

        for i, scene in enumerate(scenes):
            if progress_callback:
                progress_callback(int((i / len(scenes)) * 15), f"Đang tạo giọng đọc AI cho Cảnh {i+1}/{len(scenes)}...")
            if not scene.audio_path or not os.path.exists(scene.audio_path):
                scene_audio_path, dur = self.tts_engine.synthesize(scene.text)
                scene.audio_path = scene_audio_path
                scene.duration = max(dur, 2.5)
            else:
                dur = scene.duration
            scene_audio_files.append(scene.audio_path)
            total_audio_duration += dur

        if os.path.exists(self.hand_img_path):
            hand_img = Image.open(self.hand_img_path).convert("RGBA")
        else:
            hand_img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))

        raw_video_path = os.path.join(temp_dir, "video_track.mp4")
        merged_audio_path = os.path.join(temp_dir, "merged_audio.mp3")

        concat_list_file = os.path.join(temp_dir, "concat_list.txt")
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for a in scene_audio_files:
                f.write(f"file '{a.replace(chr(92), '/')}'\n")

        concat_cmd = [self.ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", concat_list_file, "-c", "copy", merged_audio_path]
        subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        video_cmd = [
            self.ffmpeg_exe, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "bgr24",
            "-r", str(fps),
            "-i", "-",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "veryfast",
            "-crf", "18",
            raw_video_path
        ]
        proc = subprocess.Popen(video_cmd, stdin=subprocess.PIPE)

        total_frames = int(total_audio_duration * fps)
        current_global_frame = 0

        font_size = int(32 * (height / 1080.0))
        try:
            font_title = ImageFont.truetype("arial.ttf", font_size)
        except Exception:
            font_title = ImageFont.load_default()

        try:
            for s_idx, scene in enumerate(scenes):
                scene_frames = int(scene.duration * fps)
                art_id = getattr(scene, "artwork_id", "art_growth_nature")

                for f_idx in range(scene_frames):
                    current_global_frame += 1
                    progress = f_idx / max(scene_frames, 1)

                    if progress_callback and current_global_frame % 6 == 0:
                        pct = 15 + int((current_global_frame / total_frames) * 75)
                        progress_callback(pct, f"Đang dựng Tranh Nghệ Thuật: Cảnh {s_idx + 1}/{len(scenes)} ({f_idx}/{scene_frames} frames)...")

                    frame_pil = self.artistic_engine.render_artistic_frame(
                        art_id=art_id,
                        progress=progress,
                        width=width,
                        height=height,
                        sub_text=scene.text,
                        font=font_title,
                        hand_img=hand_img,
                        theme=theme
                    )

                    frame_bgr = cv2.cvtColor(np.array(frame_pil), cv2.COLOR_RGB2BGR)
                    proc.stdin.write(frame_bgr.tobytes())

            proc.stdin.close()
            proc.wait()

            if progress_callback:
                progress_callback(95, "Đang đóng gói file Video MP4 hoàn chỉnh...")

            final_cmd = [
                self.ffmpeg_exe, "-y",
                "-i", raw_video_path,
                "-i", merged_audio_path,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                output_video_path
            ]
            subprocess.run(final_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if progress_callback:
                progress_callback(100, "Đã xuất Video Nghệ Thuật hoàn tất thành công! 🎉")

            return True
        except Exception as e:
            print(f"Error rendering video: {e}")
            if proc and proc.stdin:
                proc.stdin.close()
            return False
