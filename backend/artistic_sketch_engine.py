import os
import cv2
import math
import numpy as np
from PIL import Image, ImageFont
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
        Pure, Unobstructed 4K Cinematic Artwork Display (NO TEXT BLOCKING THE VIEW):
        - Phase 1 (0.00 -> 0.40): Elegant energetic line-art pencil sketching
        - Phase 2 (0.40 -> 0.75): Rich vibrant color watercolor wash
        - Phase 3 (0.75 -> 0.85): Smooth hand retreat offscreen
        - Phase 4 (0.85 -> 1.00): 100% steady, crystal-clear completed artwork with full visual immersion
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
            return Image.fromarray(np.clip(color_img, 0, 255).astype(np.uint8))

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
            # Full color completed (0.75 to 1.00) - Steady & Sharp, Pure Clean View
            current_frame_np = color_img.copy()

        frame_pil = Image.fromarray(np.clip(current_frame_np, 0, 255).astype(np.uint8))

        # Draw Sleek Stylus Pen Overlay (pure pen, no hand)
        if hand_img:
            pen_scale = (height / 1080.0) * 0.65
            pw = max(int(hand_img.width * pen_scale), 50)
            ph = max(int(hand_img.height * pen_scale), 50)
            pen_resized = hand_img.resize((pw, ph), Image.Resampling.LANCZOS)
            
            # Precise nib offset: tip is at (12% of width, 88% of height)
            tip_offset_x = int(pw * 0.12)
            tip_offset_y = int(ph * 0.88)

            if active_hand_pos and progress < p2_end:
                hx = int(active_hand_pos[0] - tip_offset_x)
                hy = int(active_hand_pos[1] - tip_offset_y)
                frame_pil.paste(pen_resized, (hx, hy), pen_resized)
            elif p2_end <= progress < p3_end and active_hand_pos:
                retreat = (progress - p2_end) / (p3_end - p2_end)
                retreat_eased = math.sin(retreat * math.pi / 2)
                hx = int(active_hand_pos[0] - tip_offset_x + retreat_eased * (width * 0.6))
                hy = int(active_hand_pos[1] - tip_offset_y - retreat_eased * (height * 0.6))
                frame_pil.paste(pen_resized, (hx, hy), pen_resized)

        return frame_pil
