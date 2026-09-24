# H001: sửa lượt viết content bị hết giờ — 24/09/2026

Job thử `h001-auto-20260924` đã tạo đúng brief H001 (10–15 phút, 16:9, ngôi thứ ba, `auto`) và lập được dàn ý 20 cảnh. Lượt viết SC01–SC06 đầu tiên dừng trước khi nhận JSON có cấu trúc; không có chunk nào được ghi là hoàn tất, không có content revision hay quyết định duyệt. Job này đã release H001 về kho; toàn bộ attempt giữ nguyên để đối chiếu.

Log agy `cli-20260924_110345.log` ghi lượt viết bắt đầu 11:03:49 và chạm `--print-timeout 180s` lúc 11:06:49 khi vẫn đang tạo phản hồi. Lượt này có khoảng 27.493 input tokens, 43.452 thinking tokens và 12.726 response tokens. Đây là hết thời gian cho một yêu cầu quá lớn, không phải bằng chứng đăng nhập hỏng. Dòng cảnh báo đăng nhập ở đầu log được theo sau bởi xác nhận OAuth thành công.

## Thay đổi cho job mới

- `config.json`: riêng `horror_story` viết tối đa **2 cảnh mỗi lượt**; mặc định 6 cảnh của loại video khác giữ nguyên.
- `long_script.py`: lượt viết chi tiết truyện kinh dị có giới hạn **300 giây**; lượt lập dàn ý và các loại video khác vẫn theo giới hạn cũ. Không hạ chuẩn kiểm tra cảnh, lời dẫn, coverage, anchor hoặc số ý.
- `agy_pipeline.py`: khi CLI trả thiếu `structured_output` gần mốc hết giờ, báo `AGY_TIMEOUT_INCOMPLETE`. File `agy-diagnostic-*.json` chỉ lưu loại lỗi, thời gian, kích thước và hash đầu ra; không lưu prompt, nội dung phản hồi thô hay thông tin đăng nhập. Không tự gửi lại lời gọi chưa rõ kết quả.
- `horror/narration-style.md`: nhấn rõ thời gian yên tâm giả, giữ nguồn điềm lạ đến cao trào, tính liên tục vị trí/góc nhìn và không thách người nghe làm theo ở cảnh kết. Đây là các lỗi phát hiện khi rà dàn ý job thử; không sửa dàn ý lịch sử.

43 kiểm thử liên quan content, adapter agy và chính sách horror đạt; `git diff --check` sạch. Chưa xác nhận lượt 2 cảnh bằng agy thật; cần tạo job H001 mới sau khi mã được chốt, rồi kiểm tra từng chunk theo quy trình. Bản nháp dở của job cũ không được dùng làm sản phẩm.
