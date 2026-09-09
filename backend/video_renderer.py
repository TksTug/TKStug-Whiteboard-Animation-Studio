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
from backend.utils import get_asset_path

def parse_svg_path(d_str: str) -> list[tuple[float, float]]:
    tokens = re.findall(r'[A-Za-z]|[-+]?[0-9]*\.?[0-9]+', d_str)
    points = []
    i = 0
    cur_x, cur_y = 0.0, 0.0
    start_x, start_y = 0.0, 0.0

    while i < len(tokens):
        cmd = tokens[i]
        if cmd.isalpha():
            i += 1
            if cmd == 'M':
                cur_x, cur_y = float(tokens[i]), float(tokens[i+1])
                start_x, start_y = cur_x, cur_y
                points.append((cur_x, cur_y))
                i += 2
            elif cmd == 'L':
                x, y = float(tokens[i]), float(tokens[i+1])
                for t in np.linspace(0, 1, 15):
                    px = cur_x + t * (x - cur_x)
                    py = cur_y + t * (y - cur_y)
                    points.append((px, py))
                cur_x, cur_y = x, y
                i += 2
            elif cmd == 'Q':
                cx, cy = float(tokens[i]), float(tokens[i+1])
                x, y = float(tokens[i+2]), float(tokens[i+3])
                for t in np.linspace(0, 1, 20):
                    px = (1-t)**2 * cur_x + 2*(1-t)*t * cx + t**2 * x
                    py = (1-t)**2 * cur_y + 2*(1-t)*t * cy + t**2 * y
                    points.append((px, py))
                cur_x, cur_y = x, y
                i += 4
            elif cmd == 'C':
                c1x, c1y = float(tokens[i]), float(tokens[i+1])
                c2x, c2y = float(tokens[i+2]), float(tokens[i+3])
                x, y = float(tokens[i+4]), float(tokens[i+5])
                for t in np.linspace(0, 1, 25):
                    px = (1-t)**3 * cur_x + 3*(1-t)**2 * t * c1x + 3*(1-t)*t**2 * c2x + t**3 * x
                    py = (1-t)**3 * cur_y + 3*(1-t)**2 * t * c1y + 3*(1-t)*t**2 * c2y + t**3 * y
                    points.append((px, py))
                cur_x, cur_y = x, y
                i += 6
            elif cmd == 'A':
                # Simplified circular arc approximation
                rx = float(tokens[i])
                ry = float(tokens[i+1])
                x_rot = float(tokens[i+2])
                large_arc = int(tokens[i+3])
                sweep = int(tokens[i+4])
                end_x, end_y = float(tokens[i+5]), float(tokens[i+6])
                # Generate intermediate arc points
                mid_x = (cur_x + end_x) / 2
                mid_y = (cur_y + end_y) / 2
                dx = end_x - cur_x
                dy = end_y - cur_y
                dist = math.hypot(dx, dy)
                if dist > 0.01:
                    norm_x = -dy / dist * (rx if sweep else -rx) * 0.5
                    norm_y = dx / dist * (rx if sweep else -rx) * 0.5
                    ctrl_x = mid_x + norm_x
                    ctrl_y = mid_y + norm_y
                    for t in np.linspace(0, 1, 20):
                        px = (1-t)**2 * cur_x + 2*(1-t)*t * ctrl_x + t**2 * end_x
                        py = (1-t)**2 * cur_y + 2*(1-t)*t * ctrl_y + t**2 * end_y
                        points.append((px, py))
                cur_x, cur_y = end_x, end_y
                i += 7
            elif cmd == 'Z':
                for t in np.linspace(0, 1, 15):
                    px = cur_x + t * (start_x - cur_x)
                    py = cur_y + t * (start_y - cur_y)
                    points.append((px, py))
                cur_x, cur_y = start_x, start_y
        else:
            i += 1

    return points

