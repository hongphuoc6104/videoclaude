# H001f — trạng thái media và cổng duyệt — 24/09/2026

- Job `h001-auto-20260924f`, chế độ `auto`: content revision 1 đã duyệt; media revision 1 đang `awaiting_review`; video chưa chạy.
- WAV Việt: 190 đoạn, 877,43 giây, trong khoảng 10–15 phút của brief. Cụm ba tiếng gõ SC15 và tiếng thứ tư SC16 đã đọc thành câu liền mạch.
- Flow: 3 ảnh tham chiếu nhân vật và 84 ảnh cảnh 16:9 đã được lưu; 86 yêu cầu có trạng thái `collected` trong nhật ký controller. Sáu bản sao trạng thái tool được tạo khi dọn bộ nhớ; snapshot cuối `localStorageChars=513397`, hàng đợi `IDLE`.
- Review media: `runs/h001-auto-20260924f/reviews/media/1/review.md` có manifest 96 tệp. AGY lần 1 hết giờ sau 608,73 giây, không có `structured_output`. Lần 2 trả `status=ERROR` sau 449,19 giây; transcript Antigravity ghi bộ lọc nội dung của Google chặn phản hồi sau khi xem `SC17_I4_16x9.jpg`. Lần 3 hết giờ sau 612,46 giây, không có `structured_output`. Không lần nào tạo được quyết định máy hợp lệ. Không sửa báo cáo, không đánh dấu media đã duyệt, không dựng video.
- Mã chính hiện có bản sửa chuyển profile tại commit `b33ae5c`; job H001f khóa mã cũ. Checkout `/home/hongphuoc/.codex/worktrees/h001f-frozen/videoclaude/sys` giữ đúng bản mã của job và dùng chung dữ liệu chạy qua symlink; `python3 pilot.py status h001-auto-20260924f` trong checkout này đã trả về trạng thái hợp lệ sau khi mã chính cập nhật. Các lượt tiếp tục H001f phải chạy từ checkout này.
- Cần giải quyết cổng duyệt auto bằng bộ đánh giá nghe/xem được 96 tệp theo lô nhỏ hoặc một phương thức đánh giá hợp lệ khác trong job mới. Không chạy video từ H001f trước khi media có quyết định hợp lệ.

## Cập nhật sau lượt sửa SC16

- Reject media revision 1 theo cảnh SC16 đã được ghi bằng Pilot. Images revision 6 giữ lại kết quả cũ hợp lệ và tạo lại các ảnh SC16 cần thiết; nhật ký Flow mới đều xác định được kết quả, không có yêu cầu mập mờ.
- SC16_I4 mới vẫn vẽ thân An ngồi mất đầu và thêm An ở mép phải. Media review revision 2 đã tạo nhưng chưa có `decision.json`; tiến trình đánh giá tự động được dừng vì artifact rõ ràng chưa đạt. `pilot.py status` từ checkout frozen xác nhận media `awaiting_review` revision 2, video `pending`.
