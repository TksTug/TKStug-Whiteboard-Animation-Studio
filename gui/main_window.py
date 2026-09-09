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
from PyQt6.QtGui import QFont, QIcon, QColor, QPainter, QPen, QBrush, QPixmap, QPainterPath
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from backend.tts_engine import WhiteboardTTSEngine
from backend.scene_manager import SceneManager, StoryScene
from backend.drawing_templates import TEMPLATES
from backend.video_renderer import VideoRenderer, parse_svg_path

class WorkerSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    audio_ready = pyqtSignal(str, float)

class WhiteboardCanvasWidget(QWidget):
    """Live interactive preview player showing synchronized hand-drawing in real-time"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.current_scene: StoryScene = None
        self.theme = "whiteboard"
        self.progress = 0.0
        self.is_animating = False

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        hand_path = os.path.join(base_dir, "assets", "hands", "hand_marker.png")
        if os.path.exists(hand_path):
            self.hand_pixmap = QPixmap(hand_path)
        else:
            self.hand_pixmap = QPixmap(100, 100)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.on_tick)
        self.anim_duration_ms = 4500
        self.elapsed_ms = 0

        # Audio playback support for preview
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)

    def set_scene(self, scene: StoryScene, theme: str = "whiteboard"):
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

        self.timer.start(16)

    def pause_preview(self):
        self.is_animating = False
        self.timer.stop()
        self.player.pause()

    def on_tick(self):
        self.elapsed_ms += 16
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

        if self.theme == "whiteboard":
            painter.fillRect(0, 0, w, h, QColor(255, 255, 255))
            text_color = QColor(15, 23, 42)
            box_bg = QColor(241, 245, 249)
        elif self.theme == "vintage":
            painter.fillRect(0, 0, w, h, QColor(254, 243, 199))
            text_color = QColor(69, 26, 3)
            box_bg = QColor(250, 235, 195)
        else:
            painter.fillRect(0, 0, w, h, QColor(30, 41, 59))
            text_color = QColor(248, 250, 252)
            box_bg = QColor(15, 23, 42)

        painter.setPen(QPen(QColor(51, 65, 85, 100), 2))
        painter.drawRoundedRect(1, 1, w - 2, h - 2, 8, 8)

        if not self.current_scene:
            painter.setPen(QColor(148, 163, 184))
            painter.setFont(QFont("Segoe UI", 12))
            painter.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Màn hình xem trước trực tiếp (Live Preview)")
            return

        # Subtitle rounded banner
        quote = f'"{self.current_scene.text}"'
        font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font)
        sub_rect = QRectF(25, 10, w - 50, 52)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(box_bg))
        painter.drawRoundedRect(sub_rect, 8, 8)

        painter.setPen(text_color)
        painter.drawText(QRectF(35, 12, w - 70, 48), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, quote)

        paths_spec = self.current_scene.template["paths"]
        all_parsed_paths = []
        total_points = 0

        for p_spec in paths_spec:
            pts = parse_svg_path(p_spec["d"])
            all_parsed_paths.append((pts, p_spec))
            total_points += len(pts)

        svg_w, svg_h = 500, 300
        scale = min((w * 0.72) / svg_w, (h * 0.58) / svg_h)
        offset_x = (w - svg_w * scale) / 2
        offset_y = (h - svg_h * scale) / 2 + 25

        # Drawing pacing: complete strokes at 70% progress
        draw_progress = min(self.progress / 0.70, 1.0) if self.is_animating else (1.0 if self.progress == 0 else min(self.progress / 0.70, 1.0))
        drawn_points_target = int(draw_progress * total_points)
        cum_pts = 0
        active_tip_pos = None

        for pts, p_spec in all_parsed_paths:
            p_len = len(pts)
            color = QColor(p_spec.get("color", "#000000"))
            stroke_width = max(int(p_spec.get("width", 3) * scale * 0.75), 2)
            painter.setPen(QPen(color, stroke_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

            if drawn_points_target <= cum_pts:
                pass
            elif drawn_points_target >= cum_pts + p_len:
                qpath = QPainterPath()
                for i, (px, py) in enumerate(pts):
                    tx, ty = offset_x + px * scale, offset_y + py * scale
                    if i == 0:
                        qpath.moveTo(tx, ty)
                    else:
                        qpath.lineTo(tx, ty)
                painter.drawPath(qpath)
            else:
                drawn_in_this = drawn_points_target - cum_pts
                qpath = QPainterPath()
                for i in range(drawn_in_this):
                    px, py = pts[i]
                    tx, ty = offset_x + px * scale, offset_y + py * scale
                    if i == 0:
                        qpath.moveTo(tx, ty)
                    else:
                        qpath.lineTo(tx, ty)
                    if i == drawn_in_this - 1:
                        active_tip_pos = (tx, ty)
                painter.drawPath(qpath)

            cum_pts += p_len

        # Hand animation logic
        if self.is_animating and active_tip_pos:
            hw = int(140 * scale)
            hh = int(140 * scale)
            scaled_hand = self.hand_pixmap.scaled(hw, hh, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            tip_offset_x = int(17 * scale)
            tip_offset_y = int(17 * scale)

            if self.progress < 0.70:
                painter.drawPixmap(int(active_tip_pos[0] - tip_offset_x), int(active_tip_pos[1] - tip_offset_y), scaled_hand)
            elif 0.70 <= self.progress < 0.82:
                retreat = (self.progress - 0.70) / 0.12
                hx = int(active_tip_pos[0] - tip_offset_x + retreat * (w * 0.35))
                hy = int(active_tip_pos[1] - tip_offset_y + retreat * (h * 0.35))
                painter.drawPixmap(hx, hy, scaled_hand)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TKStug Whiteboard Studio - Dựng Video Hoạt Hình Vẽ Tay Khớp Giọng Đọc Sách AI (64+ Giọng)")
        self.resize(1320, 860)
        self.setMinimumSize(1080, 720)

        self.tts_engine = WhiteboardTTSEngine()
        self.scene_manager = SceneManager()
        self.video_renderer = VideoRenderer(self.tts_engine)
        self.current_scenes: list[StoryScene] = []

        self.setup_ui()
        self.apply_theme()
        self.populate_voices()
        self.populate_templates()
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
                padding: 6px 14px;
            }
            QPushButton#playBtn:hover {
                background-color: #059669;
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

        title_label = QLabel("🎬 TKStug Whiteboard Studio")
        title_label.setStyleSheet("font-size: 18px; font-weight: 900; color: #38bdf8;")
        left_layout.addWidget(title_label)

        sub_label = QLabel("Tự Động Bóc Tách Ý Kịch Bản & Khớp Nét Vẽ Hoạt Hình Chuẩn Xác")
        sub_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        left_layout.addWidget(sub_label)

        script_group = QGroupBox("1. Kịch Bản Sách / Câu Chuyện")
        script_layout = QVBoxLayout(script_group)
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("Dán đoạn văn bản sách hoặc kịch bản câu chuyện vào đây...")
        script_layout.addWidget(self.script_input)

        btn_row = QHBoxLayout()
        self.btn_auto_segment = QPushButton("⚡ Tự Động Phân Cảnh & Khớp Hình Vẽ")
        self.btn_auto_segment.clicked.connect(self.on_auto_segment)
        btn_row.addWidget(self.btn_auto_segment)

        self.btn_clear = QPushButton("Xóa Hết")
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

        preview_group = QGroupBox("3. Màn Hình Xem Trước & Khớp Giọng Đọc (Live Player)")
        prev_layout = QVBoxLayout(preview_group)

        self.canvas_widget = WhiteboardCanvasWidget()
        prev_layout.addWidget(self.canvas_widget)

        prev_ctrl = QHBoxLayout()
        self.btn_play_preview = QPushButton("▶️ Nghe & Xem Bút Vẽ Cảnh Này")
        self.btn_play_preview.setObjectName("playBtn")
        self.btn_play_preview.clicked.connect(self.on_play_preview)
        prev_ctrl.addWidget(self.btn_play_preview)

        self.btn_pause_preview = QPushButton("⏸️ Dừng")
        self.btn_pause_preview.setObjectName("secondaryBtn")
        self.btn_pause_preview.clicked.connect(self.canvas_widget.pause_preview)
        prev_ctrl.addWidget(self.btn_pause_preview)

        prev_ctrl.addWidget(QLabel("Hình vẽ khớp:"))
        self.cb_template = QComboBox()
        self.cb_template.currentIndexChanged.connect(self.on_template_changed)
        prev_ctrl.addWidget(self.cb_template)

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
        tr_row.addWidget(QLabel("🎨 Bảng vẽ:"))
        self.cb_theme = QComboBox()
        self.cb_theme.addItem("📋 Bảng Trắng (Whiteboard)", "whiteboard")
        self.cb_theme.addItem("🎓 Bảng Đen Phấn (Blackboard)", "blackboard")
        self.cb_theme.addItem("📜 Giấy Cổ Điển (Vintage)", "vintage")
        self.cb_theme.currentIndexChanged.connect(self.on_theme_changed)
        tr_row.addWidget(self.cb_theme)

        tr_row.addWidget(QLabel("📐 Định dạng:"))
        self.cb_ratio = QComboBox()
        self.cb_ratio.addItem("🖥️ 16:9 Ngang (YouTube 1080p)", (1920, 1080))
        self.cb_ratio.addItem("📱 9:16 Dọc (TikTok / Reels)", (1080, 1920))
        tr_row.addWidget(self.cb_ratio)
        st_layout.addLayout(tr_row)

        chk_row = QHBoxLayout()
        self.chk_hand = QCheckBox("Bàn tay người thật vẽ từng nét")
        self.chk_hand.setChecked(True)
        chk_row.addWidget(self.chk_hand)

        self.chk_sfx = QCheckBox("Hiệu ứng vẽ mượt mà")
        self.chk_sfx.setChecked(True)
        chk_row.addWidget(self.chk_sfx)
        st_layout.addLayout(chk_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        st_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng xuất video...")
        self.lbl_status.setStyleSheet("font-size: 11px; color: #38bdf8;")
        st_layout.addWidget(self.lbl_status)

        self.btn_export = QPushButton("🚀 Xuất Toàn Bộ Video MP4 Hoàn Chỉnh (Full HD)")
        self.btn_export.setObjectName("accentBtn")
        self.btn_export.clicked.connect(self.on_start_export)
        st_layout.addWidget(self.btn_export)

        right_layout.addWidget(settings_group)
        splitter.addWidget(right_panel)

        splitter.setSizes([450, 830])

    def populate_templates(self):
        self.cb_template.blockSignals(True)
        self.cb_template.clear()
        for t in TEMPLATES:
            self.cb_template.addItem(f"🎨 {t['name']}", t["id"])
        self.cb_template.blockSignals(False)

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
        sample = """Trong cuộc sống, mỗi thử thách xuất hiện đều mang theo một cơ hội để chúng ta trưởng thành. Khi bạn dám gieo mầm hy vọng vào mảnh đất cằn cỗi nhất, sự kiên trì sẽ nuôi dưỡng mầm xanh vươn lên mạnh mẽ.

