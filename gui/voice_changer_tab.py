import os
import sys
import uuid
import shutil
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QSlider, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QSplitter, QTextEdit, QRadioButton, QCheckBox,
    QLineEdit
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from backend.voice_changer_engine import VoiceChangerEngine

class VoiceSignals(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

class CelebrityVoiceChangerTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = VoiceChangerEngine()
        self.input_file_path = None
        self.output_file_path = None

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.durationChanged.connect(self.on_player_duration_changed)

        self.signals = VoiceSignals()
        self.signals.progress.connect(self.on_progress)
        self.signals.finished.connect(self.on_finished)

        self.setup_ui()
        self.refresh_model_dropdown()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(10)

        # Header Title
        header_box = QFrame()
        header_box.setStyleSheet("background: #0f172a; border-radius: 8px; border: 1px solid #1e293b; padding: 10px;")
        h_layout = QVBoxLayout(header_box)
        h_layout.setContentsMargins(8, 6, 8, 6)
        
        lbl_title = QLabel("🎵 RVC v2 AI COVER STUDIO - ĐỔI GIỌNG HÁT NGƯỜI NỔI TIẾNG")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        lbl_sub = QLabel("Tự động bóc tách Vocal & Beat -> Chuyển đổi giọng hát sang Sơn Tùng, Độ Mixi, Tào Tháo... qua mô hình RVC -> Hòa âm Studio 320kbps.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        main_layout.addWidget(header_box)

        # Mode Selection Bar
        mode_box = QFrame()
        mode_box.setStyleSheet("background: #1e293b; border-radius: 6px; padding: 6px;")
        m_layout = QHBoxLayout(mode_box)
        m_layout.setContentsMargins(8, 4, 8, 4)

        lbl_mode = QLabel("Chế Độ:")
        lbl_mode.setStyleSheet("font-weight: bold; color: #f8fafc; font-size: 13px;")
        m_layout.addWidget(lbl_mode)

        self.rb_mode_song = QRadioButton("🎵 1. RVC AI Cover Bài Hát (Tự Tách Beat + Đổi Giọng Ca Sĩ + Mix Lại)")
        self.rb_mode_song.setChecked(True)
        self.rb_mode_song.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.rb_mode_song.toggled.connect(self.on_mode_toggled)
        m_layout.addWidget(self.rb_mode_song)

        self.rb_mode_text = QRadioButton("✍️ 2. Tạo Giọng Đọc & Lồng Tiếng AI (Text-To-Speech)")
        self.rb_mode_text.setStyleSheet("color: #a78bfa; font-weight: bold; font-size: 13px;")
        self.rb_mode_text.toggled.connect(self.on_mode_toggled)
        m_layout.addWidget(self.rb_mode_text)

        m_layout.addStretch()
        main_layout.addWidget(mode_box)

        # Splitter Layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setSpacing(10)

        # 1. Input Group
        self.input_grp = QGroupBox("1. Nguồn Bài Hát / Âm Thanh Đầu Vào")
        self.input_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        self.ig_layout = QVBoxLayout(self.input_grp)

        # Song Mode widgets
        self.song_widget = QWidget()
        sw_layout = QVBoxLayout(self.song_widget)
        sw_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_select_file = QPushButton("📂 Tải Lên File Bài Hát Gốc (.mp3, .wav, .m4a, .flac)")
        self.btn_select_file.setStyleSheet("background: #2563eb; color: white; font-weight: bold; padding: 10px 14px; border-radius: 6px; font-size: 13px;")
        self.btn_select_file.clicked.connect(self.select_audio_file)
        sw_layout.addWidget(self.btn_select_file)

        self.lbl_selected_file = QLabel("Chưa chọn bài hát nào.")
        self.lbl_selected_file.setStyleSheet("color: #94a3b8; font-size: 12px; font-style: italic; padding: 2px;")
        self.lbl_selected_file.setWordWrap(True)
        sw_layout.addWidget(self.lbl_selected_file)

        self.ig_layout.addWidget(self.song_widget)

        # Text Mode widgets
        self.text_widget = QWidget()
        self.text_widget.setVisible(False)
        tw_layout = QVBoxLayout(self.text_widget)
        tw_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_text_hint = QLabel("Nhập kịch bản hoặc lời bài hát cần AI đọc / hát:")
        lbl_text_hint.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        tw_layout.addWidget(lbl_text_hint)

        self.txt_script = QTextEdit()
        self.txt_script.setPlaceholderText("Ví dụ: Kẻ thắng làm vua, kẻ thua làm giặc. Ta thà phụ người trong thiên hạ chứ không để người thiên hạ phụ ta...")
        self.txt_script.setStyleSheet("background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-radius: 6px; padding: 8px; font-size: 13px;")
        self.txt_script.setMinimumHeight(100)
        tw_layout.addWidget(self.txt_script)

        self.ig_layout.addWidget(self.text_widget)
        left_layout.addWidget(self.input_grp)

        # 2. Character / Model Selection Group
        self.char_grp = QGroupBox("2. Chọn Model Giọng Nhân Vật RVC")
        self.char_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        cg_layout = QVBoxLayout(self.char_grp)

        # Dropdown and Add custom model button
        combo_h = QHBoxLayout()
        self.cb_character = QComboBox()
        self.cb_character.setStyleSheet("background: #1e293b; color: #f8fafc; font-weight: bold; padding: 8px; border-radius: 6px; border: 1px solid #334155; font-size: 13px;")
        self.cb_character.currentIndexChanged.connect(self.on_character_changed)
        combo_h.addWidget(self.cb_character, 3)

        self.btn_import_model = QPushButton("➕ Thêm Model RVC")
        self.btn_import_model.setStyleSheet("background: #059669; color: white; font-weight: bold; padding: 8px 12px; border-radius: 6px; font-size: 12px;")
        self.btn_import_model.setToolTip("Nạp thêm file model .pth, .index hoặc .zip tải từ cộng đồng")
        self.btn_import_model.clicked.connect(self.import_custom_rvc_model)
        combo_h.addWidget(self.btn_import_model, 1)
        cg_layout.addLayout(combo_h)

        # Model Info display
        self.lbl_char_desc = QLabel()
        self.lbl_char_desc.setStyleSheet("background: #1e293b; color: #38bdf8; padding: 8px; border-radius: 6px; font-size: 12px; border: 1px solid #334155;")
        self.lbl_char_desc.setWordWrap(True)
        cg_layout.addWidget(self.lbl_char_desc)

        left_layout.addWidget(self.char_grp)

        # 3. Action Button
        self.btn_process = QPushButton("🚀 BẮT ĐẦU TẠO AI COVER (RVC)")
        self.btn_process.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed); color: white; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 8px;")
        self.btn_process.clicked.connect(self.start_processing)
        left_layout.addWidget(self.btn_process)

        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        self.pbar.setTextVisible(True)
        self.pbar.setStyleSheet("QProgressBar { background: #1e293b; border-radius: 6px; text-align: center; color: white; font-weight: bold; height: 20px; } QProgressBar::chunk { background: #38bdf8; border-radius: 6px; }")
        left_layout.addWidget(self.pbar)

        self.lbl_status = QLabel("Sẵn sàng.")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 12px; font-weight: bold;")
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # --- RIGHT PANEL (Tuning & Studio Controls) ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.setSpacing(10)

        # Pro Studio Tuning Group
        self.tune_grp = QGroupBox("⚙️ Tùy Chỉnh Tone & Hòa Âm (RVC Studio Tuning)")
        self.tune_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        tg_layout = QVBoxLayout(self.tune_grp)
        tg_layout.setSpacing(8)

        # Pitch Transpose
        h_pitch_lbl = QHBoxLayout()
        lbl_p = QLabel("Đổi Tone / Key (Pitch Shift):")
        lbl_p.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.lbl_pitch_val = QLabel("0 bán âm")
        self.lbl_pitch_val.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        h_pitch_lbl.addWidget(lbl_p)
        h_pitch_lbl.addWidget(self.lbl_pitch_val)
        tg_layout.addLayout(h_pitch_lbl)

        self.slider_pitch = QSlider(Qt.Orientation.Horizontal)
        self.slider_pitch.setRange(-24, 24)
        self.slider_pitch.setValue(0)
        self.slider_pitch.valueChanged.connect(self.on_pitch_slider_changed)
        tg_layout.addWidget(self.slider_pitch)

        # Quick Key buttons
        quick_key_layout = QHBoxLayout()
        btn_female_to_male = QPushButton("Nữ ➔ Nam (-12)")
        btn_female_to_male.setStyleSheet("background: #334155; color: #cbd5e1; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        btn_female_to_male.clicked.connect(lambda: self.slider_pitch.setValue(-12))
        quick_key_layout.addWidget(btn_female_to_male)

        btn_same_gender = QPushButton("Cùng Giới (0)")
        btn_same_gender.setStyleSheet("background: #334155; color: #cbd5e1; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        btn_same_gender.clicked.connect(lambda: self.slider_pitch.setValue(0))
        quick_key_layout.addWidget(btn_same_gender)

        btn_male_to_female = QPushButton("Nam ➔ Nữ (+12)")
        btn_male_to_female.setStyleSheet("background: #334155; color: #cbd5e1; font-size: 11px; padding: 4px 8px; border-radius: 4px;")
        btn_male_to_female.clicked.connect(lambda: self.slider_pitch.setValue(12))
        quick_key_layout.addWidget(btn_male_to_female)
        tg_layout.addLayout(quick_key_layout)

        # Pitch Algorithm selector
        h_algo = QHBoxLayout()
        lbl_algo = QLabel("Thuật toán Pitch:")
        lbl_algo.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.cb_pitch_algo = QComboBox()
        self.cb_pitch_algo.addItems(["RMVPE (Chuẩn nhất - Không lạc giọng)", "PM (Nhanh)", "Harvest (Chi tiết)", "Crepe (Mượt)"])
        self.cb_pitch_algo.setStyleSheet("background: #1e293b; color: #38bdf8; padding: 4px 8px; border-radius: 4px; border: 1px solid #334155; font-size: 12px;")
        h_algo.addWidget(lbl_algo)
        h_algo.addWidget(self.cb_pitch_algo)
        tg_layout.addLayout(h_algo)

        # Index Feature Rate
        h_index_lbl = QHBoxLayout()
        lbl_idx = QLabel("Tỷ lệ đặc trưng giọng (Index Rate):")
        lbl_idx.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.lbl_index_val = QLabel("0.80")
        self.lbl_index_val.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        h_index_lbl.addWidget(lbl_idx)
        h_index_lbl.addWidget(self.lbl_index_val)
        tg_layout.addLayout(h_index_lbl)

        self.slider_index = QSlider(Qt.Orientation.Horizontal)
        self.slider_index.setRange(0, 100)
        self.slider_index.setValue(80)
        self.slider_index.valueChanged.connect(lambda v: self.lbl_index_val.setText(f"{v/100.0:.2f}"))
        tg_layout.addWidget(self.slider_index)

        # Volume Controls
        h_vocal_lbl = QHBoxLayout()
        lbl_v = QLabel("Âm Lượng Giọng Hát AI (Vocal):")
        lbl_v.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.lbl_vocal_val = QLabel("100%")
        self.lbl_vocal_val.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        h_vocal_lbl.addWidget(lbl_v)
        h_vocal_lbl.addWidget(self.lbl_vocal_val)
        tg_layout.addLayout(h_vocal_lbl)

        self.slider_vocal = QSlider(Qt.Orientation.Horizontal)
        self.slider_vocal.setRange(0, 200)
        self.slider_vocal.setValue(100)
        self.slider_vocal.valueChanged.connect(lambda v: self.lbl_vocal_val.setText(f"{v}%"))
        tg_layout.addWidget(self.slider_vocal)

        h_beat_lbl = QHBoxLayout()
        lbl_b = QLabel("Âm Lượng Nhạc Nền (Beat):")
        lbl_b.setStyleSheet("color: #f8fafc; font-size: 12px;")
        self.lbl_beat_val = QLabel("100%")
        self.lbl_beat_val.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 12px;")
        h_beat_lbl.addWidget(lbl_b)
        h_beat_lbl.addWidget(self.lbl_beat_val)
        tg_layout.addLayout(h_beat_lbl)

        self.slider_beat = QSlider(Qt.Orientation.Horizontal)
        self.slider_beat.setRange(0, 200)
        self.slider_beat.setValue(100)
        self.slider_beat.valueChanged.connect(lambda v: self.lbl_beat_val.setText(f"{v}%"))
        tg_layout.addWidget(self.slider_beat)

        right_layout.addWidget(self.tune_grp)

        # Audio Output Player Group
        self.player_grp = QGroupBox("🎧 Nghe Thử & Xuất File Hoàn Chỉnh")
        self.player_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        pg_layout = QVBoxLayout(self.player_grp)

        self.lbl_now_playing = QLabel("Chưa có bản ghi nào được tạo.")
        self.lbl_now_playing.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.lbl_now_playing.setWordWrap(True)
        pg_layout.addWidget(self.lbl_now_playing)

        # Player transport bar
        player_bar = QHBoxLayout()
        self.btn_play_pause = QPushButton("▶ Phát Nhạc")
        self.btn_play_pause.setStyleSheet("background: #059669; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_play_pause.setEnabled(False)
        player_bar.addWidget(self.btn_play_pause)

        self.btn_open_folder = QPushButton("📂 Mở Thư Mục")
        self.btn_open_folder.setStyleSheet("background: #334155; color: #f8fafc; padding: 8px 12px; border-radius: 6px;")
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        self.btn_open_folder.setEnabled(False)
        player_bar.addWidget(self.btn_open_folder)
        pg_layout.addLayout(player_bar)

        self.seek_slider = QSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 100)
        self.seek_slider.sliderMoved.connect(self.set_player_position)
        pg_layout.addWidget(self.seek_slider)

        right_layout.addWidget(self.player_grp)
        right_layout.addStretch()
        splitter.addWidget(right_widget)

        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        main_layout.addWidget(splitter)

    def refresh_model_dropdown(self):
        self.cb_character.clear()
        all_presets = self.engine.celebrity_presets + self.engine.scan_custom_models()
        for p in all_presets:
            self.cb_character.addItem(p["name"], p["id"])
        self.on_character_changed(0)

    def on_character_changed(self, index):
        char_id = self.cb_character.currentData()
        all_presets = self.engine.celebrity_presets + self.engine.scan_custom_models()
        char = next((p for p in all_presets if p["id"] == char_id), None)
        if char:
            self.lbl_char_desc.setText(f"ℹ️ {char.get('desc', '')}")
            default_shift = char.get("pitch_shift", 0)
            self.slider_pitch.setValue(default_shift)

    def on_pitch_slider_changed(self, val):
        sign = "+" if val > 0 else ""
        self.lbl_pitch_val.setText(f"{sign}{val} bán âm")

    def on_mode_toggled(self):
        is_song = self.rb_mode_song.isChecked()
        self.song_widget.setVisible(is_song)
        self.text_widget.setVisible(not is_song)
        self.tune_grp.setVisible(is_song)
        if is_song:
            self.btn_process.setText("🚀 BẮT ĐẦU TẠO AI COVER (RVC)")
        else:
            self.btn_process.setText("🎙️ TẠO GIỌNG ĐỌC & LỒNG TIẾNG AI")

    def select_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Bài Hát Gốc", "", "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg)"
        )
        if file_path:
            self.input_file_path = file_path
            self.lbl_selected_file.setText(f"🎵 {os.path.basename(file_path)}")
            self.lbl_status.setText(f"Đã chọn: {os.path.basename(file_path)}")

    def import_custom_rvc_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Chọn File Model RVC (.pth, .index hoặc .zip)", "", "RVC Models (*.pth *.index *.zip)"
        )
        if file_path:
            try:
                msg = self.engine.import_model_archive(file_path)
                QMessageBox.information(self, "Thành Công", msg)
                self.refresh_model_dropdown()
            except Exception as e:
                QMessageBox.critical(self, "Lỗi Nhập Model", str(e))

    def start_processing(self):
        char_id = self.cb_character.currentData()
        pitch_shift = self.slider_pitch.value()
        pitch_algo = self.cb_pitch_algo.currentText().split()[0].lower()
        index_rate = self.slider_index.value() / 100.0
        vocal_vol = self.slider_vocal.value() / 100.0
        beat_vol = self.slider_beat.value() / 100.0

        if self.rb_mode_song.isChecked():
            if not self.input_file_path or not os.path.exists(self.input_file_path):
                QMessageBox.warning(self, "Chưa chọn file", "Vui lòng chọn một file bài hát gốc (.mp3, .wav) trước!")
                return

            self.btn_process.setEnabled(False)
            self.pbar.setValue(10)
            self.lbl_status.setText("Đang khởi động AI Cover Engine...")

            def worker():
                try:
                    out = self.engine.process_full_ai_cover(
                        self.input_file_path,
                        char_id,
                        pitch_shift=pitch_shift,
                        pitch_algo=pitch_algo,
                        index_rate=index_rate,
                        vocal_vol=vocal_vol,
                        beat_vol=beat_vol,
                        progress_callback=lambda p, s: self.signals.progress.emit(p, s)
                    )
                    self.signals.finished.emit(True, out)
                except Exception as e:
                    self.signals.finished.emit(False, str(e))

            threading.Thread(target=worker, daemon=True).start()

        else:
            script_text = self.txt_script.toPlainText().strip()
            if not script_text:
                QMessageBox.warning(self, "Chưa nhập nội dung", "Vui lòng nhập kịch bản hoặc lời cần đọc!")
                return

            self.btn_process.setEnabled(False)
            self.pbar.setValue(20)
            self.lbl_status.setText("Đang tổng hợp giọng nói Neural AI...")

            def worker_text():
                try:
                    all_presets = self.engine.celebrity_presets + self.engine.scan_custom_models()
                    char = next((p for p in all_presets if p["id"] == char_id), all_presets[0])
                    tts_voice = char.get("tts_voice", "turbo-nam-minh")
                    
                    file_id = uuid.uuid4().hex[:8]
                    out_path = os.path.join(self.engine.temp_dir, f"speech_{char['id']}_{file_id}.mp3")
                    
                    self.signals.progress.emit(50, "Đang tạo giọng AI...")
                    self.engine.tts_engine.generate_speech(script_text, out_path, voice_name=tts_voice)
                    self.signals.finished.emit(True, out_path)
                except Exception as e:
                    self.signals.finished.emit(False, str(e))

            threading.Thread(target=worker_text, daemon=True).start()

    def on_progress(self, percent, msg):
        self.pbar.setValue(percent)
        self.lbl_status.setText(msg)

    def on_finished(self, success, result):
        self.btn_process.setEnabled(True)
        if success:
            self.output_file_path = result
            self.pbar.setValue(100)
            self.lbl_status.setText("🎉 Đã tạo thành công!")
            self.lbl_now_playing.setText(f"🎧 Đã tạo: {os.path.basename(result)}")
            self.btn_play_pause.setEnabled(True)
            self.btn_open_folder.setEnabled(True)
            self.player.setSource(QUrl.fromLocalFile(result))
            self.player.play()
            self.btn_play_pause.setText("⏸ Tạm Dừng")
            QMessageBox.information(self, "Thành Công", f"Đã hoàn thành AI Cover!\nFile lưu tại:\n{result}")
        else:
            self.lbl_status.setText("❌ Thất bại.")
            QMessageBox.critical(self, "Lỗi Xử Lý", f"Không thể xử lý:\n{result}")

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play_pause.setText("▶ Tiếp Tục")
        else:
            self.player.play()
            self.btn_play_pause.setText("⏸ Tạm Dừng")

    def on_player_position_changed(self, pos):
        dur = self.player.duration()
        if dur > 0:
            self.seek_slider.setValue(int(pos * 100 / dur))

    def on_player_duration_changed(self, dur):
        pass

    def set_player_position(self, slider_val):
        dur = self.player.duration()
        if dur > 0:
            self.player.setPosition(int(slider_val * dur / 100))

    def open_output_folder(self):
        if self.output_file_path and os.path.exists(self.output_file_path):
            folder = os.path.dirname(self.output_file_path)
            if sys.platform == "win32":
                os.startfile(folder)
            else:
                subprocess.Popen(["xdg-open", folder])
