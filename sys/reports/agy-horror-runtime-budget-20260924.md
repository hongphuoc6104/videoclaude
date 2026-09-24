# Điều chỉnh thời gian `agy` cho truyện kinh dị dài — 24/09/2026

## Bằng chứng và phạm vi

Lượt lập dàn ý của `h001-auto-20260924d` chạm `--print-timeout 180s`. Tệp chẩn đoán đã lưu ghi `elapsed_seconds=183.94`, trạng thái CLI `SUCCESS` nhưng không có `structured_output`; hệ thống đã chặn thay vì coi đó là dàn ý hoàn tất. Đây là bằng chứng về thiếu thời gian cho lượt này, chưa phải bằng chứng rằng tăng thời gian sẽ bảo đảm thành công.

Đã thêm lựa chọn `effort` hợp lệ (`low|medium|high`) cho lời gọi trên **cùng CLI `agy` dùng tài khoản**, không thêm nhà cung cấp/API khác. Riêng truyện kinh dị dài, dàn ý đầy đủ giữ một lượt 360 giây; đạo diễn dàn ý 300 giây; đạo diễn kịch bản toàn truyện 600 giây. Ba lượt dùng `--effort high` để giữ khả năng rà nội dung. Lượt viết chi tiết hai cảnh/300 giây và các loại video khác giữ cách gọi hiện có. Công cụ diễn tập đã được sửa để chuyển tiếp đúng tùy chọn mới.

Giới hạn tiến trình vẫn bằng giới hạn CLI cộng 15 giây. Trường hợp hết giờ, kết quả thiếu JSON cấu trúc hoặc lỗi khác vẫn lưu chẩn đoán và dừng, không tự thử lại. Cổng kiểm tra dàn ý, kịch bản và ba phần duyệt vẫn giữ nguyên. Không có job Pilot, revision hoặc báo cáo máy nào được sửa trong thay đổi này.

## Kiểm tra

37 bài thử tập trung trong `test_agy_adapter`, `test_long_script`, `test_outline_director`, `test_script_director` đạt. Các bài thử xác nhận đối số CLI, thời gian riêng từng lượt, đường đi video khác, chuyển tiếp của công cụ diễn tập và việc giữ cặp cảnh 300 giây. Chưa chạy lượt `agy` thật hay nghiệm thu H001 sau điều chỉnh.
