# Chuyển ảnh nền khi Flow đổi profile — bản triển khai cô lập

## Phạm vi

Khi Flow báo hết hạn mức và **không sinh ảnh**, hàng đợi vẫn chỉ chuyển những yêu cầu có nhật ký `failed_no_media`. Trước khi gửi lại bất kỳ yêu cầu nào ở profile kế tiếp, mã mới đối chiếu ảnh nền `based_on` với ba bằng chứng của lượt trước: media ID do Flow trả, profile đã gửi, và byte kết quả `generated` trùng với file `collected` còn trên đĩa. Thiếu hoặc lệch bằng chứng thì dừng trước upload và trước sinh ảnh.

Với ảnh nền ngoại profile, mã dùng thao tác Upload trong project Flow, từ chính file đã lưu. Nó chỉ nhận ID mới khi một phản hồi upload JSON thành công nêu rõ `mediaId`/`media_id` và tile UI mới chứa cùng ID đó; screenshot và hash được ghi cùng ID nguồn/đích vào `results/controller/reference-transfers/`. Journal ghi `uploading` **trước** khi mở file chooser. Nếu upload lỗi, giao diện không cho thấy ID, đăng nhập/CAPTCHA xuất hiện hoặc kết quả mơ hồ, journal giữ `uploading` và mọi lần chạy sau dừng để đối chiếu, không upload hoặc sinh ảnh lại. Lượt gửi ảnh cũng ghi cặp ID nguồn/đích đã dùng.

Ảnh Character vẫn dùng media ID đã ánh xạ ở profile đích. Upload một ảnh thông thường chưa chứng minh Flow đã đăng ký Character, nên nhân vật chưa có ánh xạ sẽ dừng. Cấu hình `reference_media: "shared"` đơn thuần không còn được coi là bằng chứng chia sẻ giữa hai tài khoản.

## Kiểm tra

- Sau rà độc lập, mã chỉ chấp nhận phản hồi của request chứa đúng byte ảnh nguồn (nhị phân hoặc base64), yêu cầu `data-media-id` trên chính tile mới bằng ID trong phản hồi, hỗ trợ nhãn UI tiếng Việt/Anh và băm byte ảnh tile tải lại. Ánh xạ tĩnh của ảnh nền đã sinh không được bỏ qua journal nguồn và upload đích; journal upload fsync cả thư mục trước thao tác ngoài. Kiểm thử profile/hàng đợi/transfer: 33 đạt.
- Đối chiếu chỉ đọc với dữ liệu H001f hiện có: 90 media ID trong nhật ký hàng đợi đều có file `collected` khớp byte `generated`; một ảnh nền SC13 cho đúng profile nguồn và đúng SHA-256. Không sửa H001f.
- [Google Flow Help](https://support.google.com/flow/answer/16729550?hl=en) xác nhận có thể dùng ảnh tải từ thiết bị làm tài nguyên/ingredient trong project. Mã mascot hiện có cũng đã dùng menu Add media → Upload, nhưng **chưa có nghiệm thu trực tiếp** việc Flow trả ID trong phản hồi JSON và tile của profile 102/13. Nếu UI không phơi bày hai bằng chứng khớp nhau, đường mới sẽ dừng an toàn ở `REFERENCE_TRANSFER_*_UNVERIFIED`.

## Lượt upload thật giới hạn

- Một ảnh nền H001f `SC16_I1` đã `collected` với SHA-256 `af81a40eacc45e960873225d4fb95a86b36f42049a16c46ec1855835da50e208` được upload **một lần** từ Profile 10 sang project của Profile 102; không gọi tạo ảnh. Flow hiện một tile mới đúng tên file nguồn, `data-media-id=f62fd305-a97b-4679-a930-3f9d85835d87`. Ảnh tile tải qua UI là WebP đã chuyển mã, nên hash tile khác hash JPG nguồn.
- Bộ quan sát không thấy phản hồi JSON có `mediaId` từ chính request mang byte JPG nguồn. Vì vậy kết quả trả `REFERENCE_TRANSFER_NETWORK_MEDIA_ID_UNVERIFIED`; journal `94293e6254ddfdb7815fa18f4c0e99a9211b1cd1c092d31884e42fff9bfcd542.json` giữ `uploading`. **Không map ID tile này, không upload lại ảnh này và không gửi yêu cầu tạo ảnh phụ thuộc.** Cần đối chiếu giao thức upload hai bước của Flow hoặc bằng chứng trực tiếp khác trước khi tuyên bố chuyển profile đạt sản xuất.

## Giới hạn chạy thật

Không đăng nhập, không tạo ảnh, không đổi cấu hình máy hay revision H001f trong lượt này. Profile 102/13 có `tool_url` và ba ánh xạ nhân vật trong `machine.local.json`; chuyển ảnh nền phụ thuộc vẫn fail closed theo lượt thử trên. Profile 14 chưa có cấu hình máy. Không ghi rằng xoay profile đã nghiệm thu sản xuất.