Mỗi ý tưởng vĩ đại đều bắt nguồn từ một khoảnh khắc tò mò và dám nghĩ khác biệt. Đừng ngại thử thách và vượt qua những giới hạn thông thường để khám phá tiềm năng vô tận bên trong bạn.

Tài chính và sự giàu có không chỉ đến từ may mắn, mà là kết quả của việc xây dựng thói quen tiết kiệm và đầu tư thông minh mỗi ngày.

Khi bạn đặt ra mục tiêu rõ ràng và tập trung cao độ, bạn sẽ tìm thấy chiếc chìa khóa mở ra cánh cửa thành công và bước lên đỉnh vinh quang."""
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
            self.lbl_status.setText(f"Đã phân chia thành {len(self.current_scenes)} phân cảnh logic và khớp hình vẽ chính xác!")
            self.canvas_widget.set_scene(self.current_scenes[0], self.cb_theme.currentData())

    def on_scene_selected(self, row: int):
        if row < 0 or row >= len(self.current_scenes):
            return
        scene = self.current_scenes[row]
        self.scene_text_edit.blockSignals(True)
        self.scene_text_edit.setText(scene.text)
        self.scene_text_edit.blockSignals(False)

        for i in range(self.cb_template.count()):
            if self.cb_template.itemData(i) == scene.template["id"]:
                self.cb_template.blockSignals(True)
                self.cb_template.setCurrentIndex(i)
                self.cb_template.blockSignals(False)
                break

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
                return audio_p, dur

            def on_done():
                audio_p, dur = synth_and_play()
                self.canvas_widget.set_scene(scene, self.cb_theme.currentData())
                self.canvas_widget.start_preview(audio_p, dur)
                self.lbl_status.setText(f"Đang phát xem trước Cảnh {row+1} ({dur:.1f}s)...")

            threading.Thread(target=on_done, daemon=True).start()

    def on_scene_text_changed(self):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            new_text = self.scene_text_edit.toPlainText().strip()
            self.current_scenes[row].text = new_text
            self.current_scenes[row].audio_path = None
            self.canvas_widget.current_scene.text = new_text
            self.canvas_widget.update()

    def on_template_changed(self, idx: int):
        row = self.scene_list.currentRow()
        if 0 <= row < len(self.current_scenes):
            tmpl_id = self.cb_template.itemData(idx)
            for t in TEMPLATES:
                if t["id"] == tmpl_id:
                    self.current_scenes[row].template = t
                    short_name = t['name'].split('&')[0].strip()
                    self.current_scenes[row].title = f"Cảnh {row+1}: {short_name}"
                    # Update item text in list
                    item = self.scene_list.item(row)
                    if item:
                        item.setText(f"🎬 {self.current_scenes[row].title}\n   \"{self.current_scenes[row].text[:55]}...\"")
                    self.canvas_widget.set_scene(self.current_scenes[row], self.cb_theme.currentData())
                    break

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
            "Lưu File Video MP4",
            os.path.join(os.path.expanduser("~"), "Desktop", "Video_Whiteboard_Story.mp4"),
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
            self.lbl_status.setText("Xuất Video thành công 100%! 🎉")
            ret = QMessageBox.information(
                self,
                "Hoàn Thành Xuất Video!",
                f"Video Whiteboard Animation của bạn đã được xuất thành công tại:\n\n{msg}\n\nBạn có muốn mở thư mục chứa video không?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ret == QMessageBox.StandardButton.Yes:
                os.startfile(os.path.dirname(msg))
        else:
            self.lbl_status.setText("Có lỗi xảy ra khi xuất video.")
            QMessageBox.critical(self, "Lỗi Xuất Video", f"Quá trình dựng video gặp sự cố:\n{msg}")
