# Chuyển ảnh nền khi Flow đổi profile — bản triển khai cô lập

## Phạm vi

Khi Flow báo hết hạn mức và **không sinh ảnh**, hàng đợi vẫn chỉ chuyển những yêu cầu có nhật ký `failed_no_media`. Trước khi gửi lại bất kỳ yêu cầu nào ở profile kế tiếp, mã mới đối chiếu ảnh nền `based_on` với ba bằng chứng của lượt trước: media ID do Flow trả, profile đã gửi, và byte kết quả `generated` trùng với file `collected` còn trên đĩa. Thiếu hoặc lệch bằng chứng thì dừng trước upload và trước sinh ảnh.

Với ảnh nền ngoại profile, mã dùng thao tác Upload trong project Flow, từ chính file đã lưu. Nó chỉ nhận ID mới khi một phản hồi upload JSON thành công nêu rõ `mediaId`/`media_id` và tile UI mới chứa cùng ID đó; screenshot và hash được ghi cùng ID nguồn/đích vào `results/controller/reference-transfers/`. Journal ghi `uploading` **trước** khi mở file chooser. Nếu upload lỗi, giao diện không cho thấy ID, đăng nhập/CAPTCHA xuất hiện hoặc kết quả mơ hồ, journal giữ `uploading` và mọi lần chạy sau dừng để đối chiếu, không upload hoặc sinh ảnh lại. Lượt gửi ảnh cũng ghi cặp ID nguồn/đích đã dùng.

Ảnh Character vẫn dùng media ID đã ánh xạ ở profile đích. Upload một ảnh thông thường chưa chứng minh Flow đã đăng ký Character, nên nhân vật chưa có ánh xạ sẽ dừng. Cấu hình `reference_media: "shared"` đơn thuần không còn được coi là bằng chứng chia sẻ giữa hai tài khoản.

## Kiểm tra

- 59 kiểm thử Node liên quan đến profile, hàng đợi, reference transfer, controller và session đạt. Các fixture không mở trình duyệt, upload lên Flow hay sinh ảnh.
- Đối chiếu chỉ đọc với dữ liệu H001f hiện có: 90 media ID trong nhật ký hàng đợi đều có file `collected` khớp byte `generated`; một ảnh nền SC13 cho đúng profile nguồn và đúng SHA-256. Không sửa H001f.
- [Google Flow Help](https://support.google.com/flow/answer/16729550?hl=en) xác nhận có thể dùng ảnh tải từ thiết bị làm tài nguyên/ingredient trong project. Mã mascot hiện có cũng đã dùng menu Add media → Upload, nhưng **chưa có nghiệm thu trực tiếp** việc Flow trả ID trong phản hồi JSON và tile của profile 102/13. Nếu UI không phơi bày hai bằng chứng khớp nhau, đường mới sẽ dừng an toàn ở `REFERENCE_TRANSFER_*_UNVERIFIED`.

## Giới hạn chạy thật

Không đăng nhập, không tạo ảnh, không upload thử, không đổi cấu hình máy và không chạm job H001f trong lượt triển khai này. Profile 102/13 hiện có `tool_url` và ba ánh xạ nhân vật trong `machine.local.json`, nhưng trạng thái đăng nhập, cổng upload và việc tool chấp nhận ID mới vẫn cần kiểm tra trực tiếp. Profile 14 chưa có cấu hình máy. Không ghi rằng xoay profile đã nghiệm thu sản xuất.
