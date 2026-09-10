import os
import cv2
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from backend.utils import get_asset_path

class ArtisticSketchEngine:
    def __init__(self):
        self.cached_artworks = {}
        self.artworks_dir = get_asset_path("artworks")
        self.hand_path = get_asset_path(os.path.join("hands", "hand_marker.png"))

    def get_artwork_paths(self, art_id: str) -> tuple[str, str]:
        """Returns (color_path, sketch_path) for an artwork ID or custom file path"""
        if os.path.isabs(art_id) and os.path.exists(art_id):
            base_no_ext = os.path.splitext(art_id)[0]
            sketch_p = f"{base_no_ext}_sketch.png"
            if not os.path.exists(sketch_p):
                self.generate_sketch_for_file(art_id, sketch_p)
            return art_id, sketch_p
        
        color_p = os.path.join(self.artworks_dir, f"{art_id}.png")
        sketch_p = os.path.join(self.artworks_dir, f"{art_id}_sketch.png")
        
        if not os.path.exists(color_p):
            color_p = os.path.join(self.artworks_dir, "art_vn_quang_trung.png")
            sketch_p = os.path.join(self.artworks_dir, "art_vn_quang_trung_sketch.png")
            
        return color_p, sketch_p

    def generate_sketch_for_file(self, color_path: str, save_sketch_path: str):
        """Converts any custom uploaded photo/image into an ultra-realistic anime pencil sketch"""
        try:
            pil_img = Image.open(color_path).convert("RGB")
            img_np = np.array(pil_img)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            inv_gray = 255 - gray
            blurred = cv2.GaussianBlur(inv_gray, (15, 15), 0)
            sketch = cv2.divide(gray, 255 - blurred, scale=256.0)
            edges1 = cv2.Canny(gray, 20, 80)
            edges2 = cv2.Canny(gray, 60, 140)
            combined_edges = cv2.bitwise_or(edges1, edges2)
            edges_inv = 255 - combined_edges
            sketch_combined = cv2.min(sketch, edges_inv)
            sketch_rgb = cv2.cvtColor(sketch_combined, cv2.COLOR_GRAY2RGB)
            Image.fromarray(sketch_rgb).save(save_sketch_path)
        except Exception as e:
            print(f"Error creating sketch for custom file: {e}")

    def render_artistic_frame(
        self,
        art_id: str,
        progress: float,
        width: int,
        height: int,
        sub_text: str = "",
        font: ImageFont.ImageFont = None,
        hand_img: Image.Image = None,
        theme: str = "vintage",
        is_static: bool = False
    ) -> Image.Image:
        """
        Smooth, Non-Shaking Synchronized Drawing & Inking:
        - Phase 1 (0.00 -> 0.40): Elegant energetic line-art pencil sketching
        - Phase 2 (0.40 -> 0.75): Rich vibrant color watercolor wash
        - Phase 3 (0.75 -> 0.85): Smooth hand retreat offscreen
        - Phase 4 (0.85 -> 1.00): 100% steady, crystal-clear, rock-solid completed artwork (NO JITTER / NO CAMERA SHAKE)
        """
        color_p, sketch_p = self.get_artwork_paths(art_id)
        
        cache_key = f"{color_p}_{width}_{height}"
        if cache_key in self.cached_artworks:
            color_img, sketch_img = self.cached_artworks[cache_key]
        else:
            c_raw = Image.open(color_p).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            s_raw = Image.open(sketch_p).convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            color_img = np.array(c_raw, dtype=np.float32)
            sketch_img = np.array(s_raw, dtype=np.float32)
            self.cached_artworks[cache_key] = (color_img, sketch_img)

        # Base background canvas
        if theme == "whiteboard":
            base_bg = np.full((height, width, 3), 255.0, dtype=np.float32)
        elif theme == "vintage":
            base_bg = np.zeros((height, width, 3), dtype=np.float32)
            base_bg[:, :] = [250.0, 240.0, 215.0]
        else:
            base_bg = np.zeros((height, width, 3), dtype=np.float32)
            base_bg[:, :] = [30.0, 41.0, 59.0]

        if is_static:
            frame_pil = Image.fromarray(np.clip(color_img, 0, 255).astype(np.uint8))
            if sub_text:
                self._render_dynamic_subtitles(frame_pil, sub_text, 1.0, width, height, font, theme)
            return frame_pil

        # Balanced Pacing Thresholds
        p1_end = 0.40
        p2_end = 0.75
        p3_end = 0.85

        active_hand_pos = None
        y_indices, x_indices = np.indices((height, width))
        diag_dist = (x_indices / width * 0.65 + y_indices / height * 0.35)

        if progress < p1_end:
            # Phase 1: Rapid LineArt Sketching
            p1_ratio = progress / p1_end
            mask_sketch = np.clip((p1_ratio * 1.35 - diag_dist) * 6.0, 0.0, 1.0)
            mask_sketch_3d = np.repeat(mask_sketch[:, :, np.newaxis], 3, axis=2)
            current_frame_np = (1.0 - mask_sketch_3d) * base_bg + mask_sketch_3d * sketch_img
            
            sweep_x = int(p1_ratio * width * 0.85 + 40)
            sweep_y = int(p1_ratio * height * 0.70 + 80)
            wobble_x = int(math.sin(progress * 70) * 16)
            wobble_y = int(math.cos(progress * 80) * 12)
            active_hand_pos = (min(max(sweep_x + wobble_x, 60), width - 60), min(max(sweep_y + wobble_y, 80), height - 80))

        elif p1_end <= progress < p2_end:
            # Phase 2: Vibrant Anime Color Wash
            p2_ratio = (progress - p1_end) / (p2_end - p1_end)
            mask_color = np.clip((p2_ratio * 1.40 - diag_dist) * 5.0, 0.0, 1.0)
            mask_color_3d = np.repeat(mask_color[:, :, np.newaxis], 3, axis=2)
            current_frame_np = (1.0 - mask_color_3d) * sketch_img + mask_color_3d * color_img

            sweep_x = int(p2_ratio * width * 0.88 + 30)
            sweep_y = int(p2_ratio * height * 0.78 + 60)
            brush_wobble_x = int(math.sin(progress * 50) * 20)
            brush_wobble_y = int(math.cos(progress * 60) * 15)
            active_hand_pos = (min(max(sweep_x + brush_wobble_x, 60), width - 60), min(max(sweep_y + brush_wobble_y, 80), height - 80))

        else:
            # Full color completed (0.75 to 1.00) - Steady & Sharp, ZERO CAMERA SHAKE
            current_frame_np = color_img.copy()

        frame_pil = Image.fromarray(np.clip(current_frame_np, 0, 255).astype(np.uint8))

        # Draw Hand Overlay (only during drawing phases)
        if hand_img:
            hand_scale = (height / 1080.0) * 0.72
            hw = max(int(hand_img.width * hand_scale), 60)
            hh = max(int(hand_img.height * hand_scale), 60)
            hand_resized = hand_img.resize((hw, hh), Image.Resampling.LANCZOS)
            
            # Precise tip offset: 17.7% of width and height
            tip_offset_x = int(hw * 0.177)
            tip_offset_y = int(hh * 0.177)

            if active_hand_pos and progress < p2_end:
                hx = int(active_hand_pos[0] - tip_offset_x)
                hy = int(active_hand_pos[1] - tip_offset_y)
                frame_pil.paste(hand_resized, (hx, hy), hand_resized)
            elif p2_end <= progress < p3_end and active_hand_pos:
                retreat = (progress - p2_end) / (p3_end - p2_end)
                retreat_eased = math.sin(retreat * math.pi / 2)
                hx = int(active_hand_pos[0] - tip_offset_x + retreat_eased * (width * 0.6))
                hy = int(active_hand_pos[1] - tip_offset_y + retreat_eased * (height * 0.6))
                frame_pil.paste(hand_resized, (hx, hy), hand_resized)

        # Render Modern Word-by-Word Highlighted Subtitle Card
        if sub_text:
            self._render_dynamic_subtitles(frame_pil, sub_text, progress, width, height, font, theme)

        return frame_pil

    def _render_dynamic_subtitles(self, img: Image.Image, text: str, progress: float, width: int, height: int, font: ImageFont.ImageFont, theme: str):
        """Renders frosted rounded subtitle banner with highlighted active words"""
        draw = ImageDraw.Draw(img)
        words = text.split()
        if not words:
            return

        if font is None:
            font_size = int(32 * (height / 1080.0))
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

        max_sub_w = int(width * 0.82)
        lines = []
        current_line = []
        line_word_indices = []
        current_line_indices = []

        for idx, w in enumerate(words):
            current_line.append(w)
            current_line_indices.append(idx)
            test_str = " ".join(current_line)
            bbox = draw.textbbox((0, 0), test_str, font=font)
            if (bbox[2] - bbox[0]) > max_sub_w and len(current_line) > 1:
                current_line.pop()
                current_line_indices.pop()
                lines.append(" ".join(current_line))
                line_word_indices.append(current_line_indices)
                current_line = [w]
                current_line_indices = [idx]
        if current_line:
            lines.append(" ".join(current_line))
            line_word_indices.append(current_line_indices)

        line_h = int(font.size * 1.35)
        total_sub_h = len(lines) * line_h
        sub_y_start = int(height * 0.055)

        max_line_w = 0
        for l in lines:
            bbox = draw.textbbox((0, 0), l, font=font)
            max_line_w = max(max_line_w, bbox[2] - bbox[0])

        pad_x, pad_y = 28, 12
        card_x1 = int((width - max_line_w) / 2 - pad_x)
        card_y1 = int(sub_y_start - pad_y)
        card_x2 = int((width + max_line_w) / 2 + pad_x)
        card_y2 = int(sub_y_start + total_sub_h + pad_y)

        # Frosted glass card backdrop with golden outline
        pill_bg = (15, 23, 42)
        draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=16, fill=pill_bg, outline=(234, 179, 8), width=2)

        active_word_idx = int(progress * len(words))

        for l_idx, (line_text, word_indices) in enumerate(zip(lines, line_word_indices)):
            line_bbox = draw.textbbox((0, 0), line_text, font=font)
            line_w = line_bbox[2] - line_bbox[0]
            cur_x = (width - line_w) / 2
            cur_y = sub_y_start + l_idx * line_h

            line_words = line_text.split()
            for w_str, global_w_idx in zip(line_words, word_indices):
                if global_w_idx <= active_word_idx:
                    word_color = (250, 204, 21) # Luminous Gold
                else:
                    word_color = (241, 245, 249) # Clean White

                draw.text((cur_x, cur_y), w_str, font=font, fill=word_color)
                w_bbox = draw.textbbox((0, 0), w_str + " ", font=font)
                cur_x += (w_bbox[2] - w_bbox[0])
