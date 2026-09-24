# Triển khai đạo diễn giọng — 24/09/2026

## Phạm vi

- Đã thêm `.agents/skills/vp-voice-director/SKILL.md` và `scripts/voice_director.py`.
- `adapters.audio()` chỉ gọi lớp tinh chỉnh này khi brief bất biến có `delivery.voice_director.enabled=true`. Kế hoạch của `scripts/delivery.py::direct()` vẫn là nền. Yêu cầu đưa vào TTS giữ nguyên các trường `texts`, `speeds`, `gains`, `gaps`, `tail`; không sửa `tts_worker.py`.
- Mỗi phản hồi agy được kiểm tra số cảnh/câu, chữ giống hệt, số hữu hạn, tốc độ 0,80–1,10 và lệch tối đa 15% so với nền, khoảng nghỉ 0–2 giây, độ to bằng 0 và nhãn giải thích hợp lệ. Không rút ngắn khoảng nghỉ quan trọng của nhịp, câu hỏi, thoại hoặc câu hé lộ. Phản hồi sai được thử thêm một lần; vẫn sai thì nhóm câu đó dùng kế hoạch nền và ghi rõ trong `voice-direction.json`.
- Phản hồi đạt được cache theo lời dẫn, kế hoạch nền, không khí, số lần đọc lại, phiên bản skill và vị trí câu. Đọc lại audio sẽ có khóa cache mới; phản hồi trong cache được kiểm tra lại trước khi dùng.

## Kiểm tra thực tế

- Skill đạt `quick_validate.py`.
- 75 bài kiểm tra voice/delivery/horror/audio đạt sau khi ghép cấu hình kênh và schema brief.
- Một lượt agy thật trên hai cảnh lịch sử (chỉ đọc, trong thư mục tạm) trả JSON hợp lệ cho 13 câu sau 148,4 giây với giới hạn 150 giây. Lượt thử trước với giới hạn 75 giây không có `structured_output`. Vì vậy mã hiện chia tối đa 10 câu mỗi lô; cảnh dài được chia ở ranh giới câu đã có rồi ghép lại, không đổi chữ hoặc khoảng nghỉ. Giới hạn sáu cảnh mỗi lượt trong cấu hình vẫn được giữ. Lỗi hoặc hết giờ được thử thêm một lần rồi dùng kế hoạch nền, có log.

## Giới hạn

Các nhãn và biên số là kiểm tra kỹ thuật. WAV của job mới vẫn phải được nghe và đánh giá ở cổng media; lượt thử agy không chứng minh chất lượng giọng kể của H001. Chưa chạy job sản xuất, chưa sửa revision/review/SQLite lịch sử, Flow hoặc TTS worker.
