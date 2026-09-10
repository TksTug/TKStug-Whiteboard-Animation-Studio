import os
import sys
import threading
import subprocess
import math
import numpy as np
from PIL import Image

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QComboBox, QSlider, QProgressBar, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QGroupBox, QSplitter, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QRectF, QUrl
from PyQt6.QtGui import QFont, QColor, QPainter, QImage
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from backend.tts_engine import WhiteboardTTSEngine
from backend.scene_manager import SceneManager, StoryScene, ARTWORK_MAPPING
from backend.drawing_templates import TEMPLATES
from backend.artistic_sketch_engine import ArtisticSketchEngine
from backend.video_renderer import VideoRenderer
from backend.ai_art_generator import AIArtGenerator
from backend.utils import get_asset_path

class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    preview_ready = pyqtSignal(int, str, float)
    art_generated = pyqtSignal(int, str)

class WhiteboardCanvasWidget(QWidget):
    """Live interactive preview player showing multi-layer pencil sketch + watercolor inking in real-time"""
    scene_completed = pyqtSignal(int)
    progress_updated = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(340)
        self.current_scene: StoryScene = None
        self.theme = "vintage"
        self.progress = 0.0
        self.show_hand = True
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
            self.player.setPosition(0)
            self.player.play()

        self.timer.start(20)
        self.update()

    def pause_preview(self):
        self.is_animating = False
        self.timer.stop()
        self.player.pause()
        self.update()

    def seek_progress(self, val_ratio: float):
        self.progress = max(0.0, min(1.0, val_ratio))
        self.elapsed_ms = int(self.progress * self.anim_duration_ms)
        if self.player.duration() > 0:
            target_pos = int(self.progress * self.player.duration())
            self.player.setPosition(target_pos)
        self.update()

    def on_tick(self):
        self.elapsed_ms += 20
        self.progress = min(self.elapsed_ms / max(self.anim_duration_ms, 1), 1.0)
        self.progress_updated.emit(self.progress)
        self.update()
        if self.progress >= 1.0:
            self.is_animating = False
            self.timer.stop()
            cur_idx = getattr(self.current_scene, "scene_index", 0)
            self.scene_completed.emit(cur_idx)

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
        use_hand = getattr(self, "show_hand", True)
        frame_pil = self.artistic_engine.render_artistic_frame(
            art_id=art_id,
            progress=self.progress,
            width=w,
            height=h,
            sub_text=self.current_scene.text,
            hand_img=self.hand_pil if (self.is_animating and use_hand) else None,
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
        self.resize(1380, 910)
        self.setMinimumSize(1100, 750)

        self.tts_engine = WhiteboardTTSEngine()
        self.scene_manager = SceneManager()
        self.video_renderer = VideoRenderer(self.tts_engine)
        self.ai_art_generator = AIArtGenerator()
        self.current_scenes = []
        self.is_playing_all = False

        self.signals = WorkerSignals()
        self.signals.preview_ready.connect(self._handle_preview_ready)
        self.signals.art_generated.connect(self._handle_art_generated)

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
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 8px;
                font-size: 13px;
                selection-background-color: #38bdf8;
                selection-color: #0b1120;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #334155;
                border-radius: 6px;
                margin-bottom: 4px;
            }
            QListWidget::item:hover {
                background-color: #334155;
            }
            QListWidget::item:selected {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #64748b;
            }
            QPushButton:pressed {
                background-color: #0f172a;
            }
            QPushButton#primaryBtn {
                background-color: #0284c7;
                color: #ffffff;
                border: 1px solid #38bdf8;
            }
            QPushButton#primaryBtn:hover {
                background-color: #0369a1;
            }
            QPushButton#aiBtn {
                background-color: #9333ea;
                color: #ffffff;
                border: 1px solid #c084fc;
            }
            QPushButton#aiBtn:hover {
                background-color: #7e22ce;
            }
            QPushButton#playAllBtn {
                background-color: #8b5cf6;
                color: #ffffff;
                border: 1px solid #a78bfa;
                font-size: 13px;
            }
            QPushButton#playAllBtn:hover {
                background-color: #7c3aed;
            }
            QPushButton#playBtn {
                background-color: #10b981;
                color: #ffffff;
                border: 1px solid #34d399;
            }
            QPushButton#playBtn:hover {
                background-color: #059669;
            }
            QPushButton#accentBtn {
                background-color: #f59e0b;
                color: #000000;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid #fbbf24;
                padding: 12px;
            }
            QPushButton#accentBtn:hover {
                background-color: #d97706;
            }
            QPushButton#uploadBtn {
                background-color: #4338ca;
                color: #ffffff;
                border: 1px solid #6366f1;
            }
            QPushButton#uploadBtn:hover {
                background-color: #3730a3;
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #f8fafc;
                selection-background-color: #0284c7;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #334155;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #38bdf8;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #ffffff;
                border: 2px solid #0284c7;
                width: 16px;
                margin-top: -5px;
                margin-bottom: -5px;
                border-radius: 8px;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 6px;
                text-align: center;
                color: #ffffff;
                font-weight: bold;
                background-color: #1e293b;
            }
            QProgressBar::chunk {
                background-color: #0284c7;
                border-radius: 5px;
            }
            QCheckBox {
                color: #e2e8f0;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #1e293b;
            }
            QCheckBox::indicator:checked {
                background-color: #0284c7;
                border-color: #38bdf8;
            }
        """)

    def setup_ui(self):
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title_label = QLabel("✨ TKStug Whiteboard Animation Studio - Studio Hoạt Họa Lịch Sử 2D Nghệ Thuật (AI Masterpiece)")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # LEFT PANEL
        left_panel = QWidget(self.splitter)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        script_group = QGroupBox("1. Nhập Kịch Bản Câu Chuyện", left_panel)
        script_layout = QVBoxLayout(script_group)
        self.script_input = QTextEdit(script_group)
        self.script_input.setPlaceholderText("Dán hoặc gõ toàn bộ câu chuyện lịch sử / kịch bản tại đây...")
        script_layout.addWidget(self.script_input)

        btn_row = QHBoxLayout()
        self.btn_auto_segment = QPushButton("🪄 Phân Tích & Phân Cảnh", script_group)
        self.btn_auto_segment.setObjectName("primaryBtn")
        self.btn_auto_segment.clicked.connect(self.on_auto_segment)
        btn_row.addWidget(self.btn_auto_segment)

        self.btn_sample_hist = QPushButton("Mẫu Lịch Sử", script_group)
        self.btn_sample_hist.setObjectName("secondaryBtn")
        self.btn_sample_hist.clicked.connect(self.load_sample_story)
        btn_row.addWidget(self.btn_sample_hist)

        self.btn_clear = QPushButton("Xóa", script_group)
        self.btn_clear.setObjectName("secondaryBtn")
        self.btn_clear.clicked.connect(self.script_input.clear)
        btn_row.addWidget(self.btn_clear)
        script_layout.addLayout(btn_row)
        left_layout.addWidget(script_group)

        storyboard_group = QGroupBox("2. Danh Sách Phân Cảnh (Storyboard)", left_panel)
        sb_layout = QVBoxLayout(storyboard_group)
        self.scene_list = QListWidget(storyboard_group)
        self.scene_list.currentRowChanged.connect(self.on_scene_selected)
        sb_layout.addWidget(self.scene_list)

        sb_btn_row = QHBoxLayout()
        self.btn_ai_gen_all = QPushButton("✨ AI Vẽ Tranh Toàn Bộ Cảnh", storyboard_group)
        self.btn_ai_gen_all.setObjectName("aiBtn")
        self.btn_ai_gen_all.clicked.connect(self.on_ai_gen_all_scenes)
        sb_btn_row.addWidget(self.btn_ai_gen_all)
        sb_layout.addLayout(sb_btn_row)

        left_layout.addWidget(storyboard_group)

        self.splitter.addWidget(left_panel)

        # RIGHT PANEL
        right_panel = QWidget(self.splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        preview_group = QGroupBox("3. Màn Hình Xem Trước Nét Vẽ & Quét Màu (Live Player)", right_panel)
        prev_layout = QVBoxLayout(preview_group)

        self.canvas_widget = WhiteboardCanvasWidget(preview_group)
        self.canvas_widget.scene_completed.connect(self._on_scene_completed)
        self.canvas_widget.progress_updated.connect(self._on_canvas_progress_updated)
        prev_layout.addWidget(self.canvas_widget)

        # Seekbar Slider
        seek_layout = QHBoxLayout()
        self.lbl_time_cur = QLabel("00:00", preview_group)
        self.lbl_time_cur.setStyleSheet("font-size: 11px; color: #94a3b8;")
        seek_layout.addWidget(self.lbl_time_cur)

        self.slider_seek = QSlider(Qt.Orientation.Horizontal, preview_group)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setValue(0)
        self.slider_seek.sliderMoved.connect(self.on_slider_moved)
        seek_layout.addWidget(self.slider_seek)

        self.lbl_time_total = QLabel("00:00", preview_group)
        self.lbl_time_total.setStyleSheet("font-size: 11px; color: #94a3b8;")
        seek_layout.addWidget(self.lbl_time_total)
        prev_layout.addLayout(seek_layout)

        # Controls Row
        prev_ctrl = QHBoxLayout()
        self.btn_play_all = QPushButton("🎬 Phát Toàn Bộ Video", preview_group)
        self.btn_play_all.setObjectName("playAllBtn")
        self.btn_play_all.clicked.connect(self.on_play_all)
        prev_ctrl.addWidget(self.btn_play_all)

        self.btn_prev_scene = QPushButton("⏮️", preview_group)
        self.btn_prev_scene.setToolTip("Cảnh trước")
        self.btn_prev_scene.clicked.connect(self.on_prev_scene)
        prev_ctrl.addWidget(self.btn_prev_scene)

        self.btn_play_preview = QPushButton("▶️ Cảnh Này", preview_group)
        self.btn_play_preview.setObjectName("playBtn")
        self.btn_play_preview.clicked.connect(self.on_play_preview)
        prev_ctrl.addWidget(self.btn_play_preview)

        self.btn_next_scene = QPushButton("⏭️", preview_group)
        self.btn_next_scene.setToolTip("Cảnh tiếp theo")
        self.btn_next_scene.clicked.connect(self.on_next_scene)
        prev_ctrl.addWidget(self.btn_next_scene)

        self.btn_pause_preview = QPushButton("⏸️ Dừng", preview_group)
        self.btn_pause_preview.setObjectName("secondaryBtn")
        self.btn_pause_preview.clicked.connect(self.on_pause_clicked)
        prev_ctrl.addWidget(self.btn_pause_preview)

        self.btn_ai_gen_single = QPushButton("✨ AI Vẽ Cảnh Này", preview_group)
        self.btn_ai_gen_single.setObjectName("aiBtn")
        self.btn_ai_gen_single.clicked.connect(self.on_ai_gen_single_scene)
        prev_ctrl.addWidget(self.btn_ai_gen_single)

        prev_ctrl.addWidget(QLabel("Tranh:", preview_group))
        self.cb_artwork = QComboBox(preview_group)
        self.cb_artwork.currentIndexChanged.connect(self.on_artwork_changed)
        prev_ctrl.addWidget(self.cb_artwork)

        self.btn_upload_img = QPushButton("📁 Tải Ảnh", preview_group)
        self.btn_upload_img.setObjectName("uploadBtn")
        self.btn_upload_img.clicked.connect(self.on_upload_custom_image)
        prev_ctrl.addWidget(self.btn_upload_img)

        prev_layout.addLayout(prev_ctrl)

        self.scene_text_edit = QTextEdit(preview_group)
        self.scene_text_edit.setMaximumHeight(65)
        self.scene_text_edit.setPlaceholderText("Nội dung câu của phân cảnh đang chọn...")
        self.scene_text_edit.textChanged.connect(self.on_scene_text_changed)
        prev_layout.addWidget(self.scene_text_edit)

        right_layout.addWidget(preview_group)

        settings_group = QGroupBox("4. Cài Đặt Xuất Video MP4 Hoàn Chỉnh", right_panel)
        st_layout = QVBoxLayout(settings_group)

        v_row = QHBoxLayout()
        v_row.addWidget(QLabel("🎙️ Giọng đọc AI (64 giọng):", settings_group))
        self.cb_voice = QComboBox(settings_group)
        v_row.addWidget(self.cb_voice)
        st_layout.addLayout(v_row)

        tr_row = QHBoxLayout()
        tr_row.addWidget(QLabel("📜 Phong cách:", settings_group))
        self.cb_theme = QComboBox(settings_group)
        self.cb_theme.addItem("📜 Giấy Cổ Điển Hoàng Triều (Vintage)", "vintage")
        self.cb_theme.addItem("📋 Bảng Trắng Nghệ Thuật (Whiteboard)", "whiteboard")
        self.cb_theme.addItem("🎓 Bảng Đen Phấn (Blackboard)", "blackboard")
        self.cb_theme.currentIndexChanged.connect(self.on_theme_changed)
        tr_row.addWidget(self.cb_theme)

        tr_row.addWidget(QLabel("📐 Định dạng:", settings_group))
        self.cb_ratio = QComboBox(settings_group)
        self.cb_ratio.addItem("🖥️ 16:9 Ngang (YouTube 1080p)", (1920, 1080))
        self.cb_ratio.addItem("📱 9:16 Dọc (TikTok / Reels)", (1080, 1920))
        tr_row.addWidget(self.cb_ratio)
        st_layout.addLayout(tr_row)

        chk_row = QHBoxLayout()
        self.chk_hand = QCheckBox("Bàn tay vẽ nét chì & quét màu nước", settings_group)
        self.chk_hand.setChecked(True)
        self.chk_hand.toggled.connect(self.on_hand_toggled)
        chk_row.addWidget(self.chk_hand)

        self.chk_camera = QCheckBox("Camera Pan & Zoom điện ảnh (Ken Burns)", settings_group)
        self.chk_camera.setChecked(True)
        chk_row.addWidget(self.chk_camera)
        st_layout.addLayout(chk_row)

        self.progress_bar = QProgressBar(settings_group)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        st_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng xuất video...", settings_group)
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38bdf8;")
        st_layout.addWidget(self.lbl_status)

        self.btn_export = QPushButton("🚀 Xuất Toàn Bộ Video MP4 Lịch Sử Hoàn Chỉnh (Full HD)", settings_group)
        self.btn_export.setObjectName("accentBtn")
        self.btn_export.clicked.connect(self.on_start_export)
        st_layout.addWidget(self.btn_export)

        right_layout.addWidget(settings_group)
        self.splitter.addWidget(right_panel)

        self.splitter.setSizes([450, 850])
        self.main_layout.addWidget(self.splitter)

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
            ("art_growth_nature", "🌱 [Nghệ Thuật] Cây Trí Tuệ & Bình Minh"),
            ("art_idea_wisdom", "💡 [Nghệ Thuật] Bóng Đèn Ý Tưởng Vũ Trụ"),
            ("art_mountain_peak", "🏔️ [Nghệ Thuật] Đỉnh Núi Vinh Quang & Cực Quang"),
            ("art_book_knowledge", "📖 [Nghệ Thuật] Sử Ký Đại Nam & Tri Thức"),
            ("art_time_hourglass", "⏳ [Nghệ Thuật] Đồng Hồ Cát Thiên Hà Thời Gian")
        ]
        for aid, title in artwork_items:
            self.cb_artwork.addItem(title, aid)
        self.cb_artwork.blockSignals(False)

    def populate_voices(self):
        self.cb_voice.clear()
        target_idx = 0
        for idx, v in enumerate(self.tts_engine.voices_data):
            v_id = v.get("id", "")
            v_name = v.get("name", "Voice")
            if v_id == "tao-thao" or "Tào Tháo" in v_name:
                display = f"👑 {v_name} (Uy Nghiêm - Lịch Sử Hào Hùng)"
                target_idx = idx
            else:
                display = f"{v_name} ({v.get('gender', 'N/A')})"
            self.cb_voice.addItem(display, v_id)
        self.cb_voice.setCurrentIndex(target_idx)

    def load_sample_story(self):
        sample = (
            "Hơn bốn ngàn năm lịch sử dựng nước và giữ nước, mảnh đất hình chữ S đã tôi luyện nên ý chí quật cường và tinh thần bất khuất của dân tộc Việt Nam.

Từ thuở sơ khai của các vua Hùng dựng nước Văn Lang, tiếng Trống Đồng Đông Sơn trầm hùng vang vọng khắp núi sông, hun đúc nên nguồn cội thiêng liêng của dòng giống Tiên Rồng.

Mùa xuân năm bốn mươi, nợ nước thù nhà sục sôi, Hai Bà Trưng cưỡi voi phất cờ khởi nghĩa tại Mê Linh, tiếng hô xung trận chấn động bờ cõi, mở ra trang sử vẻ vang của người phụ nữ Việt Nam.

Đến năm chín trăm ba mươi tám, trên dòng sông Bạch Đằng cuộn sóng gầm vang, trận địa cọc gỗ ngầm của Ngô Quyền đã nhấn chìm chiến thuyền quân thù, chấm dứt hơn một ngàn năm Bắc thuộc.

Mùa thu năm một ngàn không trăm mười, vua Lý Thái Tổ nhìn thấy rồng vàng bay lên, quyết định ban Chiếu dời đô về Thăng Long, đặt nền móng ngàn năm văn hiến cho kinh đô nước Việt.

Vào thế kỷ thứ mười ba, trước vó ngựa hung tàn của đế chế Mông Nguyên, quân dân nhà Trần với hào khí Đông A rực lửa và lời thề Sát Thát đã ba lần quét sạch giặc ngoại xâm.

Nơi núi rừng Lam Sơn hiểm trở, Lê Lợi cùng Nguyễn Trãi nếm mật nằm gai mười năm trường kỳ, dùng thanh gươm Thuận Thiên dẹp tan quân Minh, lập lại nền thái bình muôn thuở.

Mùa xuân Kỷ Dậu năm một ngàn bảy trăm tám mươi chín, Hoàng đế Quang Trung mặc áo vải cờ đào thần tốc hành quân, đại phá hai mươi chín vạn quân Thanh tại Ngọc Hồi Đống Đa vang dội.

Bên dòng sông Hương thơ mộng, Cố Đô Huế sừng sững uy nghiêm với Ngọ Môn và cung điện cổ kính, lưu giữ tinh hoa kiến trúc cùng bản sắc văn hóa hoàng triều ngàn đời.

Tháng năm năm một ngàn chín trăm năm mươi tư, chiến dịch Điện Biên Phủ toàn thắng lừng lẫy năm châu chấn động địa cầu, khẳng định sức mạnh đại đoàn kết toàn dân.

Từ đỉnh đầu Lũng Cú Móng Cái đến mũi Cà Mau, cùng hai quần đảo Hoàng Sa và Trường Sa thiêng liêng, non sông Việt Nam liền một dải, chủ quyền lãnh thổ đời đời bất khả xâm phạm.

Kế thừa truyền thống kiên cường của cha ông, thế hệ hôm nay vững vàng bước vào kỷ nguyên mới, viết tiếp những trang sử vẻ vang đưa non sông Việt Nam vươn tầm thế giới."
        )
        self.script_input.setPlainText(sample)
        self.on_auto_segment()

    def on_auto_segment(self):
        text = self.script_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa nhập văn bản", "Vui lòng dán văn bản kịch bản trước khi phân cảnh!")
            return

        self.current_scenes = self.scene_manager.segment_script_into_scenes(text)
        self.scene_list.clear()

        for s in self.current_scenes:
            short_txt = s.text[:45].replace('\n', ' ')
            item_text = f"🎬 {s.title}\n   '{short_txt}...'"
            item = QListWidgetItem(item_text)
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
            self.cb_artwork.blockSignals(True)
            custom_title = f"🖼️ [Ảnh Riêng] {os.path.basename(art_id)}"
            self.cb_artwork.addItem(custom_title, art_id)
            self.cb_artwork.setCurrentIndex(self.cb_artwork.count() - 1)
            self.cb_artwork.blockSignals(False)

        self.canvas_widget.set_scene(scene, self.cb_theme.currentData())
        dur = scene.duration or 4.0
        self.lbl_time_total.setText(f"{int(dur // 60):02d}:{int(dur % 60):02d}")
        self.lbl_time_cur.setText("00:00")
        self.slider_seek.setValue(0)

    def on_ai_gen_single_scene(self):
        row = self.scene_list.currentRow()
        if row < 0 or row >= len(self.current_scenes):
            QMessageBox.warning(self, "Chưa chọn cảnh", "Vui lòng chọn một phân cảnh để tạo tranh!")
            return
        scene = self.current_scenes[row]
        self.lbl_status.setText(f"✨ AI đang vẽ tranh 2D anime cho Cảnh {row+1}...")
        self.btn_ai_gen_single.setEnabled(False)

        def run_ai():
            try:
                img_path = self.ai_art_generator.generate_art_for_text(scene.text)
                self.signals.art_generated.emit(row, img_path)
            except Exception as e:
                print(f"Error in AI Art generation: {e}")

        threading.Thread(target=run_ai, daemon=True).start()

    def on_ai_gen_all_scenes(self):
        if not self.current_scenes:
            QMessageBox.warning(self, "Chưa có phân cảnh", "Vui lòng phân cảnh kịch bản trước khi tạo tranh AI!")
            return
        self.lbl_status.setText("✨ AI đang vẽ tranh cho toàn bộ phân cảnh...")
        self.btn_ai_gen_all.setEnabled(False)

        def run_all_ai():
            for idx, sc in enumerate(self.current_scenes):
                try:
                    img_path = self.ai_art_generator.generate_art_for_text(sc.text)
                    self.signals.art_generated.emit(idx, img_path)
                except Exception as e:
                    print(f"Error generating art for scene {idx}: {e}")

        threading.Thread(target=run_all_ai, daemon=True).start()

    def _handle_art_generated(self, row: int, img_path: str):
        if 0 <= row < len(self.current_scenes):
            self.current_scenes[row].artwork_id = img_path
            if self.scene_list.currentRow() == row:
                custom_title = f"✨ [AI Art] {os.path.basename(img_path)}"
                self.cb_artwork.blockSignals(True)
                self.cb_artwork.addItem(custom_title, img_path)
                self.cb_artwork.setCurrentIndex(self.cb_artwork.count() - 1)
                self.cb_artwork.blockSignals(False)
                self.canvas_widget.set_scene(self.current_scenes[row], self.cb_theme.currentData())
            self.lbl_status.setText(f"✨ Đã tạo tranh AI thành công cho Cảnh {row+1}!")
        self.btn_ai_gen_single.setEnabled(True)
        self.btn_ai_gen_all.setEnabled(True)

    def on_play_all(self):
        if not self.current_scenes:
            return
        if self.is_playing_all:
            self.is_playing_all = False
            self.canvas_widget.pause_preview()
            self.btn_play_all.setText("🎬 Phát Toàn Bộ Video")
            self.lbl_status.setText("Đã tạm dừng phát toàn bộ.")
            return

        self.is_playing_all = True
        self.btn_play_all.setText("⏸️ Dừng Phát Toàn Bộ")
        cur_row = self.scene_list.currentRow()
        if cur_row < 0 or cur_row >= len(self.current_scenes):
            cur_row = 0
            self.scene_list.setCurrentRow(0)
        self.play_scene_at(cur_row, continue_all=True)

    def on_play_preview(self):
        self.is_playing_all = False
        self.btn_play_all.setText("🎬 Phát Toàn Bộ Video")
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            self.play_scene_at(row, continue_all=False)

    def play_scene_at(self, row: int, continue_all: bool = False):
        if row < 0 or row >= len(self.current_scenes):
            return
        scene = self.current_scenes[row]
        voice_id = self.cb_voice.currentData()
        self.lbl_status.setText(f"Đang chuẩn bị giọng đọc Cảnh {row+1}/{len(self.current_scenes)}...")

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
        if 0 <= row < len(self.current_scenes):
            scene = self.current_scenes[row]
            scene.duration = dur
            self.lbl_time_total.setText(f"{int(dur // 60):02d}:{int(dur % 60):02d}")
            self.canvas_widget.set_scene(scene, self.cb_theme.currentData())
            self.canvas_widget.start_preview(audio_p, dur)
            self.lbl_status.setText(f"Đang phát Cảnh {row+1}/{len(self.current_scenes)} ({dur:.1f}s)...")

    def _on_scene_completed(self, completed_idx: int):
        if self.is_playing_all:
            next_idx = completed_idx + 1
            if next_idx < len(self.current_scenes):
                self.scene_list.setCurrentRow(next_idx)
                self.play_scene_at(next_idx, continue_all=True)
            else:
                self.is_playing_all = False
                self.btn_play_all.setText("🎬 Phát Toàn Bộ Video")
                self.lbl_status.setText("Đã xem xong toàn bộ video! 🎉")

    def _on_canvas_progress_updated(self, progress: float):
        self.slider_seek.blockSignals(True)
        self.slider_seek.setValue(int(progress * 1000))
        self.slider_seek.blockSignals(False)
        dur = getattr(self.canvas_widget.current_scene, "duration", 4.0) if self.canvas_widget.current_scene else 4.0
        cur_sec = progress * dur
        self.lbl_time_cur.setText(f"{int(cur_sec // 60):02d}:{int(cur_sec % 60):02d}")

    def on_slider_moved(self, val: int):
        ratio = val / 1000.0
        self.canvas_widget.seek_progress(ratio)

    def on_prev_scene(self):
        cur_row = self.scene_list.currentRow()
        if cur_row > 0:
            self.scene_list.setCurrentRow(cur_row - 1)
            if self.is_playing_all or self.canvas_widget.is_animating:
                self.play_scene_at(cur_row - 1, continue_all=self.is_playing_all)

    def on_next_scene(self):
        cur_row = self.scene_list.currentRow()
        if cur_row < len(self.current_scenes) - 1:
            self.scene_list.setCurrentRow(cur_row + 1)
            if self.is_playing_all or self.canvas_widget.is_animating:
                self.play_scene_at(cur_row + 1, continue_all=self.is_playing_all)

    def on_pause_clicked(self):
        self.is_playing_all = False
        self.btn_play_all.setText("🎬 Phát Toàn Bộ Video")
        self.canvas_widget.pause_preview()
        self.lbl_status.setText("Đã tạm dừng xem trước.")

    def on_scene_text_changed(self):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            new_text = self.scene_text_edit.toPlainText().strip()
            self.current_scenes[row].text = new_text
            self.current_scenes[row].audio_path = None
            if self.canvas_widget.current_scene:
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

    def on_hand_toggled(self, checked: bool):
        self.canvas_widget.show_hand = checked
        self.canvas_widget.update()

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
        use_hand = self.chk_hand.isChecked()

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
                    use_hand=use_hand,
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
                folder = os.path.dirname(msg)
                if sys.platform == "win32":
                    os.startfile(folder)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", folder])
                else:
                    subprocess.Popen(["xdg-open", folder])
        else:
            self.lbl_status.setText("Có lỗi xảy ra trong quá trình xuất video.")
            QMessageBox.critical(self, "Lỗi Xuất Video", f"Không thể xuất video:\n{msg}")
