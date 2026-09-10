import re
from backend.drawing_templates import TEMPLATES, find_best_template_for_text

HISTORICAL_KEYWORD_MAPPING = [
    ("art_vn_bach_dang", ["bạch đằng", "cọc gỗ", "thủy chiến", "thuyền chiến", "ngô quyền", "trần hưng đạo", "trận đánh", "chiến thuyền", "sông bạch đằng"]),
    ("art_vn_trong_dong", ["trống đồng", "đông sơn", "hùng vương", "văn lang", "âu lạc", "nguồn cội", "ngàn năm", "tổ tiên", "văn hóa"]),
    ("art_vn_hai_ba_trung", ["hai bà trưng", "trưng trắc", "trưng nhị", "cưỡi voi", "mê linh", "nữ tướng", "khởi nghĩa"]),
    ("art_vn_quang_trung", ["quang trung", "nguyễn huệ", "ngọc hồi", "đống đa", "quân thanh", "áo vải", "hoàng đế", "đại phá"]),
    ("art_vn_dien_bien_phu", ["điện biên phủ", "chiến dịch", "vỡ òa", "lừng lẫy", "năm châu", "chiến hào", "đại tướng", "võ nguyên giáp"]),
    ("art_vn_hoang_thanh", ["thăng long", "hoàng thành", "kinh đô", "cột cờ", "hà nội", "lý thái tổ", "dời đô"]),
    ("art_vn_co_do_hue", ["cố đô", "huế", "nhà nguyễn", "ngọ môn", "sông hương", "kinh thành"]),
    ("art_vn_ban_do", ["việt nam", "non sông", "bản đồ", "đất nước", "quê hương", "hoàng sa", "trường sa", "chủ quyền", "độc lập", "dân tộc"])
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

        raw_paragraphs = [p.strip() for p in full_text.splitlines() if p.strip()]
        chunks = []

        for p in raw_paragraphs:
            sentences = re.split(r'(?<=[.!?…])\s+', p)
            current_chunk = []
            current_word_count = 0

            for s in sentences:
                s = s.strip()
                if not s:
                    continue
                words = s.split()
                if current_word_count + len(words) > 55 and current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [s]
                    current_word_count = len(words)
                else:
                    current_chunk.append(s)
                    current_word_count += len(words)

            if current_chunk:
                chunks.append(" ".join(current_chunk))

        self.scenes = []
        for i, chunk in enumerate(chunks):
            tmpl = find_best_template_for_text(chunk)
            short_name = tmpl['name'].split('&')[0].strip()
            scene = StoryScene(i, chunk, f"Cảnh {i+1}: {short_name}", tmpl)
            self.scenes.append(scene)

        return self.scenes
