import os
import sys
import uuid
import shutil
import threading
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QSlider, QProgressBar, QMessageBox,
    QGroupBox, QFrame, QSplitter, QTextEdit, QRadioButton, QCheckBox
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

        self.signals = VoiceSignals()
        self.signals.progress.connect(self.on_progress)
        self.signals.finished.connect(self.on_finished)

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
        
        lbl_title = QLabel("🎵 AI COVER STUDIO - ĐỔI GIỌNG BÀI HÁT & NGƯỜI NỔI TIẾNG")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        lbl_sub = QLabel("Tự động bóc tách Nhạc Beat & Giọng Hát -> Đổi giọng ca sĩ sang Người Nổi Tiếng -> Tự động Mix lại bài hát hoàn chỉnh.")
        lbl_sub.setStyleSheet("font-size: 12px; color: #94a3b8;")
        h_layout.addWidget(lbl_title)
        h_layout.addWidget(lbl_sub)
        main_layout.addWidget(header_box)

        # Mode Selection Bar
        mode_box = QFrame()
        mode_box.setStyleSheet("background: #1e293b; border-radius: 6px; padding: 6px;")
        m_layout = QHBoxLayout(mode_box)
        m_layout.setContentsMargins(8, 4, 8, 4)

        lbl_mode = QLabel("Chế Độ Xử Lý:")
        lbl_mode.setStyleSheet("font-weight: bold; color: #f8fafc;")
        m_layout.addWidget(lbl_mode)

        self.rb_mode_song = QRadioButton("🎵 1. Đổi Giọng Bài Hát Đầy Đủ (Tự Tách Beat + Đổi Giọng Ca Sĩ + Mix Lại)")
        self.rb_mode_song.setChecked(True)
        self.rb_mode_song.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 13px;")
        self.rb_mode_song.toggled.connect(self.on_mode_toggled)
        m_layout.addWidget(self.rb_mode_song)

        self.rb_mode_text = QRadioButton("✍️ 2. Tạo Giọng Đọc & Hát AI Trực Tiếp Từ Lời Bài Hát / Kịch Bản")
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
        
        self.btn_select_file = QPushButton("📂 Tải Lên File Bài Hát (.mp3, .wav, .m4a)")
        self.btn_select_file.setStyleSheet("background: #2563eb; color: white; font-weight: bold; padding: 10px 14px; border-radius: 6px; font-size: 13px;")
        self.btn_select_file.clicked.connect(self.on_select_file)
        sw_layout.addWidget(self.btn_select_file)

        self.lbl_file_info = QLabel("Chưa chọn file bài hát nào...")
        self.lbl_file_info.setStyleSheet("color: #cbd5e1; font-size: 11px;")
        self.lbl_file_info.setWordWrap(True)
        sw_layout.addWidget(self.lbl_file_info)

        self.btn_play_orig = QPushButton("▶ Nghe Thử Bài Hát Gốc")
        self.btn_play_orig.setStyleSheet("background: #334155; color: #e2e8f0; padding: 6px; border-radius: 5px;")
        self.btn_play_orig.setEnabled(False)
        self.btn_play_orig.clicked.connect(self.on_play_original)
        sw_layout.addWidget(self.btn_play_orig)

        self.chk_auto_sep = QCheckBox("🎧 Tự động tách riêng Nhạc Beat và Giọng Ca Sĩ (Khuyên dùng)")
        self.chk_auto_sep.setChecked(True)
        self.chk_auto_sep.setStyleSheet("color: #10b981; font-weight: bold; margin-top: 4px;")
        sw_layout.addWidget(self.chk_auto_sep)

        self.ig_layout.addWidget(self.song_widget)

        # Text Mode widgets
        self.text_widget = QWidget()
        tw_layout = QVBoxLayout(self.text_widget)
        tw_layout.setContentsMargins(0, 0, 0, 0)
        
        lbl_hint_text = QLabel("Nhập lời bài hát hoặc văn bản bạn muốn Người Nổi Tiếng hát/nói:")
        lbl_hint_text.setStyleSheet("color: #94a3b8; font-size: 11px;")
        tw_layout.addWidget(lbl_hint_text)

        self.txt_lyrics = QTextEdit()
        self.txt_lyrics.setPlainText("Ta thà phụ người trong thiên hạ, chứ không để người trong thiên hạ phụ ta! Non sông Đại Việt muôn đời trường tồn!")
        self.txt_lyrics.setStyleSheet("background: #0f172a; color: white; border: 1px solid #334155; border-radius: 6px; padding: 10px; font-size: 13px;")
        self.txt_lyrics.setFixedHeight(120)
        tw_layout.addWidget(self.txt_lyrics)
        self.text_widget.setVisible(False)
        self.ig_layout.addWidget(self.text_widget)

        left_layout.addWidget(self.input_grp)

        # 2. Mixing Controls Group
        self.mix_grp = QGroupBox("2. Tinh Chỉnh Âm Lượng Hòa Âm (Studio Mixer)")
        self.mix_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        mg_layout = QVBoxLayout(self.mix_grp)

        # Pitch Shift
        lbl_pitch_title = QLabel("Tông Giọng (Pitch Shift):")
        lbl_pitch_title.setStyleSheet("color: #cbd5e1; font-size: 12px;")
        mg_layout.addWidget(lbl_pitch_title)

        pitch_row = QHBoxLayout()
        self.slider_pitch = QSlider(Qt.Orientation.Horizontal)
        self.slider_pitch.setRange(-12, 12)
        self.slider_pitch.setValue(0)
        self.slider_pitch.valueChanged.connect(self.on_pitch_changed)
        
        self.lbl_pitch_val = QLabel("0 (Tự động tối ưu)")
        self.lbl_pitch_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 140px;")
        pitch_row.addWidget(self.slider_pitch)
        pitch_row.addWidget(self.lbl_pitch_val)
        mg_layout.addLayout(pitch_row)

        # Vocal Vol
        lbl_vocal_vol = QLabel("Âm Lượng Giọng Hát AI:")
        lbl_vocal_vol.setStyleSheet("color: #cbd5e1; font-size: 12px; margin-top: 6px;")
        mg_layout.addWidget(lbl_vocal_vol)

        vvol_row = QHBoxLayout()
        self.slider_vocal_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_vocal_vol.setRange(50, 200)
        self.slider_vocal_vol.setValue(110)
        self.slider_vocal_vol.valueChanged.connect(lambda v: self.lbl_vocal_vol_val.setText(f"{v}%"))

        self.lbl_vocal_vol_val = QLabel("110%")
        self.lbl_vocal_vol_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 45px;")
        vvol_row.addWidget(self.slider_vocal_vol)
        vvol_row.addWidget(self.lbl_vocal_vol_val)
        mg_layout.addLayout(vvol_row)

        # Beat Vol
        lbl_beat_vol = QLabel("Âm Lượng Nhạc Nền Beat:")
        lbl_beat_vol.setStyleSheet("color: #cbd5e1; font-size: 12px; margin-top: 6px;")
        mg_layout.addWidget(lbl_beat_vol)

        bvol_row = QHBoxLayout()
        self.slider_beat_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_beat_vol.setRange(30, 150)
        self.slider_beat_vol.setValue(100)
        self.slider_beat_vol.valueChanged.connect(lambda v: self.lbl_beat_vol_val.setText(f"{v}%"))

        self.lbl_beat_vol_val = QLabel("100%")
        self.lbl_beat_vol_val.setStyleSheet("color: #38bdf8; font-weight: bold; min-width: 45px;")
        bvol_row.addWidget(self.slider_beat_vol)
        bvol_row.addWidget(self.lbl_beat_vol_val)
        mg_layout.addLayout(bvol_row)

        left_layout.addWidget(self.mix_grp)
        left_layout.addStretch()
        splitter.addWidget(left_widget)

        # --- RIGHT PANEL ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.setSpacing(10)

        # 3. Celebrity Voice Preset Selector Group
        voice_grp = QGroupBox("3. Chọn Người Nổi Tiếng Mục Tiêu")
        voice_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        vg_layout = QVBoxLayout(voice_grp)

        self.cb_celebrity = QComboBox()
        self.cb_celebrity.setStyleSheet("background: #1e293b; color: white; padding: 8px; border: 1px solid #475569; border-radius: 6px; font-size: 13px;")
        for p in self.engine.celebrity_presets:
            self.cb_celebrity.addItem(f"{p['name']} ({p['category']})", p['id'])
        self.cb_celebrity.currentIndexChanged.connect(self.on_celebrity_changed)
        vg_layout.addWidget(self.cb_celebrity)

        self.lbl_celeb_desc = QLabel(self.engine.celebrity_presets[0]["desc"])
        self.lbl_celeb_desc.setStyleSheet("background: #0f172a; color: #a5f3fc; border-radius: 6px; padding: 10px; font-size: 11px;")
        self.lbl_celeb_desc.setWordWrap(True)
        vg_layout.addWidget(self.lbl_celeb_desc)

        right_layout.addWidget(voice_grp)

        # 4. Action & Output Card Group
        action_grp = QGroupBox("4. Xử Lý Tự Động & Xuất Bản")
        action_grp.setStyleSheet("QGroupBox { font-weight: bold; color: #f8fafc; border: 1px solid #334155; border-radius: 8px; margin-top: 10px; padding-top: 15px; }")
        ag_layout = QVBoxLayout(action_grp)

        self.btn_convert = QPushButton("🚀 BẮT ĐẦU ĐỔI GIỌNG BÀI HÁT (AI COVER FULL)")
        self.btn_convert.setStyleSheet("background: #f59e0b; color: #000; font-weight: bold; font-size: 14px; padding: 12px; border-radius: 8px;")
        self.btn_convert.clicked.connect(self.on_start_conversion)
        ag_layout.addWidget(self.btn_convert)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1e293b; border-radius: 6px; text-align: center; color: white; } QProgressBar::chunk { background: #38bdf8; border-radius: 6px; }")
        ag_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Sẵn sàng đổi giọng...")
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        ag_layout.addWidget(self.lbl_status)

        out_player_row = QHBoxLayout()
        self.btn_play_out = QPushButton("▶ Nghe Thử Bản AI Cover")
        self.btn_play_out.setStyleSheet("background: #10b981; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px; font-size: 13px;")
        self.btn_play_out.setEnabled(False)
        self.btn_play_out.clicked.connect(self.on_play_output)
        out_player_row.addWidget(self.btn_play_out)

        self.btn_save_mp3 = QPushButton("💾 Lưu Bài Hát MP3 320kbps")
        self.btn_save_mp3.setStyleSheet("background: #0284c7; color: white; font-weight: bold; padding: 10px 16px; border-radius: 6px; font-size: 13px;")
        self.btn_save_mp3.setEnabled(False)
        self.btn_save_mp3.clicked.connect(self.on_save_output)
        out_player_row.addWidget(self.btn_save_mp3)

        ag_layout.addLayout(out_player_row)

        right_layout.addWidget(action_grp)
        right_layout.addStretch()

        splitter.addWidget(right_widget)
        main_layout.addWidget(splitter)

    def on_mode_toggled(self):
        is_song_mode = self.rb_mode_song.isChecked()
        self.song_widget.setVisible(is_song_mode)
        self.text_widget.setVisible(not is_song_mode)
        self.mix_grp.setVisible(is_song_mode)
        if is_song_mode:
            self.btn_convert.setText("🚀 BẮT ĐẦU ĐỔI GIỌNG BÀI HÁT (AI COVER FULL)")
        else:
            self.btn_convert.setText("🎙️ TẠO GIỌNG ĐỌC & HÁT AI NGƯỜI NỔI TIẾNG NGAY")

    def on_select_file(self):
        fpath, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn File Bài Hát / Âm Thanh",
            os.path.expanduser("~"),
            "Audio Files (*.mp3 *.wav *.m4a *.flac *.ogg)"
        )
        if fpath:
            self.input_file_path = fpath
            info = self.engine.get_audio_info(fpath)
            dur_str = f"{int(info['duration'] // 60)}m {int(info['duration'] % 60)}s"
            fname = os.path.basename(fpath)
            self.lbl_file_info.setText(f"📁 {fname}\n⏱ Thời lượng: {dur_str}")
            self.btn_play_orig.setEnabled(True)
            self.lbl_status.setText("Đã nạp file bài hát thành công.")

    def on_play_original(self):
        if self.input_file_path and os.path.exists(self.input_file_path):
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.btn_play_orig.setText("▶ Nghe Thử Bài Hát Gốc")
            else:
                self.player.setSource(QUrl.fromLocalFile(self.input_file_path))
                self.player.play()
                self.btn_play_orig.setText("⏸ Tạm Dừng")

    def on_pitch_changed(self, val: int):
        if val > 0:
            self.lbl_pitch_val.setText(f"+{val} (Tăng cao)")
        elif val < 0:
            self.lbl_pitch_val.setText(f"{val} (Trầm sâu)")
        else:
            self.lbl_pitch_val.setText("0 (Tự động tối ưu)")

    def on_celebrity_changed(self, idx: int):
        if 0 <= idx < len(self.engine.celebrity_presets):
            preset = self.engine.celebrity_presets[idx]
            self.lbl_celeb_desc.setText(preset.get("desc", ""))

    def on_start_conversion(self):
        celebrity_id = self.cb_celebrity.currentData()
        is_song_mode = self.rb_mode_song.isChecked()

        if is_song_mode:
            if not self.input_file_path or not os.path.exists(self.input_file_path):
                QMessageBox.warning(self, "Chưa Chọn Bài Hát", "Vui lòng bấm 'Tải Lên File Bài Hát' trước!")
                return
        else:
            lyrics_text = self.txt_lyrics.toPlainText().strip()
            if not lyrics_text:
                QMessageBox.warning(self, "Chưa Nhập Văn Bản", "Vui lòng nhập lời bài hát hoặc câu nói cần phát âm!")
                return

        temp_out = os.path.join(self.engine.temp_dir, f"ai_cover_result_{uuid.uuid4().hex[:6]}.mp3")

        self.btn_convert.setEnabled(False)
        self.progress_bar.setValue(0)

        def run():
            try:
                def p_cb(pct, text):
                    self.signals.progress.emit(pct, text)

                if is_song_mode:
                    pitch_val = self.slider_pitch.value()
                    vocal_vol = self.slider_vocal_vol.value() / 100.0
                    beat_vol = self.slider_beat_vol.value() / 100.0
                    auto_sep = self.chk_auto_sep.isChecked()
                    ok = self.engine.convert_song_ai_cover(
                        input_audio_path=self.input_file_path,
                        celebrity_id=celebrity_id,
                        output_path=temp_out,
                        pitch_semitones=pitch_val,
                        vocal_volume=vocal_vol,
                        beat_volume=beat_vol,
                        auto_separate_beat=auto_sep,
                        progress_callback=p_cb
                    )
                else:
                    lyrics_text = self.txt_lyrics.toPlainText().strip()
                    ok = self.engine.synthesize_celebrity_speech(
                        text=lyrics_text,
                        celebrity_id=celebrity_id,
                        output_path=temp_out,
                        progress_callback=p_cb
                    )

                self.signals.finished.emit(ok, temp_out)
            except Exception as e:
                self.signals.finished.emit(False, str(e))

        t = threading.Thread(target=run, daemon=True)
        t.start()

    def on_progress(self, pct: int, text: str):
        self.progress_bar.setValue(pct)
        self.lbl_status.setText(text)

    def on_finished(self, success: bool, msg: str):
        self.btn_convert.setEnabled(True)

        if success:
            self.output_file_path = msg
            self.btn_play_out.setEnabled(True)
            self.btn_save_mp3.setEnabled(True)
            self.progress_bar.setValue(100)
            self.lbl_status.setText("🎉 Đã hoàn thành bản AI Cover! Bấm 'Nghe Thử' bên dưới để thưởng thức.")
            self.on_play_output()
        else:
            self.lbl_status.setText("Có lỗi xảy ra.")
            QMessageBox.critical(self, "Lỗi Đổi Giọng", f"Không thể xử lý:\n{msg}")

    def on_play_output(self):
        if self.output_file_path and os.path.exists(self.output_file_path):
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.btn_play_out.setText("▶ Nghe Lại Bản AI Cover")
            else:
                self.player.setSource(QUrl.fromLocalFile(self.output_file_path))
                self.player.play()
                self.btn_play_out.setText("⏸ Tạm Dừng")

    def on_save_output(self):
        if not self.output_file_path or not os.path.exists(self.output_file_path):
            return
        
        save_dest, _ = QFileDialog.getSaveFileName(
            self,
            "Lưu File Bài Hát MP3 Đã Đổi Giọng",
            os.path.join(os.path.expanduser("~"), "Desktop", "Bai_Hat_AI_Cover_Celebrity.mp3"),
            "MP3 Audio (*.mp3)"
        )
        if save_dest:
            shutil.copy2(self.output_file_path, save_dest)
            QMessageBox.information(self, "Đã Lưu Thành Công", f"Đã lưu bài hát tại:\n{save_dest}")
