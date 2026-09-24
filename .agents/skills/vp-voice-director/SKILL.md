---
name: vp-voice-director
description: Tinh chỉnh nhịp đọc từng câu cho lời dẫn truyện kinh dị đã chốt trong giai đoạn media, trước khi tổng hợp giọng Việt.
---

# Đạo diễn giọng truyện kinh dị

Chạy sau khi content được duyệt, trong `pilot.py run JOB media`. Đọc `horror/narration-style.md` mục “How the voice will read it” và hồ sơ `delivery` trong brief. `scripts/delivery.py::direct()` là mốc đọc bắt buộc; `scripts/voice_director.py` chỉ tinh chỉnh từng câu theo nghĩa và nhịp truyện.

Giữ nguyên từng ký tự trong lời dẫn đã chốt, thứ tự và số câu. Chỉ đề xuất tốc độ, khoảng lặng sau câu và nhãn giải thích. Tốc độ 0.80–1.10, lệch không quá 15% so với mốc của chính câu đó; khoảng lặng 0–2 giây; `gain_db` luôn bằng 0. Không thêm SSML, dấu cảm xúc hay chỉ dẫn thì thầm vào lời dẫn: Gwen-TTS không hiểu các thẻ đó.

Trước chi tiết sắp lộ, giữ nhịp chậm; câu căng ngắn và câu thoại cần khoảng lặng rõ; sau câu gây sợ, để người nghe có thời gian tiếp nhận. Dùng nghĩa của câu để phân biệt câu kể bình thường với câu gây sợ, nhưng giữ độ chuyển vừa phải. Nhãn `delivery_tag` và `reason` chỉ dùng để kiểm tra, không được đọc thành tiếng.

Nếu kết quả tinh chỉnh sai cấu trúc hoặc vượt giới hạn, sửa tối đa một lượt cho cùng lô. Hết lượt thì dùng mốc `direct()` cho lô đó và ghi fallback trong `voice-direction.json`. Đây là bước kỹ thuật nội bộ; kết quả media vẫn phải nghe WAV thật ở cổng duyệt chung.
