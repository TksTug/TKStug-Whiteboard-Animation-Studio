import re
from backend.drawing_templates import TEMPLATES, find_best_template_for_text

# Priority Ordered Mapping: More specific historical events come first
HISTORICAL_KEYWORD_MAPPING = [
    ("art_vn_nha_tran", ["mông - nguyên", "mông nguyên", "đông a", "diên hồng", "sát thát", "nhà trần", "hàm tử", "chương dương"]),
    ("art_vn_quang_trung", ["quang trung", "nguyễn huệ", "ngọc hồi", "khương thượng", "đống đa", "mãn thanh", "áo vải cờ đào", "kỷ dậu", "tây sơn"]),
    ("art_vn_le_loi_lam_son", ["lam sơn", "lê lợi", "nguyễn trãi", "bình định vương", "thuận thiên", "nhà minh", "nghĩa quân"]),
    ("art_vn_hai_ba_trung", ["hai bà trưng", "trưng trắc", "trưng nhị", "cưỡi voi", "mê linh", "tô định", "lĩnh nam", "người phụ nữ"]),
    ("art_vn_bach_dang", ["bạch đằng", "cọc gỗ", "ngô quyền", "nam hán", "lưu hoằng tháo", "thủy chiến", "chín trăm ba mươi tám"]),
    ("art_vn_hoang_thanh", ["thăng long", "chiếu dời đô", "lý thái tổ", "đại la", "hoa lư", "ngàn năm văn hiến", "một ngàn không trăm mười"]),
    ("art_vn_co_do_hue", ["cố đô huế", "cố đô", "sông hương", "ngọ môn", "thái hòa", "lăng tẩm", "nhã nhạc", "kinh thành huế"]),
    ("art_vn_dien_bien_phu", ["điện biên phủ", "de castries", "khoét núi", "lừng lẫy năm châu", "năm mươi tư", "hồ chí minh", "thực dân pháp"]),
    ("art_vn_bien_dao_hoang_sa", ["sa vĩ", "móng cái", "cà mau", "hoàng sa", "trường sa", "biển đảo", "lũng cú", "hải đảo", "tấc biển"]),
    ("art_vn_ky_nguyen_tuong_lai", ["kỷ nguyên mới", "kỷ nguyên", "tri thức", "sáng tạo", "hội nhập", "cường quốc", "vươn mình", "tương lai"]),
    ("art_vn_trong_dong", ["trống đồng", "đông sơn", "vua hùng", "văn lang", "chim lạc", "phong châu", "nguồn cội", "tiên rồng", "thuở sơ khai"]),
    ("art_vn_ban_do", ["bốn ngàn năm", "dải đất hình chữ s", "tiền nhân", "bờ cõi", "giữ nước", "non sông", "bản đồ"])
]

ARTWORK_MAPPING = {
    "growth_seed": "art_growth_nature",
    "lightbulb_idea": "art_idea_wisdom",
    "mountain_success": "art_mountain_peak",
    "hourglass_time": "art_time_hourglass",
    "open_book": "art_book_knowledge",
    "lighthouse_storm": "art_lighthouse_storm",
    "money_wealth": "art_wealth_finance",
    "target_bullseye": "art_target_focus",
    "brain_intellect": "art_idea_wisdom",
    "heart_emotion": "art_home_family",
    "handshake_partner": "art_partnership_deal",
    "rocket_launch": "art_rocket_breakthrough",
    "trophy_winner": "art_trophy_glory",
    "growth_chart": "art_growth_chart",
    "gear_system": "art_gear_system",
    "shield_security": "art_shield_protection",
    "key_solution": "art_key_unlock",
    "puzzle_pieces": "art_puzzle_solution",
    "chat_communication": "art_chat_connection",
    "coffee_relax": "art_coffee_peace",
    "home_family": "art_home_family",
    "compass_journey": "art_compass_journey",
    "fire_passion": "art_fire_passion",
    "balance_scale": "art_balance_scale",
    "person_thinking": "art_person_thinking",
    "person_working": "art_person_working"
}

def find_best_artwork_for_history(text: str) -> str:
    clean = text.lower()
    for aid, kws in HISTORICAL_KEYWORD_MAPPING:
        for kw in kws:
            if kw in clean:
                return aid
    return None

class StoryScene:
    def __init__(self, scene_index: int, text: str, title: str = "", template: dict = None, artwork_id: str = None):
        self.scene_index = scene_index
        self.text = text.strip()
        self.title = title or f"Phân cảnh {scene_index + 1}"
        self.template = template or find_best_template_for_text(self.text)
        
        hist_art = find_best_artwork_for_history(self.text)
        if hist_art:
            self.artwork_id = hist_art
        else:
            tmpl_id = self.template.get("id", "growth_seed") if isinstance(self.template, dict) else "growth_seed"
            self.artwork_id = artwork_id or ARTWORK_MAPPING.get(tmpl_id, "art_growth_nature")
            
        self.audio_path = None
        self.duration = 4.0

class SceneManager:
    def __init__(self):
        self.scenes: list[StoryScene] = []

    def segment_script_into_scenes(self, full_text: str) -> list[StoryScene]:
        if not full_text or not full_text.strip():
            return []

        # Split strictly by paragraph so user's 12 paragraphs become exactly 12 scenes
        raw_paragraphs = [p.strip() for p in full_text.splitlines() if p.strip()]

        titles = [
            "1. Khởi Nguồn Non Sông Đại Việt",
            "2. Vua Hùng & Trống Đồng Đông Sơn",
            "3. Hai Bà Trưng Khởi Nghĩa Mê Linh",
            "4. Ngô Quyền Thủy Chiến Bạch Đằng",
            "5. Lý Thái Tổ Dời Đô Thăng Long",
            "6. Nhà Trần & Hào Khí Đông A Sát Thát",
            "7. Lê Lợi & Gươm Thần Lam Sơn",
            "8. Vua Quang Trung Đại Phá Quân Thanh",
            "9. Cố Đô Huế Di Sản Hoàng Triều",
            "10. Chiến Thắng Điện Biên Phủ",
            "11. Biển Đảo Hoàng Sa - Trường Sa",
            "12. Kỷ Nguyên Mới Vươn Tầm Thế Giới"
        ]

        self.scenes = []
        for i, paragraph in enumerate(raw_paragraphs):
            tmpl = find_best_template_for_text(paragraph)
            hist_art = find_best_artwork_for_history(paragraph)
            short_name = tmpl['name'].split('&')[0].strip() if tmpl else f"Cảnh {i+1}"
            custom_title = titles[i] if i < len(titles) else f"Cảnh {i+1}: {short_name}"
            
            scene = StoryScene(i, paragraph, custom_title, tmpl)
            if hist_art:
                scene.artwork_id = hist_art
            self.scenes.append(scene)

        return self.scenes
