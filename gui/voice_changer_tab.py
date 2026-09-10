import os
import sys
import uuid
import shutil
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QSplitter, QTextEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from backend.tts_engine import WhiteboardTTSEngine

class VoiceSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

class CelebrityVoiceChangerTab(QWidget):
    """
    100% Genuine Ready-to-Use Celebrity & Iconic Voices Studio:
    - Pre-trained, highly recognizable authentic voices
    - Instant demo playback & custom text synthesis
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tts = WhiteboardTTSEngine()
        self.temp_dir = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "celebrity_voice_studio")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.output_file_path = None

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)

        self.signals = VoiceSignals()
        self.signals.progress.connect(self.on_progress)
        self.signals.finished.connect(self.on_finished)

        self.ready_voices = [
            {
                "id": "tao-thao",
                "name": "👑 Tào Tháo (Lồng Tiếng Tam Quốc Diễn Nghĩa)",
                "sample_text": "Ta thà phụ người trong thiên hạ, chứ không để người trong thiên hạ phụ ta! Kẻ thức thời mới là trang tuấn kiệt!",
                "desc": "Giọng lồng tiếng phim Tam Quốc kinh điển: Trầm hùng, uy nghiêm, dứt khoát, khí phách quyền lực."
            },
            {
                "id": "ngoc-ngan-ke-chuyen-vbee",
                "name": "🎙️ Nguyễn Ngọc Ngạn (Kể Chuyện Đêm Khuya / Truyện Ma)",
                "sample_text": "Kính thưa quý vị, đêm nay trời đầy sương lạnh, câu chuyện rùng rợn bắt đầu tại một ngôi làng cổ...",
                "desc": "Chất giọng miền Bắc ma mị, trầm ấm, dẫn chuyện lôi cuốn bậc nhất của MC Nguyễn Ngọc Ngạn."
            },
            {
                "id": "theanh28-nu",
                "name": "📰 THEANH28 (Nữ Phát Thanh Bản Tin Hot Trend)",
                "sample_text": "Chào mừng các bạn đã quay trở lại với bản tin xu hướng nóng nhất trên mạng xã hội ngày hôm nay.",
                "desc": "Giọng nữ đọc tin tức triệu view: Trẻ trung, nhanh nhẹn, dứt khoát, cực kỳ cuốn hút."
            },
            {
                "id": "cuppy-vi",
                "name": "👧 Cuppy (Trợ Lý Ảo TikTok & Siêu Dễ Thương)",
                "sample_text": "Xin chào bạn! Mình là Cuppy, trợ lý ảo thông minh của bạn đây. Hôm nay bạn thấy thế nào?",
                "desc": "Giọng nữ trợ lý ảo ngọt ngào, tươi vui, thân thiện được yêu thích nhất."
            },
            {
                "id": "thien-tam-doc-truyen-vbee",
                "name": "🍃 Thiện Tâm (Đọc Truyện Miền Nam / Tâm Linh Phật Giáo)",
                "sample_text": "Vạn sự tùy duyên, tâm an vạn sự an. Cuộc đời như một dòng sông, hãy để tâm mình thanh tịnh.",
                "desc": "Chất giọng nam miền Nam sâu lắng, truyền cảm, an yên và thanh tịnh."
            },
            {
                "id": "turbo_namminh",
                "name": "📻 Nam Minh (Phát Thanh Viên Thời Sự VTV)",
                "sample_text": "Kính chào quý vị khán giả, sau đây là bản tin thời sự đặc biệt phát sóng trực tiếp trên đài truyền hình.",
                "desc": "Giọng nam phát thanh viên đài truyền hình quốc gia: Chuẩn xác, rõ ràng, sang trọng và chuẩn mực."
            },
            {
                "id": "turbo_hoaimy",
                "name": "🌸 Hoài My (Phát Thanh Viên Nữ Truyền Hình)",
                "sample_text": "Chào mừng quý vị và các bạn đã đến với chương trình văn hóa nghệ thuật và khám phá du lịch Việt Nam.",
                "desc": "Giọng nữ truyền hình mượt mà, trong trẻo, nhẹ nhàng và tự nhiên 100%."
            }
        ]

        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header Title
        header_box = QFrame()
        header_box.setStyleSheet("background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; padding: 10px;")
        h_layout = QVBoxLayout(header_box)
        h_layout.setContentsMargins(8, 8, 8, 8)
        
        lbl_title = QLabel("🎙️ STUDIO GIỌNG NÓI & NHÂN VẬT NỔI TIẾNG CÓ SẴN (GENUINE AI VOICES)")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        lbl_sub = QLabel("Tập hợp các mẫu giọng thật 100% đã được huấn luyện chuẩn xác (Tào Tháo, Nguyễn Ngọc Ngạn, Theanh28, Cuppy, Phát thanh viên VTV...).")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        main_layout.addWidget(header_box)

        # Splitter Layout (Left: Voice List & Samples, Right: Custom Text & Synthesis)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL: Voice Selector ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(10)

        voice_grp = QGroupBox("1. Danh Sách Giọng Nổi Tiếng Có Sẵn (Chọn Để Dùng Ngay)")
        voice_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        vg_layout = QVBoxLayout(voice_grp)

        self.voice_list = QListWidget()
        self.voice_list.setStyleSheet("""
            QListWidget {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                font-size: 13px;
                padding: 4px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1e293b;
                border-radius: 4px;
                margin-bottom: 2px;
            }
            QListWidget::item:selected {
                background: #0284c7;
                color: #ffffff;
                font-weight: bold;
            }
            QListWidget::item:hover:!selected {
                background: #1e293b;
            }
        """)

        for v in self.ready_voices:
            self.voice_list.addItem(f"{v['name']}")

        self.voice_list.currentRowChanged.connect(self.on_voice_selected)
        vg_layout.addWidget(self.voice_list)

        self.lbl_voice_desc = QLabel(self.ready_voices[0]["desc"])
        self.lbl_voice_desc.setStyleSheet("background: #1e293b; color: #a5f3fc; border-radius: 6px; padding: 10px; font-size: 11px;")
        self.lbl_voice_desc.setWordWrap(True)
        vg_layout.addWidget(self.lbl_voice_desc)

        left_layout.addWidget(voice_grp)
        splitter.addWidget(left_widget)

        # --- RIGHT PANEL: Text & Synthesis ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.setSpacing(10)

        input_grp = QGroupBox("2. Nhập Lời Bài Hát Hoặc Văn Bản Bạn Muốn Nhân Vật Nói")
        input_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        ig_layout = QVBoxLayout(input_grp)

        self.txt_input = QTextEdit()
        self.txt_input.setPlainText(self.ready_voices[0]["sample_text"])
        self.txt_input.setStyleSheet("background: #0f172a; color: white; border: 1px solid #334155; border-radius: 6px; padding: 10px; font-size: 13px;")
        self.txt_input.setFixedHeight(140)
        ig_layout.addWidget(self.txt_input)

        btn_sample_row = QHBoxLayout()
        btn_load_sample = QPushButton("📝 Dùng Câu Thoại Mẫu Của Nhân Vật")
        btn_load_sample.setStyleSheet("background: #334155; color: #e2e8f0; padding: 6px 12px; border-radius: 5px;")
        btn_load_sample.clicked.connect(self.on_load_sample_text)
        btn_sample_row.addWidget(btn_load_sample)
        btn_sample_row.addStretch()
        ig_layout.addLayout(btn_sample_row)

        right_layout.addWidget(input_grp)

        # Action Group
        act_grp = QGroupBox("3. Tạo Âm Thanh & Nghe Thử")
        act_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        ag_layout = QVBoxLayout(act_grp)

        self.btn_create = QPushButton("⚡ BẤM ĐỂ TẠO GIỌNG NHÂN VẬT NÀY NGAY (1-2 GIÂY)")
        self.btn_create.setStyleSheet("background: #f59e0b; color: #000; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 8px;")
        self.btn_create.clicked.connect(self.on_create_voice)
        ag_layout.addWidget(self.btn_create)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1e293b; border-radius: 6px; text-align: center; color: white; } QProgressBar::chunk { background: #38bdf8; border-radius: 6px; }")
        ag_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng tạo giọng...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        ag_layout.addWidget(self.lbl_status)

        out_btn_row = QHBoxLayout()
        self.btn_play = QPushButton("▶ Nghe Thử Giọng AI Ngay")
        self.btn_play.setStyleSheet("background: #10b981; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px; font-size: 13px;")
        self.btn_play.setEnabled(False)
        self.btn_play.clicked.connect(self.on_play_audio)
        out_btn_row.addWidget(self.btn_play)

        self.btn_save = QPushButton("💾 Lưu File MP3 Về Máy")
        self.btn_save.setStyleSheet("background: #0284c7; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px; font-size: 13px;")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.on_save_audio)
        out_btn_row.addWidget(self.btn_save)

        ag_layout.addLayout(out_btn_row)
        right_layout.addWidget(act_grp)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        splitter.setSizes([450, 650])
        main_layout.addWidget(splitter)

        self.voice_list.setCurrentRow(0)

    def on_voice_selected(self, row: int):
        if 0 <= row < len(self.ready_voices):
            v = self.ready_voices[row]
            self.lbl_voice_desc.setText(v["desc"])

    def on_load_sample_text(self):
        row = self.voice_list.currentRow()
        if 0 <= row < len(self.ready_voices):
            self.txt_input.setPlainText(self.ready_voices[row]["sample_text"])

    def on_create_voice(self):
        text = self.txt_input.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Chưa Nhập Văn Bản", "Vui lòng nhập lời bài hát hoặc câu nói bạn muốn nghe!")
            return

        row = self.voice_list.currentRow()
        if row < 0 or row >= len(self.ready_voices):
            row = 0
        v_info = self.ready_voices[row]
        voice_id = v_info["id"]

        self.btn_create.setEnabled(False)
        self.progress_bar.setValue(0)
        self.lbl_status.setText(f"Đang tạo giọng AI: {v_info['name']}...")

        temp_out = os.path.join(self.temp_dir, f"voice_{voice_id}_{uuid.uuid4().hex[:6]}.mp3")

        def run():
            try:
                self.signals.progress.emit(40, "Đang kết nối mô hình AI...")
                p, dur = self.tts.synthesize(text, voice_id=voice_id, output_path=temp_out)
                self.signals.progress.emit(100, "Hoàn tất!")
                self.signals.finished.emit(True, temp_out)
            except Exception as e:
                self.signals.finished.emit(False, str(e))

        t = threading.Thread(target=run, daemon=True)
        t.start()

    def on_progress(self, pct: int, text: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(text)

    def on_finished(self, success: bool, msg: str):
        self.btn_create.setEnabled(True)

        if success:
            self.output_file_path = msg
            self.btn_play.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.progress_bar.setValue(100)
            self.lbl_status.setText("🎉 Đã tạo xong giọng AI! Bấm 'Nghe Thử' bên dưới để thưởng thức.")
            # Auto play immediately so user hears it instantly!
            self.on_play_audio()
        else:
            self.lbl_status.setText("Có lỗi xảy ra.")
            QMessageBox.critical(self, "Lỗi Tạo Giọng", f"Không thể tạo giọng:\n{msg}")

    def on_play_audio(self):
        if self.output_file_path and os.path.exists(self.output_file_path):
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.btn_play.setText("▶ Nghe Lại Giọng AI")
            else:
                self.player.setSource(QUrl.fromLocalFile(self.output_file_path))
                self.player.play()
                self.btn_play.setText("⏸ Tạm Dừng")

    def on_save_audio(self):
        if not self.output_file_path or not os.path.exists(self.output_file_path):
            return
        
        save_dest, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu File Âm Thanh Giọng AI",
            os.path.join(os.path.expanduser("~"), "Desktop", "Giong_AI_Nguoi_Noi_Tieng.mp3"),
            "MP3 Audio (*.mp3)"
        )
        if save_dest:
            shutil.copy2(self.output_file_path, save_dest)
            QMessageBox.information(self, "Đã Lưu Thành Công", f"Đã lưu file âm thanh tại:\n{save_dest}")
