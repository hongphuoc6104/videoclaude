# Thiết lập Flow nhiều profile — 24/09/2026

## Đã xác minh

- Profile 10: phiên sản xuất đã xác minh đúng đường dẫn Chrome và tool. H001f tạo đủ 84 ảnh cảnh trên profile này; sáu bản sao trạng thái tool đã được ghi trong quá trình dọn dung lượng. Chưa gặp lỗi hết hạn mức.
- Profile 102: đã remix VP Stickman Lab trong dự án Flow riêng. Tool hiển thị phiên bản V2.2.0, Nano Banana Pro, ô Base Scene/Character, Initialize Generation, Start Queue và hàng đợi rỗng. Đã tải ảnh mascot chuẩn và hai ảnh tham chiếu CH02/CH03 của H001f; lấy media ID thật từ ô ảnh Flow.
- Profile 13: đã tạo dự án Flow, remix cùng tool và kiểm tra các điều khiển như Profile 102. Đã tải ba ảnh tham chiếu và lấy media ID thật.
- `experiments/b2_illustrator/machine.local.json`: bật `automatic_account_switching`, đặt tool URL riêng của Profile 102/13 và ánh xạ ba media ID gốc (mascot, CH02, CH03) tới media ID của từng tài khoản. Kiểm tra `loadRotationPolicy()` xác nhận thứ tự tiếp theo là Profile 102 và các tham chiếu này được ánh xạ.

## Đang chờ

- Profile 14: đã tạo thư mục Chrome chuyên dụng và mở trang đăng nhập Google. Chờ người dùng đăng nhập; chưa có tool URL hoặc media ID nên chính sách tự bỏ qua profile này.
- Chưa có lỗi hết hạn mức thật trong H001f, vì vậy chưa có bằng chứng chuyển profile khi đang tạo ảnh. Không ghi là đã nghiệm thu chuyển thật.
- Ảnh Base Scene sinh trong từng wave chưa có media ID tương ứng ở profile khác. Nếu giới hạn xảy ra giữa chuỗi ảnh phụ thuộc, chính sách sẽ dừng an toàn với `REFERENCE_MEDIA_NOT_ON_PROFILE`; cần nhập ảnh base đã tạo vào profile đích và bổ sung ánh xạ trước khi tiếp tục. Không đánh dấu chúng là dùng chung khi chưa xác minh.

## Đường dẫn cục bộ

- Cấu hình riêng máy: `sys/experiments/b2_illustrator/machine.local.json` (Git bỏ qua; không chứa mật khẩu).
- Nhật ký ảnh: `sys/experiments/b2_illustrator/results/controller/production-attempts/`.
- Bản sao trạng thái 5 MB: `sys/experiments/b2_illustrator/results/controller/tool-state/`.
- Job hiện hành: `sys/runs/h001-auto-20260924f/`.
