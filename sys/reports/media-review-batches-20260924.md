# Duyệt media tự động theo lô — 24/09/2026

## Thiết kế hiện tại

- Bộ duyệt dùng **một lô ảnh tham chiếu và các lô hai cảnh**. H001f có 20 cảnh nên cần 11 lượt AGY. Mỗi lô cảnh xem toàn bộ JPG của hai cảnh, các ảnh tham chiếu và ảnh cuối của lô trước; nghe clip WAV cắt đúng khung PCM từ bản master. Tám tiêu chí media đều phải đạt, với quan sát cụ thể cho từng ảnh và từng cảnh trong clip.
- Python đọc và hash **toàn bộ byte** của các JSON/SRT gốc. Nó đối chiếu payload trong ba envelope với job hiện tại, dấu nguồn content, ảnh và lời nhắc đã lập kế hoạch, mọi ID/tỷ lệ ảnh, WAV/segment, SRT tạo chính xác từ câu và thời gian, nhịp hình tính lại từ lời dẫn/ảnh/âm thanh, cùng manifest và trang review. Receipt nhập media (nếu có) được đối chiếu hash bản sao và nguồn. Dữ liệu cảnh cần đánh giá được đưa trực tiếp vào từng request AGY: lời dẫn, hình, nhịp, cue phụ đề, coverage, outline, yêu cầu brief và nhân vật. Không ghi rằng AGY đã đọc metadata gốc.
- Dấu vết transcript AGY phải chứng minh từng `view_file` của JPG và clip WAV trả media đúng loại. Thiếu khả năng nhìn/nghe, thiếu tệp, thiếu quan sát hoặc tiêu chí không pass đều chặn duyệt.
- Lô đạt được lưu theo hash nội dung riêng, gồm cảnh, brief, ảnh, ảnh tham chiếu, ảnh ranh giới, dữ liệu nhịp/phụ đề và PCM của clip. Khi manifest mới chỉ đổi một ảnh, các lô không bị ảnh hưởng được dùng lại sau khi kiểm tra lại hash tệp cũ, tệp hiện tại và transcript AGY. Báo cáo cuối vẫn gắn với hash **toàn bộ manifest hiện tại**; liệt kê riêng `deterministically_verified_files`, `agy_viewed_files`, ánh xạ ảnh hiện tại ↔ ảnh đã xem và phạm vi WAV gốc được nghe qua clip.

## Kiểm tra

- Manifest H001f thật, chỉ đọc: **96 tệp → 11 lô** (1 tham chiếu, 10 cặp cảnh); các clip nối kín **877,434645833 giây**.
- `python3 -m unittest tests.test_machine_review_batches -q`: 13 kiểm thử đạt, gồm manifest giả lập đủ 96 tệp, thiếu cue SRT, sửa payload metadata dù cập nhật manifest, thiếu dữ liệu inline, thiếu ảnh đã xem, thông tin quan sát chung chung, transcript cache đổi, và chỉ chạy lại lô bị ảnh hưởng khi một ảnh hoặc ảnh ranh giới đổi.
- `python3 -m unittest tests.test_workflow -q`: 27 kiểm thử quy trình đạt trước bản chỉnh cuối; cần chạy lại sau tích hợp.
- Thử AGY thật trước đó trên mảnh SRT tạm cho thấy transcript văn bản dài có thể bị cắt ngắn. Thiết kế hiện tại không yêu cầu AGY xem JSON/SRT gốc; dữ liệu đó được đọc và đối chiếu bằng Python. Chưa chạy AGY thật trên lô ảnh/WAV của job mới.

## Giới hạn

- `view_file` chứng minh công cụ đã cấp ảnh/âm thanh cho AGY, không tự chứng minh chất lượng phán đoán. Quan sát từng tệp, tiêu chí bắt buộc và báo cáo duyệt vẫn là điều kiện riêng.
- Transcript AGY là đường dẫn nội bộ; mất hoặc thay đổi transcript trước khi tổng hợp làm lô đã lưu không được dùng lại. H001f khóa mã cũ, nên chỉ dùng bản sửa với job tương thích mới hoặc đường nhập hợp lệ; không chèn quyết định vào H001f.
