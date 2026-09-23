Đường dẫn vận hành trong skill tính từ `sys/` của dự án; chạy `cd sys` trước các lệnh. Video cho người dùng nằm ở `../video/<tên-video>/`.

# Âm thanh trong media

Đọc AGENTS.md và docs/workflow.md. Trước sản xuất chạy status JOB và next JOB. Hai chế độ review/auto; chỉ ba phần content/media/video. Không áp dụng hướng dẫn duyệt từng module cũ.

Dùng run JOB media. Việt: Gwen-TTS (`tts_engine=gwen`, `.venv-gwen`) nhân bản giọng trong `assets/voices/<tts_voice>/` (voice.json + giọng mẫu); đọc từng câu trên GPU, mỗi câu được kiểm độ dài và đọc lại tối đa `tts_check_retries` lần, hết lượt thì dừng lỗi; thiếu CUDA hoặc hết VRAM thì dừng, không lùi về CPU. VieNeu (`tts_engine=vieneu`) chỉ dùng khi cài lại `.venv-tts`/`.venv-tts-gpu`; engine thực tế và các lần lùi về CPU ghi trong tts-result.json (với lời dẫn tiếng Việt chứa từ mượn tiếng Anh: không viết in hoa toàn bộ để tránh TTS đọc đánh vần từng chữ cái; đại từ đơn lẻ I dùng 'Ai' để phát âm tiếng Anh chuẩn tự nhiên); Anh Alba / Pocket TTS CPU INT8 tốc độ gốc. Caching âm thanh dựa trên content-addressed hash tại cache/tts/. Dual/16:9 bắt buộc narration_en và .venv-en. Bàn giao WAV Việt/Anh, SRT, thời lượng thật cùng ảnh tại media; không xin duyệt audio riêng. Sửa giọng bằng reject media --part audio; sửa lời dẫn bằng reject content.

Brief có `delivery` (truyện kinh dị) thì giọng Việt được đạo diễn theo `scripts/delivery.py`: mỗi cảnh có tốc độ và khoảng nghỉ riêng; thoại, câu ngắn, câu hỏi, dấu “…” và câu khép cảnh căng được chỉnh riêng; thêm màu giọng `delivery.fx`. Mỗi đoạn có thêm `speech_end` để nhạc nền nổi lên trong khoảng lặng. Muốn đổi cách đọc cho các job sau thì sửa `horror/channel.json` → `delivery`, không sửa brief đã lưu. Chi tiết xem docs/horror.md, mục "Đạo diễn giọng kể".


Quyết định người dùng cần đúng phần/revision và phản hồi nguyên văn. Quyết định máy chỉ qua báo cáo kiểm tra thật. Không tự tạo bằng chứng, không sửa file đã lưu hoặc ghi SQLite trực tiếp.
