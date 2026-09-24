# Rà độc lập media H001f — 24/09/2026

Đây là báo cáo bằng chứng chỉ đọc cho `h001-auto-20260924f`, **không phải quyết định duyệt media**. Đối chiếu revision content 1, audio 1, images 3 và review media 1. Không thay đổi artifact hay trạng thái Pilot.

## Hồ sơ kỹ thuật

- Có đủ 190 file `segment-000.wav` đến `segment-189.wav`, đều mono PCM 16-bit/48 kHz, không rỗng và không có mẫu chạm ngưỡng clipping. Tổng thời lượng segment và `narration.wav` cùng là **877,4346 giây (14:37,435)**, trong khoảng 10–15 phút của brief. `subtitles.srt` có 531 cue. Đây chỉ là kiểm tra cấu trúc/tín hiệu.
- Có đủ **84/84 ảnh cảnh** 1376×768 và ba ảnh đăng ký nhân vật. Cả 84 file mở được; `revisions/images/3/output.json` và `revisions/audio/1/output.json` đều ghi `checks.passed=true`.
- `reviews/media/1/manifest.json` liệt kê 96 asset; mọi file liệt kê đều tồn tại, 97 SHA-256 đã ghi (gồm `review.md`) đều khớp file hiện tại. `visual-timing.json` có đủ cảnh SC01–SC20.
- **Chưa có quyết định media**: `reviews/media/1/decision.json` chưa tồn tại. Ba lượt machine-review media đã lưu đều thất bại (`AGY_TIMEOUT_INCOMPLETE`, `AGY_FAILED`, `AGY_TIMEOUT_INCOMPLETE`) và chưa có response đánh giá chất lượng.

## Những hình cần sửa trước khi dựng

1. **SC13_I4 — sai vị trí manh mối chính.** Ảnh [SC13_I4](../runs/h001-auto-20260924f/revisions/images/3/SC13_I4_16x9.jpg) vẽ tờ giấy vàng và ba vạch trên bức tường **bên dưới gương**. Lời dẫn SC13 và prompt yêu cầu giấy dán ở **mặt sau tấm ván ép của gương**, chỉ thấy khi An nghiêng gương. [SC13_I3](../runs/h001-auto-20260924f/revisions/images/3/SC13_I3_16x9.jpg) còn thêm chân dung một phụ nữ trên tường, không có trong căn phòng đã thiết lập. Đây là sai lệch cao trào, nên sửa cảnh SC13 qua quy trình reject media có kiểm soát.
2. **SC16_I4 — nhân vật bị nhân đôi và mất đầu.** [Ảnh](../runs/h001-auto-20260924f/revisions/images/3/SC16_I4_16x9.jpg) có một thân An không đầu ngồi trên giường và một mặt/thân An khác ở mép phải. Prompt chỉ yêu cầu một An ở mép khung, gương tối dần và chưa xuất hiện thực thể. Cần sửa cảnh SC16.
3. **SC17_I1 — hành động nhảy trước cảnh.** [Ảnh](../runs/h001-auto-20260924f/revisions/images/3/SC17_I1_16x9.jpg) cho An đứng trước gương. Cuối SC16 An còn cứng người trên giường; SC18 mới là lúc cậu bật dậy bỏ chạy. Cần giữ An trên giường trong SC17 hoặc dùng góc nhìn phản chiếu tương ứng khi sửa cảnh SC17.
4. **Dấu bốn cánh ở góc ảnh.** Vùng cố định gần góc phải dưới có cùng biểu tượng lấp lánh bốn cánh trên toàn bộ 84 JPG (đối chiếu vùng ảnh, quan sát trực tiếp ở SC13_I4, SC16_I4, SC17_I1 và ảnh mascot). Dấu này nằm trong file JPG, không phải lớp giao diện xem ảnh. Flow Profile 10 và 102 đều có công tắc visible watermark bật nhưng bị khóa với thông báo khu vực bắt buộc; [Google Flow Help](https://support.google.com/flow/answer/16353333?hl=en) xác nhận Việt Nam tự áp dấu nhìn thấy. Vì vậy đây nhiều khả năng là dấu của Flow, không phải chi tiết do prompt tạo. Cần quyết định của người dùng trước khi đưa ảnh có dấu vào video; không xóa dấu hậu kỳ.

## Cảnh và nhân vật đạt ở mức nhìn trực tiếp

- Chuỗi SC09 cho thấy mặt ván gương hướng ra phòng và chưa lộ giấy; SC12 chỉ lộ góc giấy; SC19 đưa gương về mặt ván hướng ra phòng. Chuỗi ý chính hiện rõ, ngoại trừ sai lệch SC13_I4 nêu trên.
- SC15–SC16 thể hiện nguồn tiếng gõ là phía gương; SC17_I3/I4 thể hiện bóng đen bên cạnh hình phản chiếu của An. Không thấy bóng đen ở phòng thật trong những ảnh cuối đã xem.
- Tám ảnh SC01/SC20 đã xem thể hiện CH01 với đầu tròn trắng viền tối, hai mắt oval đen, miệng mở có lưỡi san hô, áo xanh nhạt và một thân; không thấy răng hoặc lông mày. Dấu bốn cánh vẫn hiện trên ảnh mascot.

## Âm thanh và nhịp cao trào

- **Kiểm tra nghe WAV: `unsupported` trong phiên rà độc lập này.** Không thể xác nhận cách phát âm, chất giọng, lỗi câu, tiếng gõ nghe thực tế hoặc chất lượng mix bằng thông số kỹ thuật; không được coi 190 WAV hợp lệ là đã duyệt âm thanh.
- Dữ liệu đoạn cho thấy câu SC15 chứa “Cốc… cốc… cốc.” ở 655,26–661,05 giây; SC16 đọc “Hai giây im bặt.” ở 661,05–662,90, rồi “An nín thở. ‘Cốc.’” ở 662,90–665,64. Nhịp hình đặt ba tiếng tại 655,26 và tiếng thứ tư tại khoảng 664,11 giây, cách nhau **8,85 giây theo mốc beat**. Đây là mốc nội suy theo câu, không phải phép đo thời điểm từng tiếng gõ. SC16 không có SFX `knock` riêng trong content. Vì vậy nhịp “hai giây” chưa được chứng minh bằng artifact âm thanh.

## Kết luận

Artifact đã đủ số lượng và khớp hash, nhưng **media chưa đạt để chuyển sang video** do ba ảnh sai lệch nêu trên, dấu bốn cánh trên JPG và chưa có quyết định đánh giá media hợp lệ. Cần sửa ảnh theo cảnh qua cổng media, kiểm tra âm thanh bằng công cụ nghe thật, rồi để bộ đánh giá `auto` xem/nghe artifact và lưu quyết định đúng quy trình.
