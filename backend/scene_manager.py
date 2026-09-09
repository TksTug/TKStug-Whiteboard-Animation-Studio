import re
from backend.drawing_templates import TEMPLATES, find_best_template_for_text

class StoryScene:
    def __init__(self, scene_index: int, text: str, title: str = "", template: dict = None):
        self.scene_index = scene_index
        self.text = text.strip()
        self.title = title or f"Phân cảnh {scene_index + 1}"
        self.template = template or find_best_template_for_text(self.text)
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
