import re
from backend.drawing_templates import TEMPLATES, find_best_template_for_text

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

class StoryScene:
    def __init__(self, scene_index: int, text: str, title: str = "", template: dict = None, artwork_id: str = None):
        self.scene_index = scene_index
        self.text = text.strip()
        self.title = title or f"Phân cảnh {scene_index + 1}"
        self.template = template or find_best_template_for_text(self.text)
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
                if current_word_count + len(words) > 35 and current_chunk:
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
