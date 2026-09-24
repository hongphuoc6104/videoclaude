# Kế hoạch tiếp tục Video Pilot — 24/09/2026

Nguồn: phiên Claude trong `~/.claude/projects/-home-hongphuoc-Desktop-videoclaude/a4a1e483-266e-4880-b0a7-6127bf9cdb94.jsonl`, ba nhật ký subagent của phiên đó, trạng thái Git và lệnh `pilot.py doctor/status/next`. Người dùng đã duyệt hai skill đạo diễn lúc 07:25 và đã chọn lần chạy H001 `auto`: 10–15 phút, 16:9, ngôi thứ ba, không khí theo hạt giống.

## Công việc đang thực hiện song song

1. **Dựng video chia đoạn:** hoàn tất mã chưa commit trong `render_parts.py`, `renderer/render.mjs` và vùng render của adapter; kiểm tra cache, thử lại khi lỗi, nối khung hình/âm thanh; dựng một bản đối chứng một lượt từ tài sản sẵn có và so tại các điểm nối. Lưu báo cáo `reports/segmented-render-20260924.md`.
2. **Đạo diễn kịch bản:** làm skill `vp-script-director` và nối vào content cho brief kinh dị. Chấm sáu tiêu chí; điểm đạt do mã tính; tối đa hai lượt sửa bằng cách cho người viết tạo lại bản nháp và neo mới, không sửa lời dẫn sau khi đã neo. Lưu bằng chứng và kiểm thử. Lưu báo cáo `reports/script-director-impl-20260924.md`.
3. **Đạo diễn giọng:** làm skill `vp-voice-director` và nối vào audio. Chỉ tinh chỉnh tốc độ/khoảng nghỉ trong biên Gwen hỗ trợ; giữ nguyên chữ và độ to; lỗi thì thử lại một lần rồi dùng bộ đạo diễn quy tắc hiện có. Cache theo nội dung và lượt đọc lại, lưu bằng chứng và kiểm thử. Lưu báo cáo `reports/voice-director-impl-20260924.md`.

Các phần trên không sửa revisions, reviews, SQLite hoặc job cũ. Những file dùng chung được ghép tuần tự sau khi từng phần hoàn tất.

## Ghép, kiểm tra và chạy thật

4. Kiểm tra toàn bộ thay đổi, đặc biệt cấu hình brief, adapter audio/render, schema và workflow. Chạy kiểm thử liên quan và bộ kiểm thử chung; xử lý lỗi phát sinh. Commit các thay đổi nguồn đã đạt cùng báo cáo, giữ nguyên dữ liệu lịch sử và file người dùng chưa commit không thuộc phạm vi.
5. Đối chiếu cấu hình Flow trên máy: session phải nạp mã hàng đợi mới; profile đang dùng, model và tham chiếu phải đúng. Chuyển profile chỉ dùng profile đã có `tool_url` và media mascot hợp lệ; trạng thái chưa rõ kết quả phải đối chiếu, không gửi trùng. Không coi bài kiểm thử giả là nghiệm thu Flow thật.
6. Tạo **job H001 mới** bằng `horror/bank.py start` với đúng sáu lựa chọn đã được người dùng trả lời, rồi chạy `doctor`, `status`, `next` và quy trình `content → media → video` ở mode `auto`. Mỗi cổng cần đánh giá artifact thật. Nếu gặp `unsupported`, đăng nhập/CAPTCHA hoặc trạng thái Flow chưa rõ, dừng đúng cổng và báo bằng chứng; không ghi pass giả hay sửa integrity của job cũ.
7. Chỉ sau khi video có đủ ba quyết định hợp lệ và xuất thành công mới `horror/bank.py mark JOB`. Báo cáo kết quả kiểm thử đầu cuối, video, lỗi còn lại và phần Flow/profile chưa nghiệm thu.

## Trạng thái lúc khôi phục

- Bốn commit sau 06:00 đã có: Gwen TTS `82ad5e3`, mật độ ảnh `d10807d`, sửa Flow `b7a8b31`, cập nhật quy tắc `048860d`.
- Dựng chia đoạn đã có mã chưa commit và nhật ký thử 10 đoạn/8.968 khung hình; đối chứng một lượt và báo cáo cuối chưa xong.
- Hai skill mới chưa có file; các subagent Claude trước chỉ đọc mã rồi bị ngắt do hạn mức.
- Mọi job thử cũ trả `Protected implementation changed`; H001 đã trả về kho, chưa có job chạy thử đầu cuối mới.
- `machine.local.json` vẫn đặt `automatic_account_switching=false`; profile kế tiếp chưa được xác minh đủ `tool_url`/tham chiếu. `doctor` báo `machine_review_media_verified=false`.

## Cập nhật sau khi ghép mã

- Ba phần dựng chia đoạn, đạo diễn kịch bản và đạo diễn giọng đã có mã, skill, kiểm thử và báo cáo riêng. Đạo diễn kịch bản đã bổ sung `revision_requests` mã `SD…` và kiểm tra `revision_response` của người viết; phần này được phát hiện và sửa trong lượt rà cuối.
- Bộ kiểm thử chung trước sửa cuối đạt 311/311. Sau sửa cuối: 32 kiểm thử trực tiếp của ba phần mới và 67 kiểm thử hồi quy content/workflow đạt. Bộ Flow Node đạt 62/62. Hai skill mới qua `quick_validate.py`; brief H001 tạo trong bộ nhớ hợp schema và bật cả hai đạo diễn.
- Chrome chuyên dụng Profile 10 đã kết nối đúng đường dẫn/executable. Tool mở được, hàng đợi thật đang rỗng; chưa gửi ảnh trong lượt này. Ba request cũ chưa rõ kết quả vẫn giữ nguyên trong journal, không gửi lại. Chúng mang identity khác H001 nên không chặn job mới.
- agy đã trả phản hồi có cấu trúc trong ba lượt thử riêng: chấm một cảnh theo schema đạo diễn kịch bản, nghe WAV và xem/nghe MP4 2 phút. Đây là kiểm tra khả năng công cụ, không phải quyết định duyệt H001.
- Việc còn lại: chốt commit nguồn, tạo H001 mới, chạy ba phần và xử lý lỗi dựa trên artifact thật.
