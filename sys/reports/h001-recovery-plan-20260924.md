# Kế hoạch tiếp tục H001 — 24/09/2026

## Đích và điểm dừng hiện tại

Đích là video H001 được duyệt hợp lệ theo chế độ `auto`, xuất MP4 16:9. Job `h001-auto-20260924f` đã duyệt content, tạo 190 WAV/877,43 giây và 84 ảnh; media revision 1 đang chờ quyết định, video chưa được phép chạy. Ba lượt đánh giá media nguyên khối không hoàn tất: hai lượt hết 600 giây, một lượt bị bộ lọc nội dung Google chặn. Transcript chỉ xem 30/23/15 đường dẫn riêng, trong khi manifest có 96 tệp. Không tiếp tục thử nguyên khối cùng đầu vào.

## Công việc song song

| Nhánh | Người thực hiện | Đầu ra cần kiểm chứng |
| --- | --- | --- |
| Rà artifact | Subagent QA | Báo cáo lỗi ảnh/giọng theo cảnh và bằng chứng trên file thật; không sửa trạng thái job. |
| Bộ duyệt chia lô | Subagent review_batches | Mã và kiểm thử trong worktree riêng: lô nhỏ, cache kết quả đã đạt, mỗi tệp/tiêu chí được xem hoặc nghe thật, thiếu/unsupported thì dừng. Không ghép vào H001f vì integrity. |
| Đường giữ artifact | Subagent reuse_path | Bằng chứng về khả năng chuyển WAV/ảnh sang job mã mới mà vẫn giữ xuất xứ; chỉ triển khai nếu hợp đồng Pilot cho phép. |
| Điều phối | Agent chính | Kiểm tra bằng chứng, chọn đường triển khai, giữ cổng content → media → video, cập nhật người dùng và nhật ký. |

## Thứ tự phụ thuộc

1. QA đã chỉ ra SC13_I4 đặt giấy/ba vạch trên tường thay vì sau lưng gương, SC16_I4 có An ngồi mất đầu và thêm một mặt An, SC17_I1 cho An đứng trước khi lời dẫn cho cậu đứng dậy. Sửa lần lượt theo cảnh bằng `pilot.py reject ... media --revision N --scene SCxx --note ...` trong checkout mã gốc của H001f, rồi `run ... media` để tạo revision mới; không sửa revision hay SQLite. Chỉ một người vận hành Pilot tại một thời điểm; đang giao lượt SC16 trước.
2. QA cũng thấy biểu tượng bốn cánh trong cả 84 JPG. [Google Flow Help](https://support.google.com/flow/answer/16353333?hl=en) cho biết Flow tự áp dấu nhìn thấy ở Việt Nam và có mục `Visible watermarking` dưới ảnh hồ sơ. Kiểm tra tùy chọn trên đúng tài khoản và khả năng tải lại ảnh đã tạo; không giả rằng prompt "no watermark" có thể loại dấu do dịch vụ thêm, và không xóa dấu hậu kỳ khi chưa rõ điều kiện sử dụng.
3. Kiểm tra bản duyệt chia lô bằng tests và bằng chứng modality thật. Dùng cho job mới có integrity phù hợp. H001f chỉ có thể chạy với mã gốc trong checkout frozen hoặc một tiến trình cùng mã gốc và đường dẫn dữ liệu chính tắc đã kiểm tra.
4. Nếu có đường nhập artifact chính thức và kiểm chứng hash/nguồn gốc, tạo job mới với cùng brief và đánh giá chất lượng lại; nếu không, giữ H001f ở cổng media cho đến khi có giải pháp hợp lệ. Không đổi mode hoặc gán quyết định giả.
5. Chỉ sau media được duyệt mới dựng video bằng các đoạn theo ranh giới cảnh, kiểm số khung/âm thanh/file thực, rồi để máy đánh giá video và xuất MP4 sau quyết định hợp lệ.

## Việc ngoài đường găng

Flow Profile 102/13 đã có tool, ảnh tham chiếu và mã xoay đã thử mở đúng profile. Chưa có quota thật để thử chuyển sau lỗi. Profile 14 chờ người dùng đăng nhập; sau đó mới tạo bản tool, tải ảnh tham chiếu và thêm URL/media ID vào cấu hình máy.
