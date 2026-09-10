import os
import re
import uuid
import urllib.request
import urllib.parse
from PIL import Image
from backend.utils import get_asset_path

HISTORICAL_TRANSLATIONS = [
    ("quang trung", "Emperor Quang Trung Nguyen Hue of Vietnam in heroic red dragon armor"),
    ("bạch đằng", "Battle of Bach Dang River with wooden stakes trapping ancient warships in storm"),
    ("trống đồng", "Dong Son sacred bronze drum glowing with mythical sun motifs and ancient Hung King chiefs"),
    ("hai bà trưng", "Trung Sisters national heroines riding giant battle war elephants with swords and banners"),
    ("điện biên phủ", "Victory of Dien Bien Phu heroic soldiers waving red flag with yellow star on bunker at sunrise"),
    ("thăng long", "Imperial Citadel of Thang Long in Hanoi with ancient palace and flag tower"),
    ("hoàng thành", "Imperial Citadel in Hanoi with lotus ponds and ancient gates"),
    ("huế", "Ancient Imperial City of Hue Ngo Mon gate reflecting on Perfume River at sunset"),
    ("việt nam", "Sacred S-shaped map of Vietnam glowing with golden dragon aura surrounded by turquoise sea"),
    ("núi", "Heroic explorer standing on top of highest snowy mountain peak at sunrise"),
    ("ý tưởng", "Luminous glowing cosmic lightbulb in magical library of wisdom with floating books"),
    ("cây", "Vibrant sacred tree of life sprouting with golden sunbeams in magical lush forest"),
    ("sách", "Ancient open history book with glowing scrolls and castles floating out like stardust"),
    ("thời gian", "Ornate golden hourglass with cosmic galaxy stardust inside mahogany study"),
    ("chiến thắng", "Golden victory trophy cup with laurel wreath and fireworks celebration"),
    ("hợp tác", "Two anime leaders making heroic alliance handshake in royal palace"),
    ("thương mại", "Prosperous ancient trading harbor with ships and golden coins"),
    ("hải đăng", "Majestic lighthouse shining beam of hope through turbulent ocean storm"),
]

class AIArtGenerator:
    def __init__(self):
        self.output_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "whiteboard_ai_art")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_art_for_text(self, text: str) -> str:
        """Generates a stunning 2D anime digital illustration from any Vietnamese sentence"""
        clean = text.lower()
        matched_concept = None
        for kw, en_concept in HISTORICAL_TRANSLATIONS:
            if kw in clean:
                matched_concept = en_concept
                break

        if not matched_concept:
            # General anime prompt
            # Extract key words
            short_clean = re.sub(r'[^\w\s]', '', clean)[:60]
            matched_concept = f"epic Vietnamese historical fantasy scene, {short_clean}, vibrant atmosphere"

        full_prompt = f"masterpiece 2D anime digital illustration, {matched_concept}, Makoto Shinkai studio ghibli cinematic anime movie art, dramatic lighting, highly detailed, 4k"
        encoded_prompt = urllib.parse.quote(full_prompt)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1280&height=720&model=flux&nologo=true"

        out_filename = f"ai_art_{uuid.uuid4().hex[:8]}.png"
        out_path = os.path.join(self.output_dir, out_filename)

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        data = urllib.request.urlopen(req, timeout=40).read()
        
        with open(out_path, "wb") as f:
            f.write(data)

        return out_path
