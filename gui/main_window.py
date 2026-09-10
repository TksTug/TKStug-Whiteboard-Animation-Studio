import os
import sys
import threading
import math
import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QSlider, QProgressBar, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QFrame, QSplitter, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QPointF, QRectF, QUrl
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QPen, QBrush, QPixmap, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from backend.tts_engine import WhiteboardTTSEngine
from backend.scene_manager import SceneManager, StoryScene, ARTWORK_MAPPING
from backend.drawing_templates import TEMPLATES
from backend.artistic_sketch_engine import ArtisticSketchEngine
from backend.video_renderer import VideoRenderer
from backend.utils import get_asset_path

class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    preview_ready = pyqtSignal(int, str, float)

class WhiteboardCanvasWidget(QWidget):
    """Live interactive preview player showing multi-layer pencil sketch + watercolor inking in real-time"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(320)
        self.current_scene: StoryScene = None
        self.theme = "vintage"
        self.progress = 0.0
        self.is_animating = False

        self.artistic_engine = ArtisticSketchEngine()

        hand_path = get_asset_path(os.path.join("hands", "hand_marker.png"))
        if os.path.exists(hand_path):
            self.hand_pil = Image.open(hand_path).convert("RGBA")
        else:
            self.hand_pil = Image.new("RGBA", (200, 200), (0, 0, 0, 0))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self.anim_duration_ms = 4500
        self.elapsed_ms = 0

        # Audio playback support for preview
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

    def set_scene(self, scene: StoryScene, theme: str = "vintage"):
        self.current_scene = scene
        self.theme = theme
        self.progress = 0.0
        self.elapsed_ms = 0
        self.is_animating = False
        self.timer.stop()
        self.player.stop()
        if scene:
            self.anim_duration_ms = int(max(scene.duration, 2.5) * 1000)
        self.update()

    def start_preview(self, audio_path: str = None, duration_sec: float = None):
        if not self.current_scene:
            return
        if duration_sec:
            self.anim_duration_ms = int(max(duration_sec, 2.5) * 1000)
        elif self.current_scene.duration:
            self.anim_duration_ms = int(max(self.current_scene.duration, 2.5) * 1000)

        self.progress = 0.0
        self.elapsed_ms = 0
        self.is_animating = True

        if audio_path and os.path.exists(audio_path):
            self.player.setSource(QUrl.fromLocalFile(audio_path))
            self.player.play()

        self.timer.start(20) # 50 fps smooth tick
        self.update()

    def pause_preview(self):
        self.is_animating = False
        self.timer.stop()
        self.player.pause()
        self.update()

    def on_tick(self):
        self.elapsed_ms += 20
        self.progress = min(self.elapsed_ms / max(self.anim_duration_ms, 1), 1.0)
        self.update()
        if self.progress >= 1.0:
            self.is_animating = False
            self.timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()

        if not self.current_scene:
            painter.fillRect(0, 0, w, h, QColor(15, 23, 42))
            painter.setPen(QColor(148, 163, 184))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Màn hình xem trước trực tiếp (Live Player)")
            return

        art_id = getattr(self.current_scene, "artwork_id", "art_vn_quang_trung")
        is_static = not self.is_animating and (self.progress == 0.0 or self.progress == 1.0)

        # Render high-grade artistic frame
        frame_pil = self.artistic_engine.render_artistic_frame(
            art_id=art_id,
            progress=self.progress,
            width=w,
            height=h,
            sub_text=self.current_scene.text,
            hand_img=self.hand_pil if self.is_animating else None,
            theme=self.theme,
            is_static=is_static
        )

        # Convert to QImage and draw
        img_rgb = frame_pil.convert("RGBA")
        data = img_rgb.tobytes("raw", "RGBA")
        qimg = QImage(data, w, h, QImage.Format.Format_RGBA8888)
        painter.drawImage(0, 0, qimg)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TKStug Whiteboard Studio - Dựng Video Lịch Sử & Kể Chuyện Nghệ Thuật (Tối Ưu 5-15 Phút)")
        self.resize(1350, 890)
        self.setMinimumSize(1100, 750)

        self.tts_engine = WhiteboardTTSEngine()
        self.scene_manager = SceneManager()
        self.video_renderer = VideoRenderer(self.tts_engine)
        self.current_scenes: list[StoryScene] = []

        self.signals = WorkerSignals()
        self.signals.preview_ready.connect(self._handle_preview_ready)

        self.setup_ui()
        self.apply_theme()
        self.populate_voices()
        self.populate_artworks()
        self.load_sample_story()

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #0b1120;
                color: #f8fafc;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QGroupBox {
                border: 1px solid #1e293b;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 14px;
                font-weight: bold;
                font-size: 13px;
                color: #38bdf8;
                background-color: #0f172a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 14px;
                padding: 0 6px;
            }
            QTextEdit, QListWidget {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 8px;
                color: #f1f5f9;
                font-size: 13px;
                selection-background-color: #2563eb;
            }
            QTextEdit:focus, QListWidget:focus {
                border: 1px solid #3b82f6;
            }
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px 16px;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
            QPushButton:pressed {
                background-color: #1e40af;
            }
            QPushButton#secondaryBtn {
                background-color: #334155;
                color: #f8fafc;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #475569;
            }
            QPushButton#accentBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
                font-size: 14px;
                font-weight: 800;
                padding: 14px 20px;
            }
            QPushButton#accentBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1d4ed8, stop:1 #6d28d9);
            }
            QPushButton#playBtn {
                background-color: #10b981;
                font-size: 12px;
                padding: 7px 16px;
                font-weight: bold;
            }
            QPushButton#playBtn:hover {
                background-color: #059669;
            }
            QPushButton#uploadBtn {
                background-color: #8b5cf6;
                font-size: 12px;
                padding: 6px 12px;
            }
            QPushButton#uploadBtn:hover {
                background-color: #7c3aed;
            }
            QComboBox {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
                color: #f8fafc;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #2563eb;
            }
            QProgressBar {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                text-align: center;
                color: white;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #10b981);
                border-radius: 7px;
            }
        """)

    def setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # LEFT PANEL
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        title_label = QLabel("🇻🇳 TKStug Studio - Dựng Video Lịch Sử & Kể Chuyện AI")
        title_label.setStyleSheet("font-size: 17px; font-weight: 900; color: #38bdf8;")
        left_layout.addWidget(title_label)

        sub_label = QLabel("Hỗ Trợ Video Dài 5 - 15 Phút, Tranh Phác Thảo Nét Chì & Quét Màu Nước Cổ Phong")
        sub_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        left_layout.addWidget(sub_label)

        script_group = QGroupBox("1. Kịch Bản Lịch Sử / Câu Chuyện Dài (5 - 15 Phút)")
        script_layout = QVBoxLayout(script_group)
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("Dán kịch bản lịch sử (dài 500 - 3000 từ) vào đây...")
        script_layout.addWidget(self.script_input)

        btn_row = QHBoxLayout()
        self.btn_auto_segment = QPushButton("⚡ Tự Động Phân Cảnh & Khớp Tranh Lịch Sử")
        self.btn_auto_segment.clicked.connect(self.on_auto_segment)
        btn_row.addWidget(self.btn_auto_segment)

        self.btn_sample_hist = QPushButton("Mẫu Lịch Sử")
        self.btn_sample_hist.setObjectName("secondaryBtn")
        self.btn_sample_hist.clicked.connect(self.load_sample_story)
        btn_row.addWidget(self.btn_sample_hist)

        self.btn_clear = QPushButton("Xóa")
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.script_input.clear)
        btn_row.addWidget(self.btn_clear)
        script_layout.addLayout(btn_row)
        left_layout.addWidget(script_group)

        storyboard_group = QGroupBox("2. Danh Sách Phân Cảnh (Storyboard)")
        sb_layout = QVBoxLayout(storyboard_group)
        self.scene_list = QListWidget()
        self.scene_list.currentRowChanged.connect(self.on_scene_selected)
        sb_layout.addWidget(self.scene_list)
        left_layout.addWidget(storyboard_group)

        splitter.addWidget(left_panel)

        # RIGHT PANEL
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        preview_group = QGroupBox("3. Màn Hình Xem Trước Nét Vẽ & Quét Màu (Live Player)")
        prev_layout = QVBoxLayout(preview_group)

        self.canvas_widget = WhiteboardCanvasWidget()
        prev_layout.addWidget(self.canvas_widget)

        prev_ctrl = QHBoxLayout()
        self.btn_play_preview = QPushButton("▶️ Nghe & Xem Vẽ Cảnh Này")
        self.btn_play_preview.setObjectName("playBtn")
        self.btn_play_preview.clicked.connect(self.on_play_preview)
        prev_ctrl.addWidget(self.btn_play_preview)

        self.btn_pause_preview = QPushButton("⏸️ Dừng")
        self.btn_pause_preview.setObjectName("secondaryBtn")
        self.btn_pause_preview.clicked.connect(self.canvas_widget.pause_preview)
        prev_ctrl.addWidget(self.btn_pause_preview)

        prev_ctrl.addWidget(QLabel("Tranh:"))
        self.cb_artwork = QComboBox()
        self.cb_artwork.currentIndexChanged.connect(self.on_artwork_changed)
        prev_ctrl.addWidget(self.cb_artwork)

        self.btn_upload_img = QPushButton("📁 Tải Ảnh Riêng")
        self.btn_upload_img.setObjectName("uploadBtn")
        self.btn_upload_img.clicked.connect(self.on_upload_custom_image)
        prev_ctrl.addWidget(self.btn_upload_img)

        prev_layout.addLayout(prev_ctrl)

        self.scene_text_edit = QTextEdit()
        self.scene_text_edit.setMaximumHeight(65)
        self.scene_text_edit.setPlaceholderText("Nội dung câu của phân cảnh đang chọn...")
        self.scene_text_edit.textChanged.connect(self.on_scene_text_changed)
        prev_layout.addWidget(self.scene_text_edit)

        right_layout.addWidget(preview_group)

        settings_group = QGroupBox("4. Cài Đặt Xuất Video MP4 Hoàn Chỉnh")
        st_layout = QVBoxLayout(settings_group)

        v_row = QHBoxLayout()
        v_row.addWidget(QLabel("🎙️ Giọng đọc AI (64 giọng):"))
        self.cb_voice = QComboBox()
        v_row.addWidget(self.cb_voice)
        st_layout.addLayout(v_row)

        tr_row = QHBoxLayout()
        tr_row.addWidget(QLabel("📜 Phong cách:"))
        self.cb_theme = QComboBox()
        self.cb_theme.addItem("📜 Giấy Cổ Điển Hoàng Triều (Vintage)", "vintage")
        self.cb_theme.addItem("📋 Bảng Trắng Nghệ Thuật (Whiteboard)", "whiteboard")
        self.cb_theme.addItem("🎓 Bảng Đen Phấn (Blackboard)", "blackboard")
        self.cb_theme.currentIndexChanged.connect(self.on_theme_changed)
        tr_row.addWidget(self.cb_theme)

        tr_row.addWidget(QLabel("📐 Định dạng:"))
        self.cb_ratio = QComboBox()
        self.cb_ratio.addItem("🖥️ 16:9 Ngang (YouTube 1080p)", (1920, 1080))
        self.cb_ratio.addItem("📱 9:16 Dọc (TikTok / Reels)", (1080, 1920))
        tr_row.addWidget(self.cb_ratio)
        st_layout.addLayout(tr_row)

        chk_row = QHBoxLayout()
        self.chk_hand = QCheckBox("Bàn tay vẽ nét chì & quét màu nước")
        self.chk_hand.setChecked(True)
        chk_row.addWidget(self.chk_hand)

        self.chk_camera = QCheckBox("Camera Pan & Zoom điện ảnh (Ken Burns)")
        self.chk_camera.setChecked(True)
        chk_row.addWidget(self.chk_camera)
        st_layout.addLayout(chk_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        st_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng xuất video...")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38bdf8;")
        st_layout.addWidget(self.lbl_status)

        self.btn_export = QPushButton("🚀 Xuất Toàn Bộ Video MP4 Lịch Sử Hoàn Chỉnh (Full HD)")
        self.btn_export.setObjectName("accentBtn")
        self.btn_export.clicked.connect(self.on_start_export)
        st_layout.addWidget(self.btn_export)

        right_layout.addWidget(settings_group)
        splitter.addWidget(right_panel)

        splitter.setSizes([450, 850])

    def populate_artworks(self):
        self.cb_artwork.blockSignals(True)
        self.cb_artwork.clear()
        
        artwork_items = [
            ("art_vn_quang_trung", "🇻🇳 [Lịch Sử] Vua Quang Trung Đại Phá Quân Thanh"),
            ("art_vn_bach_dang", "🇻🇳 [Lịch Sử] Trận Thủy Chiến Sông Bạch Đằng"),
            ("art_vn_trong_dong", "🇻🇳 [Lịch Sử] Trống Đồng Đông Sơn & Hùng Vương"),
            ("art_vn_hai_ba_trung", "🇻🇳 [Lịch Sử] Hai Bà Trưng Cưỡi Voi Ra Trận"),
            ("art_vn_dien_bien_phu", "🇻🇳 [Lịch Sử] Chiến Thắng Điện Biên Phủ"),
            ("art_vn_hoang_thanh", "🇻🇳 [Lịch Sử] Hoàng Thành Thăng Long & Cột Cờ"),
            ("art_vn_co_do_hue", "🇻🇳 [Lịch Sử] Cố Đô Huế & Ngọ Môn Hoàng Thành"),
            ("art_vn_ban_do", "🇻🇳 [Lịch Sử] Bản Đồ Non Sông Việt Nam"),
            ("art_growth_nature", "🌱 [Nghệ Thuật] Mầm Cây & Bình Minh"),
            ("art_idea_wisdom", "💡 [Nghệ Thuật] Bóng Đèn Trí Tuệ & Ý Tưởng"),
            ("art_mountain_peak", "🏔️ [Nghệ Thuật] Đỉnh Núi Vinh Quang"),
            ("art_time_hourglass", "⏳ [Nghệ Thuật] Đồng Hồ Cát Thời Gian"),
            ("art_book_knowledge", "📖 [Nghệ Thuật] Cuốn Sách & Tri Thức"),
            ("art_lighthouse_storm", "🗼 [Nghệ Thuật] Hải Đăng Vượt Bão Tố"),
            ("art_wealth_finance", "💰 [Nghệ Thuật] Tài Chính & Thịnh Vượng"),
            ("art_target_focus", "🎯 [Nghệ Thuật] Hồng Tâm & Mục Tiêu"),
            ("art_partnership_deal", "🤝 [Nghệ Thuật] Bắt Tay Hợp Tác"),
            ("art_rocket_breakthrough", "🚀 [Nghệ Thuật] Tên Lửa Bứt Phá"),
            ("art_trophy_glory", "🏆 [Nghệ Thuật] Chiếc Cúp Chiến Thắng"),
            ("art_gear_system", "⚙️ [Nghệ Thuật] Bánh Răng Hệ Thống"),
            ("art_shield_protection", "🛡️ [Nghệ Thuật] Khiên Chắn Bảo Vệ"),
            ("art_key_unlock", "🔑 [Nghệ Thuật] Chìa Khóa Giải Pháp"),
            ("art_growth_chart", "📈 [Nghệ Thuật] Biểu Đồ Tăng Trưởng"),
            ("art_puzzle_solution", "🧩 [Nghệ Thuật] Mảnh Ghép Vấn Đề"),
            ("art_chat_connection", "💬 [Nghệ Thuật] Giao Tiếp Thấu Hiểu"),
            ("art_coffee_peace", "☕ [Nghệ Thuật] Tách Cà Phê Bình Yên"),
            ("art_home_family", "🏡 [Nghệ Thuật] Ngôi Nhà & Gia Đình"),
            ("art_compass_journey", "🧭 [Nghệ Thuật] La Bàn Hành Trình"),
            ("art_fire_passion", "🔥 [Nghệ Thuật] Ngọn Lửa Đam Mê"),
            ("art_balance_scale", "⚖️ [Nghệ Thuật] Cán Cân Lựa Chọn"),
            ("art_person_thinking", "🤔 [Nghệ Thuật] Người Suy Ngẫm"),
            ("art_person_working", "💻 [Nghệ Thuật] Người Làm Việc Chăm Chỉ")
        ]
        
        for aid, title in artwork_items:
            self.cb_artwork.addItem(title, aid)
            
        self.cb_artwork.blockSignals(False)

    def populate_voices(self):
        self.cb_voice.clear()
        turbo_voices = []
        studio_voices = []

        for v in self.tts_engine.voices_data:
            v_id = v.get("id") or v.get("sample")
            name = v.get("name", "Giọng AI")
            tag = v.get("tag", "")
            gender = v.get("gender", "")
            icon = "👨" if "nam" in gender.lower() or "male" in str(v).lower() else "👩"

            if v.get("voice_type") == "turbo" or "Siêu Tốc" in name:
                turbo_voices.append((f"⚡ [SIÊU TỐC] {icon} {name}", v_id))
            else:
                studio_voices.append((f"💎 [STUDIO] {icon} {name} ({tag})", v_id))

        for title, vid in turbo_voices:
            self.cb_voice.addItem(title, vid)

        for title, vid in studio_voices:
            self.cb_voice.addItem(title, vid)

        if self.cb_voice.count() > 0:
            self.cb_voice.setCurrentIndex(0)

    def load_sample_story(self):
        sample = """Lịch sử hào hùng của dân tộc Việt Nam được dựng xây bằng máu, mồ hôi và lòng quả cảm của biết bao thế hệ tiền nhân.

Từ tiếng vang của tiếng Trống Đồng Đông Sơn thời các vua Hùng dựng nước Văn Lang, hào khí non sông đã chảy sâu vào huyết quản mỗi người con đất Việt.

Vào mùa đông năm 938, trên dòng sông Bạch Đằng lịch sử, Ngô Quyền đã cho bố trí trận địa cọc gỗ ngầm xé tan đoàn chiến thuyền Nam Hán, mở ra kỷ nguyên độc lập tự chủ lâu dài cho dân tộc.

Đến mùa xuân Kỷ Dậu năm 1789, người anh hùng áo vải cờ đào Nguyễn Huệ - Hoàng đế Quang Trung đã hành quân thần tốc đại phá 29 vạn quân Thanh, làm nên chiến thắng Ngọc Hồi - Đống Đa vang dội muôn đời.

Và trong thế kỷ hai mươi, chiến thắng Điện Biên Phủ lừng lẫy năm châu chấn động địa cầu đã khẳng định bản lĩnh kiên cường, khát vọng tự do cháy bỏng của đất nước Việt Nam."""
        self.script_input.setText(sample)
        self.on_auto_segment()

    def on_auto_segment(self):
        text = self.script_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa nhập văn bản", "Vui lòng dán văn bản kịch bản trước khi phân cảnh!")
            return

        self.current_scenes = self.scene_manager.segment_script_into_scenes(text)
        self.scene_list.clear()

        for s in self.current_scenes:
            item = QListWidgetItem(f"🎬 {s.title}\n   \"{s.text[:55]}...\"")
            self.scene_list.addItem(item)

        if self.current_scenes:
            self.scene_list.setCurrentRow(0)
            self.lbl_status.setText(f"Đã phân chia thành {len(self.current_scenes)} phân cảnh lịch sử hoàn chỉnh!")
            self.canvas_widget.set_scene(self.current_scenes[0], self.cb_theme.currentData())

    def on_scene_selected(self, row: int):
        if row < 0 or row >= len(self.current_scenes):
            return
        scene = self.current_scenes[row]
        self.scene_text_edit.blockSignals(True)
        self.scene_text_edit.setText(scene.text)
        self.scene_text_edit.blockSignals(False)

        # Select corresponding artwork in combo
        art_id = getattr(scene, "artwork_id", "art_vn_quang_trung")
        found = False
        for i in range(self.cb_artwork.count()):
            if self.cb_artwork.itemData(i) == art_id:
                self.cb_artwork.blockSignals(True)
                self.cb_artwork.setCurrentIndex(i)
                self.cb_artwork.blockSignals(False)
                found = True
                break

        if not found and os.path.exists(art_id):
            # Custom image item
            self.cb_artwork.blockSignals(True)
            custom_title = f"🖼️ [Ảnh Riêng] {os.path.basename(art_id)}"
            self.cb_artwork.addItem(custom_title, art_id)
            self.cb_artwork.setCurrentIndex(self.cb_artwork.count() - 1)
            self.cb_artwork.blockSignals(False)

        self.canvas_widget.set_scene(scene, self.cb_theme.currentData())

    def on_play_preview(self):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            scene = self.current_scenes[row]
            voice_id = self.cb_voice.currentData()
            self.lbl_status.setText("Đang chuẩn bị giọng đọc xem trước...")

            def synth_and_play():
                if not scene.audio_path or not os.path.exists(scene.audio_path):
                    audio_p, dur = self.tts_engine.synthesize(scene.text, voice_id=voice_id)
                    scene.audio_path = audio_p
                    scene.duration = max(dur, 2.5)
                else:
                    dur = scene.duration
                    audio_p = scene.audio_path
                self.signals.preview_ready.emit(row, audio_p, dur)

            threading.Thread(target=synth_and_play, daemon=True).start()

    def _handle_preview_ready(self, row: int, audio_p: str, dur: float):
        """Thread-safe handler executing on Main GUI Thread"""
        if 0 <= row < len(self.current_scenes):
            scene = self.current_scenes[row]
            self.canvas_widget.set_scene(scene, self.cb_theme.currentData())
            self.canvas_widget.start_preview(audio_p, dur)
            self.lbl_status.setText(f"Đang phát xem trước Cảnh {row+1} ({dur:.1f}s)...")

    def on_scene_text_changed(self):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            new_text = self.scene_text_edit.toPlainText().strip()
            self.current_scenes[row].text = new_text
            self.current_scenes[row].audio_path = None
            self.canvas_widget.current_scene.text = new_text
            self.canvas_widget.update()

    def on_artwork_changed(self, idx: int):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            art_id = self.cb_artwork.itemData(idx)
            self.current_scenes[row].artwork_id = art_id
            self.canvas_widget.set_scene(self.current_scenes[row], self.cb_theme.currentData())

    def on_upload_custom_image(self):
        row = self.scene_list.currentRow()
        if row < 0 or row >= len(self.current_scenes):
            QMessageBox.warning(self, "Chưa chọn cảnh", "Vui lòng chọn một phân cảnh trước khi tải ảnh!")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn bức ảnh tư liệu lịch sử của bạn",
            os.path.expanduser("~"),
            "Image Files (*.png *.jpg *.jpeg *.webp *.bmp)"
        )

        if file_path:
            self.current_scenes[row].artwork_id = file_path
            custom_title = f"🖼️ [Ảnh Riêng] {os.path.basename(file_path)}"
            self.cb_artwork.blockSignals(True)
            self.cb_artwork.addItem(custom_title, file_path)
            self.cb_artwork.setCurrentIndex(self.cb_artwork.count() - 1)
            self.cb_artwork.blockSignals(False)

            self.canvas_widget.set_scene(self.current_scenes[row], self.cb_theme.currentData())
            self.lbl_status.setText(f"Đã nạp ảnh tư liệu cho Cảnh {row+1}: {os.path.basename(file_path)}")

    def on_theme_changed(self, idx: int):
        theme = self.cb_theme.currentData()
        if self.canvas_widget.current_scene:
            self.canvas_widget.set_scene(self.canvas_widget.current_scene, theme)

    def on_start_export(self):
        if not self.current_scenes:
            QMessageBox.warning(self, "Chưa có phân cảnh", "Vui lòng phân cảnh kịch bản trước khi xuất video!")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu File Video MP4 Lịch Sử",
            os.path.join(os.path.expanduser("~"), "Desktop", "Video_Lich_Su_Viet_Nam.mp4"),
            "Video Files (*.mp4)"
        )

        if not save_path:
            return

        self.btn_export.setEnabled(False)
        self.btn_auto_segment.setEnabled(False)
        self.progress_bar.setValue(0)

        theme = self.cb_theme.currentData()
        resolution = self.cb_ratio.currentData()
        voice_id = self.cb_voice.currentData()

        self.worker_signals = WorkerSignals()
        self.worker_signals.progress.connect(self.on_render_progress)
        self.worker_signals.finished.connect(self.on_render_finished)

        def run_render():
            try:
                def p_cb(pct, status_text):
                    self.worker_signals.progress.emit(pct, status_text)

                for s in self.current_scenes:
                    s.audio_path = None

                original_synth = self.tts_engine.synthesize
                def custom_synth(txt, **kwargs):
                    return original_synth(txt, voice_id=voice_id)
                self.video_renderer.tts_engine.synthesize = custom_synth

                ok = self.video_renderer.render_full_story(
                    self.current_scenes,
                    save_path,
                    resolution=resolution,
                    theme=theme,
                    progress_callback=p_cb
                )
                self.worker_signals.finished.emit(ok, save_path)
            except Exception as e:
                self.worker_signals.finished.emit(False, str(e))

        t = threading.Thread(target=run_render, daemon=True)
        t.start()

    def on_render_progress(self, pct: int, text: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(text)

    def on_render_finished(self, success: bool, msg: str):
        self.btn_export.setEnabled(True)
        self.btn_auto_segment.setEnabled(True)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_status.setText("Xuất Video Lịch Sử thành công 100%! 🎉")
            ret = QMessageBox.information(
                self,
                "Hoàn Thành Xuất Video!",
                f"Video Lịch Sử của bạn đã được xuất thành công tại:\n\n{msg}\n\nBạn có muốn mở thư mục chứa video không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                os.startfile(os.path.dirname(msg))
        else:
            self.lbl_status.setText("Có lỗi xảy ra khi xuất video.")
            QMessageBox.critical(self, "Lỗi Xuất Video", f"Quá trình dựng video gặp sự cố:\n{msg}")
