# Đường hoàn thành H001 — cập nhật 24/09/2026

## Trạng thái đã xác minh

- Job `h001-auto-20260924f`: content revision 1 đã duyệt; media revision 2 chờ đánh giá tự động, chưa có `decision.json`; video chưa tạo revision. Không có tiến trình Pilot/Flow/render H001 đang chạy tại lúc kiểm tra.
- Âm thanh đã có 190 WAV, tổng 877,4346 giây (14:37). Có 84 ảnh cảnh và 3 ảnh tham chiếu. Bản MP4 2 phút hiện có chỉ là preview.
- Ba cảnh cần sửa hình: SC13 (giấy/ba vạch phải nằm sau gương), SC16 (An bị nhân đôi/mất đầu), SC17 (An đứng dậy quá sớm). Plan ứng viên chỉ đổi 11 đơn vị ảnh; 73/84 đơn vị giữ nguyên. Một lần sửa SC16 theo plan cũ không đạt.
- Dấu bốn cánh bắt buộc của Flow hiện diện trong tất cả 84 ảnh. Câu hỏi chọn giữ ảnh Flow có dấu hay đổi nguồn ảnh đã gửi cho người dùng; chưa có câu trả lời tại lúc viết.
- Người dùng chọn tạm dùng Profile 10, 102 và 13. Cấu hình xoay 10 → 102 → 13 đang bật; Profile 14 chưa đăng nhập và được bỏ qua. Chưa có lần hết hạn mức thật để nghiệm thu việc xoay.
- H001f khóa mã cũ. Bộ duyệt media nguyên khối đã không hoàn tất ba lần; bộ duyệt mới chia 11 lô không thể gắn trực tiếp vào job cũ. Không sửa integrity/review/decision để chuyển cổng.

## Bốn việc để ra MP4 dài

1. Chốt nguồn ảnh theo lựa chọn của người dùng. Nếu giữ Flow, tiếp tục với dấu do dịch vụ áp; nếu đổi nguồn, phải thiết lập nguồn hợp lệ trước khi tạo ảnh còn thiếu.
2. Bàn giao seed H001 sang job kế nhiệm cùng brief/lựa chọn, chốt và **duyệt lại content** với kế hoạch hình sửa SC13/16/17; nhập WAV có chứng từ. Nhánh đang triển khai nhập ảnh chọn lọc để giữ tối đa 73 ảnh có kế hoạch không đổi; nếu chỉ chứng minh được ở mức cảnh nguyên vẹn thì giữ 71 ảnh và sinh lại 13 ảnh. Mọi tham chiếu chuỗi base phải được kiểm tra, không gán ID hay nhật ký giả.
3. Đánh giá media thật bằng 11 lô ảnh/nghe WAV. Chỉ quyết định tự động sau khi từng lô đạt và kiểm tra kỹ thuật toàn bộ manifest đạt. Nếu có lỗi, sửa đúng cảnh/lô rồi chạy lại.
4. Dựng video 16:9 theo các đoạn ranh giới cảnh khoảng 2 phút; kiểm kết nối hình/tiếng, xem và nghe thành phẩm theo đoạn, quyết định video tự động, rồi xuất MP4. Video review theo đoạn đang được triển khai vì một lượt xem MP4 14:37 có rủi ro hết giờ.

Trên H001f, hai cổng chưa đạt là **media → video**. Trên đường job kế nhiệm cần ba quyết định hợp lệ **content → media → video**, vì kế hoạch hình của content thay đổi. Chưa gọi sản phẩm hoàn tất cho đến khi video có quyết định hợp lệ và file xuất hiện trong `video/`.

## Phân việc song song hiện tại

| Nhánh | Đầu ra cần đạt |
| --- | --- |
| Nhập ảnh chọn lọc | Mã trong worktree riêng, chứng từ/hash từng ảnh và chuỗi base; kiểm thử; không chạm job sống. |
| Duyệt video theo đoạn | Mã trong worktree riêng, chứng cứ xem/nghe thật từng đoạn, cache hợp lệ và fail closed; kiểm thử. |
| Profile Flow | Xác minh 102/13/14; cấu hình Profile 14 sau khi có phiên đăng nhập thật; không gửi tạo ảnh để thử. |
| Điều phối | Kiểm tra tích hợp, nghiệm thu mã, quyết định đường chuyển job, sản xuất qua Pilot và báo cáo tiến độ. |

Tích hợp mã theo thứ tự nhập ảnh chọn lọc rồi duyệt video theo đoạn, chạy kiểm thử chung và một lượt thử đa phương thức thật trước khi tạo job kế nhiệm. Job mới khóa phiên bản mã tại thời điểm tạo; vì vậy không mở job giữa lúc hai nhánh còn thay đổi mã.

## Những phần chưa được chứng minh

- Chưa có quota thật để nghiệm thu chuyển profile sau khi Flow báo hết hạn mức. Một lần tải riêng ảnh base SC02_I1 sang Profile 102 đã chứng minh request chứa byte nguồn được mã hóa, phản hồi mạng có ID trùng ô ảnh mới và nhật ký `registered`; chưa có lượt tạo ảnh phụ thuộc thực tế trên profile mới. Hai lượt tải SC16_I1 và SC01_I1 trước đó vẫn mơ hồ, không dùng ID hay gửi lại.
- Profile 14 có thể cần người dùng đăng nhập; không suy từ trang login rằng đã sẵn sàng.
- Bộ duyệt media chia lô chưa chạy trọn trên job H001 mới; bộ duyệt video chia lô chưa có bằng chứng chạy thật.
- Các ảnh sửa SC13/16/17 và video dài chưa được tạo, chưa có quyết định media/video.
