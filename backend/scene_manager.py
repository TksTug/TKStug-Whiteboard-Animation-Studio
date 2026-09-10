ARTWORK_MAPPING = {}

import re
from backend.drawing_templates import TEMPLATES, find_best_template_for_text

SCENE_MASTERPIECE_ORDER = [
    ("1. Khởi Nguồn Non Sông Đại Việt", "art_vn_ban_do"),
    ("2. Vua Hùng & Trống Đồng Đông Sơn", "art_vn_trong_dong"),
    ("3. Hai Bà Trưng Khởi Nghĩa Mê Linh", "art_vn_hai_ba_trung"),
    ("4. Ngô Quyền Thủy Chiến Bạch Đằng", "art_vn_bach_dang"),
    ("5. Lý Thái Tổ Dời Đô Thăng Long", "art_vn_hoang_thanh"),
    ("6. Nhà Trần & Hào Khí Đông A Sát Thát", "art_vn_nha_tran"),
    ("7. Lê Lợi & Gươm Thần Lam Sơn", "art_vn_le_loi_lam_son"),
    ("8. Vua Quang Trung Đại Phá Quân Thanh", "art_vn_quang_trung"),
    ("9. Cố Đô Huế Di Sản Hoàng Triều", "art_vn_co_do_hue"),
    ("10. Chiến Thắng Điện Biên Phủ", "art_vn_dien_bien_phu"),
    ("11. Biển Đảo Hoàng Sa - Trường Sa", "art_vn_bien_dao_hoang_sa"),
    ("12. Kỷ Nguyên Mới Vươn Tầm Thế Giới", "art_vn_ky_nguyen_tuong_lai")
]

class StoryScene:
    def __init__(self, scene_index: int, text: str, title: str = "", template: dict = None, artwork_id: str = None):
        self.scene_index = scene_index
        self.text = text.strip()
        self.title = title or f"Phân cảnh {scene_index + 1}"
        self.template = template or find_best_template_for_text(self.text)
        self.artwork_id = artwork_id or "art_vn_quang_trung"
        self.audio_path = None
        self.duration = 4.0

class SceneManager:
    def __init__(self):
        self.scenes: list[StoryScene] = []

    def segment_script_into_scenes(self, full_text: str) -> list[StoryScene]:
        if not full_text or not full_text.strip():
            return []

        raw_paragraphs = [p.strip() for p in full_text.splitlines() if p.strip()]

        self.scenes = []
        for i, paragraph in enumerate(raw_paragraphs):
            tmpl = find_best_template_for_text(paragraph)
            
            if i < len(SCENE_MASTERPIECE_ORDER):
                title, art_id = SCENE_MASTERPIECE_ORDER[i]
            else:
                title = f"Cảnh {i+1}: Lịch Sử Đại Việt"
                art_id = "art_vn_quang_trung"
            
            scene = StoryScene(i, paragraph, title, tmpl, artwork_id=art_id)
            self.scenes.append(scene)

        return self.scenes
