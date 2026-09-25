# Kế hoạch video xem thử: đúng 2 phút đầu H001

**Phạm vi mới:** một MP4 16:9 tiếng Việt dài đúng `00:02:00.000`, dựa trên hạt giống H001 “Tiếng gõ sau tấm gương”. Đây là đoạn mở của truyện, kết ở điểm móc; không kể hoặc hé lộ cú lật của bản 10–15 phút. Job dài `tieng-go-sau-guong-thu-20260924` đã dừng và H001 đã trả về kho; không đánh dấu hạt giống đã làm chỉ vì có đoạn xem thử.

## Nội dung và mốc hình

| Mốc mục tiêu | Lời kể và hành động | Hình cần có |
|---|---|---|
| 00:00–00:30 | Cảnh 1 đã duyệt: gương úp mặt vào tường, ba tiếng gõ đúng hai giờ; người dẫn nhường lời cho Nam. | Mascot chuẩn trong phòng tối; gương quay lưng. |
| 00:30–01:15 | Cảnh 2 đã duyệt: Nam là sinh viên cần phòng rẻ, kéo vali vào dãy trọ cuối hẻm; hành lang vắng. | Nam ở đầu hẻm; dãy trọ. |
| 01:15–02:00 | Cảnh 3 đã duyệt: bà chủ trao chìa khóa số bảy, né ánh mắt Nam; kết ở cử chỉ nhìn ra sau vai cậu. | Bà chủ và chìa khóa; tay Nam nhận chìa. |

Mốc trên là nhịp dựng mục tiêu. Lấy nguyên văn ba cảnh đầu từ content revision 3 đã duyệt. Thời lượng cuối phải đo bằng WAV thật; nếu vượt 120 giây, dừng ở câu trọn vẹn gần mốc nhất và chỉnh nhịp trước khi dựng; nếu ngắn hơn, giữ hình/âm nền đến đúng 120 giây. Không làm giọng nhanh bất thường hoặc cắt giữa câu. Mọi neo hình/tiếng động bám lời dẫn cuối.

## Trình tự thực hiện ngắn nhất

1. Chốt lời dẫn khoảng 2 phút từ ba cảnh đầu đã duyệt. Mỗi cảnh tổng hợp riêng bằng Gwen “Phạm Tuyên”; dùng bản vá cache từng câu/từng cảnh đã kiểm tra ở checkout riêng. Sau mỗi cảnh, lưu WAV và đo ngay. Nếu câu lỗi, chỉ tạo lại câu đó.
2. Tạo bộ ảnh tĩnh cho đúng ba cảnh bằng Flow với mascot chuẩn, ảnh tham chiếu nhân vật và Base scene reference. Một tab, tối đa bốn worker; thu và lưu ảnh sau từng lượt để không chạm giới hạn `localStorage` khoảng 5 MB. Không gửi trùng nếu trạng thái không rõ.
3. Dựng ảnh + WAV + phụ đề theo nhịp lời kể, trộn nền/tiếng động CC0 ở mức nhỏ. Xuất MP4 16:9 đúng 120 giây, xem/nghe toàn bộ, kiểm tra không cắt câu, không sai nhân vật, không có chữ ngoài danh sách cho phép.
4. Bàn giao MP4, WAV, lời dẫn và ảnh đối chiếu. Giữ nhãn **bản xem thử 2 phút**; không gọi là video truyện 10–15 phút đã hoàn tất và không chạy `horror/bank.py mark`.

## Cổng quy trình cần xử lý

`horror/bank.py` hiện chỉ có mức ngắn nhất **4–6 phút**. Vì vậy không thể tạo một job Pilot 2 phút hợp lệ bằng các lựa chọn hiện có. Đoạn 2 phút cần được làm như **preview riêng** từ H001, hoặc phải phát triển một chế độ preview 2 phút được kiểm tra trước khi cho Pilot quản lý như sản phẩm chính thức. Không chỉnh brief/revision/integrity của job cũ để ép qua cổng. Quyết định duyệt tự động cho content revision 3 của job dài không phải quyết định duyệt cho MP4 preview mới; bản preview phải được nghe/xem thật trước khi bàn giao.

## Trạng thái lúc lập kế hoạch

- TTS job dài đã dừng; chưa có WAV cache của H001.
- Flow session và Chrome dùng cho lượt này đã dừng.
- H001 đã release về kho. Không có MP4 H001.
- Bản sửa Gwen chia theo cảnh, lưu từng câu ngay, đã đạt 12 kiểm thử Gwen và 40 kiểm thử audio trong checkout riêng; chưa tích hợp vào checkout sản xuất.
