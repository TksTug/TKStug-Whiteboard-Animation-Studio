# 🎬 TKStug Whiteboard Animation Studio

> **Hệ thống AI Dựng Video Hoạt Hình Bảng Trắng Vẽ Tay Khớp Giọng Đọc Sách Tự Động**  
> *Automated AI Whiteboard Animation & Storytelling Video Studio with 64+ Vietnamese Voices*

---

## ✨ Tính Năng Nổi Bật (Key Features)

- ⚡ **Tự Động Bóc Tách Ngữ Nghĩa & Phân Cảnh (Smart Semantic Chunker)**: Nhập kịch bản câu chuyện hoặc tóm tắt sách (1 - 5 phút), hệ thống tự động bóc tách thành các phân cảnh logic ngắn gọn.
- 🎨 **Thư Viện 26+ Hình Vẽ Vector Sắc Nét (Vector Sketch Library)**: Tự động phân tích từ khóa tiếng Việt để ghép hình vẽ phác thảo phù hợp theo ngữ cảnh (*Tài chính, Mục tiêu, Bộ não, Trái tim, Hợp tác, Tên lửa bứt phá, Cúp vô địch, Bánh răng hệ thống, Chìa khóa giải pháp, Biểu đồ tăng trưởng, v.v.*).
- 🎙️ **Tích Hợp 64+ Giọng Đọc AI Cao Cấp (64+ AI Neural Voices)**: Hỗ trợ đầy đủ các giọng đọc siêu tốc & studio truyền cảm (Bắc, Trung, Nam, Đọc truyện đêm khuya, Podcast,...).
- ✍️ **Mô Phỏng Bàn Tay Người Thật & Nhịp Điệu Vẽ Chuẩn Phim Hoạt Hình (70% - 30% Rhythm)**:
  - Bàn tay cầm bút vẽ từng nét theo phương trình toán học đường cong Bézier trong **70% thời lượng**.
  - **30% thời lượng còn lại**, tay tự động lùi và ẩn đi để người xem thưởng thức trọn vẹn bức vẽ cùng phụ đề trong lúc giọng đọc kết thúc câu.
- 📱 **Đa Dạng Tỉ Lệ Khung Hình & Phông Nền**:
  - **16:9 Ngang**: Dành cho YouTube Full HD 1080p, Facebook Video.
  - **9:16 Dọc**: Dành cho TikTok, YouTube Shorts, Facebook Reels.
  - Phông nền: **Bảng Trắng (Whiteboard)**, **Bảng Đen Phấn (Blackboard)**, **Giấy Cổ Điển (Vintage)**.
- 📺 **Trình Phát Xem Trước Trực Tiếp Có Âm Thanh (Live Preview Player)**: Nghe thử giọng đọc thực tế và xem chuyển động nét vẽ khớp từng giây trước khi xuất video.

---

## 🛠️ Cài Đặt & Chạy (Installation & Run)

### Yêu Cầu Hệ Thống:
- Python 3.10+
- Hệ điều hành: Windows 10/11, macOS, Linux

### 1. Cài đặt thư viện phụ thuộc:
```bash
pip install PyQt6 Pillow numpy opencv-python imageio-ffmpeg edge-tts
```

### 2. Khởi chạy ứng dụng:
```bash
python main.py
```

### 3. Đóng gói thành file thực thi `.exe` độc lập:
```bash
pyinstaller --noconfirm --onedir --windowed --name TKStug_Whiteboard_Studio --add-data "assets;assets" main.py
```

---

## 📁 Cấu Trúc Dự Án (Project Structure)

```
tkstug_whiteboard_studio/
├── assets/
│   ├── hands/                 # Hình ảnh cánh tay người thật cầm bút
│   ├── sounds/                # Hiệu ứng âm thanh bút dạ
│   └── saydi_voices.json      # Danh mục 64 giọng đọc AI
├── backend/
│   ├── drawing_templates.py   # 26 mẫu vector sketch & bộ khớp từ khóa thông minh
│   ├── scene_manager.py       # Thuật toán phân đoạn kịch bản câu chuyện
│   ├── tts_engine.py          # Bộ tổng hợp giọng nói AI và đo đạc thời lượng
│   ├── video_renderer.py      # Bộ dựng khung hình & ghép video FFmpeg 1080p
│   └── utils.py               # Quản lý đường dẫn tài nguyên
├── gui/
│   └── main_window.py         # Giao diện PyQt6 & Trình phát trực tiếp (Live Player)
├── main.py                    # Điểm khởi chạy ứng dụng
├── requirements.txt           # Danh sách thư viện cần thiết
└── README.md
```

---

## 📄 Bản Quyền (License)
Dự án được phát triển bởi TKStug Studio. Mã nguồn mở phục vụ mục đích học tập và sáng tạo nội dung tự động.