def wrap_text(text: str, font, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines = []
    current = []
    for w in words:
        current.append(w)
        test_line = " ".join(current)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > max_width and len(current) > 1:
            current.pop()
            lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines

class VideoRenderer:
    def __init__(self, tts_engine: WhiteboardTTSEngine):
        self.tts_engine = tts_engine
        self.ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        self.hand_img_path = get_asset_path(os.path.join("hands", "hand_marker.png"))
        self.marker_sfx_path = get_asset_path(os.path.join("sounds", "marker_draw.wav"))

    def render_full_story(self, scenes: list[StoryScene], output_video_path: str, resolution: tuple[int, int] = (1920, 1080), theme: str = "whiteboard", progress_callback = None) -> bool:
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

        hand_scale = (height / 1080.0) * 0.75
        hand_w = max(int(hand_img.width * hand_scale), 50)
        hand_h = max(int(hand_img.height * hand_scale), 50)
        hand_img_resized = hand_img.resize((hand_w, hand_h), Image.Resampling.LANCZOS)
        tip_x, tip_y = int(60 * hand_scale), int(60 * hand_scale)

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

        bg_color = (255, 255, 255) if theme == "whiteboard" else (254, 243, 199) if theme == "vintage" else (30, 41, 59)
        text_color = (15, 23, 42) if theme == "whiteboard" else (69, 26, 3) if theme == "vintage" else (248, 250, 252)

        try:
            font_size = int(32 * (height / 1080.0))
            try:
                font_title = ImageFont.truetype("arial.ttf", font_size)
            except Exception:
                font_title = ImageFont.load_default()

            for s_idx, scene in enumerate(scenes):
                scene_frames = int(scene.duration * fps)
                paths_data = []
                total_points = 0
                for p_spec in scene.template["paths"]:
                    pts = parse_svg_path(p_spec["d"])
                    paths_data.append({"pts": pts, "spec": p_spec})
                    total_points += len(pts)

                svg_w, svg_h = 500, 300
                scale = min((width * 0.72) / svg_w, (height * 0.55) / svg_h)
                offset_x = (width - svg_w * scale) / 2
                offset_y = (height - svg_h * scale) / 2 + (height * 0.08)

                canvas = Image.new("RGB", (width, height), bg_color)
                draw = ImageDraw.Draw(canvas)

                sub_lines = wrap_text(f'"{scene.text}"', font_title, int(width * 0.82), draw)
                line_height = int(font_size * 1.35)
                total_text_h = len(sub_lines) * line_height
                sub_y_start = int(height * 0.06)

                max_line_w = 0
                for l in sub_lines:
                    bbox = draw.textbbox((0, 0), l, font=font_title)
                    max_line_w = max(max_line_w, bbox[2] - bbox[0])

                pill_padding_x = 24
                pill_padding_y = 10
                pill_x1 = int((width - max_line_w) / 2 - pill_padding_x)
                pill_y1 = int(sub_y_start - pill_padding_y)
                pill_x2 = int((width + max_line_w) / 2 + pill_padding_x)
                pill_y2 = int(sub_y_start + total_text_h + pill_padding_y)
                pill_bg = (241, 245, 249) if theme == "whiteboard" else (250, 235, 195) if theme == "vintage" else (15, 23, 42)

                for f_idx in range(scene_frames):
                    current_global_frame += 1
                    raw_progress = f_idx / max(scene_frames, 1)

                    # Hand draws the sketch during the first 70% of the scene duration
                    draw_progress = min(raw_progress / 0.70, 1.0)

                    if progress_callback and current_global_frame % 6 == 0:
                        pct = 15 + int((current_global_frame / total_frames) * 75)
                        progress_callback(pct, f"Đang dựng Video: Cảnh {s_idx + 1}/{len(scenes)} ({f_idx}/{scene_frames} frames)...")

                    target_point_count = int(draw_progress * total_points)
                    cum_pts = 0
                    active_pt = None

                    frame_img = canvas.copy()
                    frame_draw = ImageDraw.Draw(frame_img)

                    # Draw subtitle backdrop and text
                    frame_draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=12, fill=pill_bg)
                    for li, line in enumerate(sub_lines):
                        bbox = frame_draw.textbbox((0, 0), line, font=font_title)
                        lw = bbox[2] - bbox[0]
                        lx = (width - lw) / 2
                        ly = sub_y_start + li * line_height
                        frame_draw.text((lx, ly), line, font=font_title, fill=text_color)

                    # Draw vector sketch strokes
                    for p in paths_data:
                        pts = p["pts"]
                        spec = p["spec"]
                        color = spec.get("color", "#000000")
                        stroke_w = int(spec.get("width", 3) * scale * 0.7)
                        p_len = len(pts)

                        if target_point_count <= cum_pts:
                            pass
                        elif target_point_count >= cum_pts + p_len:
                            transformed_pts = [(offset_x + x * scale, offset_y + y * scale) for x, y in pts]
                            if len(transformed_pts) > 1:
                                frame_draw.line(transformed_pts, fill=color, width=max(stroke_w, 2), joint="curve")
                        else:
                            drawn_len = target_point_count - cum_pts
                            transformed_pts = [(offset_x + x * scale, offset_y + y * scale) for x, y in pts[:drawn_len]]
                            if len(transformed_pts) > 1:
                                frame_draw.line(transformed_pts, fill=color, width=max(stroke_w, 2), joint="curve")
                            if transformed_pts:
                                active_pt = transformed_pts[-1]

                        cum_pts += p_len

                    # Hand animation logic:
                    # 0.00 -> 0.70: hand draws at active point
                    # 0.70 -> 0.82: hand smoothly moves away off-screen
                    # 0.82 -> 1.00: hand is hidden, viewer enjoys the full sketch while narration finishes
                    if raw_progress < 0.70 and active_pt:
                        hx = int(active_pt[0] - tip_x)
                        hy = int(active_pt[1] - tip_y)
                        frame_img.paste(hand_img_resized, (hx, hy), hand_img_resized)
                    elif 0.70 <= raw_progress < 0.82 and active_pt:
                        retreat_factor = (raw_progress - 0.70) / 0.12
                        hx = int(active_pt[0] - tip_x + retreat_factor * (width * 0.35))
                        hy = int(active_pt[1] - tip_y + retreat_factor * (height * 0.35))
                        frame_img.paste(hand_img_resized, (hx, hy), hand_img_resized)

                    frame_bgr = cv2.cvtColor(np.array(frame_img), cv2.COLOR_RGB2BGR)
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
                progress_callback(100, "Đã xuất Video hoàn tất thành công! 🎉")

            return True
        except Exception as e:
            print(f"Error rendering video: {e}")
            if proc and proc.stdin:
                proc.stdin.close()
            return False
