# Kế hoạch tiếp tục H001 — 24/09/2026

## Đích và điểm dừng hiện tại

Đích là video H001 được duyệt hợp lệ theo chế độ `auto`, xuất MP4 16:9. Job `h001-auto-20260924f` đã duyệt content, tạo 190 WAV/877,43 giây và 84 ảnh; media revision 2 đang chờ quyết định, video chưa được phép chạy. Ba lượt đánh giá media revision 1 nguyên khối không hoàn tất: hai lượt hết 600 giây, một lượt bị bộ lọc nội dung Google chặn. Transcript chỉ xem 30/23/15 đường dẫn riêng, trong khi manifest có 96 tệp. Không tiếp tục thử nguyên khối cùng đầu vào. Lượt reject SC16 đã tạo images revision 6 nhưng SC16_I4 vẫn bị nhân đôi/mất đầu; AGY của media revision 2 được dừng trước khi có thể duyệt nhầm.

## Công việc song song

| Nhánh | Người thực hiện | Đầu ra cần kiểm chứng |
| --- | --- | --- |
| Rà artifact | Subagent QA | Báo cáo lỗi ảnh/giọng theo cảnh và bằng chứng trên file thật; không sửa trạng thái job. |
| Bộ duyệt chia lô | Subagent review_batches | Mã và kiểm thử trong worktree riêng: lô nhỏ, cache kết quả đã đạt, mỗi tệp/tiêu chí được xem hoặc nghe thật, thiếu/unsupported thì dừng. Không ghép vào H001f vì integrity. |
| Đường giữ artifact | Subagent reuse_path | Bằng chứng về khả năng chuyển WAV/ảnh sang job mã mới mà vẫn giữ xuất xứ; chỉ triển khai nếu hợp đồng Pilot cho phép. |
| Điều phối | Agent chính | Kiểm tra bằng chứng, chọn đường triển khai, giữ cổng content → media → video, cập nhật người dùng và nhật ký. |

## Thứ tự phụ thuộc

1. QA đã chỉ ra SC13_I4 đặt giấy/ba vạch trên tường thay vì sau lưng gương, SC16_I4 có An ngồi mất đầu và thêm một mặt An, SC17_I1 cho An đứng trước khi lời dẫn cho cậu đứng dậy. Một lượt reject SC16 theo cảnh vẫn không sửa được I4; ảnh I4 cũ dùng I1 làm base nhưng prompt đồng thời bảo giữ An trên giường và thêm mặt/vai An ở mép khung. Bản ứng viên image-plan trong `sys/scratch/h001f-next-job-image-plan-20260924/` tách I4 khỏi base có người và sửa vị trí giấy/hành động. Không sửa revision hay SQLite; chỉ một người vận hành Pilot tại một thời điểm. Chờ lựa chọn của người dùng về dấu Flow trước khi tạo ảnh tiếp.
2. QA cũng thấy biểu tượng bốn cánh trong cả 84 JPG. [Google Flow Help](https://support.google.com/flow/answer/16353333?hl=en) cho biết Flow tự áp dấu nhìn thấy ở Việt Nam. Kiểm tra trực tiếp Profile 10 và 102: công tắc visible watermark bật nhưng vô hiệu hóa, giao diện ghi khu vực bắt buộc có dấu. Đã hỏi người dùng chọn giữ dấu Flow cho H001 hay đổi nguồn tạo ảnh; không tự coi lựa chọn mặc định là phản hồi và không xóa dấu hậu kỳ.
3. Kiểm tra bản duyệt chia lô bằng tests và bằng chứng modality thật. Dùng cho job mới có integrity phù hợp. H001f chỉ có thể chạy với mã gốc: checkout frozen đọc `status/next`, còn sản xuất cần Pilot **và** dịch vụ Flow cùng mã frozen ở đường dẫn `sys/` chính qua namespace riêng đã kiểm tra. Không dùng symlink dài của checkout cho lệnh tạo ảnh.
4. Nếu có đường nhập artifact chính thức và kiểm chứng hash/nguồn gốc, tạo job mới với cùng brief và đánh giá chất lượng lại; nếu không, giữ H001f ở cổng media cho đến khi có giải pháp hợp lệ. Không đổi mode hoặc gán quyết định giả.
5. Chỉ sau media được duyệt mới dựng video bằng các đoạn theo ranh giới cảnh, kiểm số khung/âm thanh/file thực, rồi để máy đánh giá video và xuất MP4 sau quyết định hợp lệ.

## Việc ngoài đường găng

Flow Profile 102/13 đã có tool, ảnh tham chiếu và mã xoay đã thử mở đúng profile. Chưa có quota thật để thử chuyển sau lỗi. Profile 14 chờ người dùng đăng nhập; sau đó mới tạo bản tool, tải ảnh tham chiếu và thêm URL/media ID vào cấu hình máy.
