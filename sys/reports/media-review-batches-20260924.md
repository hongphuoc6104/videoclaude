# Duyệt media tự động theo lô — 24/09/2026

## Thay đổi

- `machine_review.review()` chia media thành các lô văn bản ngắn, một lô ảnh tham chiếu/phụ, rồi các lô hai cảnh. Mỗi lô cảnh yêu cầu kiểm tra đủ tám tiêu chí media, từng ảnh, ảnh tham chiếu và ảnh ranh giới cảnh trước.
- JSON/SRT dài được tách thành các mảnh UTF-8 tối đa 2.500 byte và 100 dòng, tối đa năm mảnh mỗi lượt. Mảnh ghép lại đúng từng byte của tệp gốc; dấu vết `view_file` phải cho thấy đã trả **toàn bộ dòng** và không có cờ cắt ngắn. Báo cáo cuối chỉ tính tệp gốc là đã xem khi tất cả mảnh đều đạt. Các lô đã đạt chỉ được dùng lại khi transcript AGY vẫn tồn tại và hash không đổi.
- WAV gốc được cắt theo ranh giới cảnh bằng khung PCM nguyên vẹn. Mỗi lô phải nghe toàn bộ clip; trước khi báo đạt, bộ điều phối xác minh các clip nối kín toàn bộ khung WAV ở từng ngôn ngữ.
- Mỗi lô lưu request, response, quan sát có cấu trúc theo loại tệp, quyết định và dấu vết `view_file` của AGY. Lô đạt được dùng lại khi tiếp tục; lô có lỗi chất lượng thật giữ `rejected.json` và buộc tạo media revision mới. Lỗi công cụ/thiếu khả năng nghe chỉ dừng duyệt, có thể thử lại sau khi sửa công cụ.
- Báo cáo cuối chỉ được tạo nếu mọi tệp trong manifest được phân và xem, mọi tiêu chí đều pass, ảnh/WAV không đổi và dấu vết AGY xác nhận từng `view_file` thành công. Báo cáo nhúng kết quả các lô để dấu duyệt gắn với bằng chứng đã chốt. Không đổi ba cổng công khai, revision hoặc review cũ.

## Kiểm tra

- Manifest thật H001f: 96 tệp → 88 lô (77 lô văn bản, 1 lô ảnh tham chiếu/bản sao, 10 lô cảnh). Mười clip nối kín **877,434645833 giây**, đúng số khung WAV gốc. Đây chỉ là lập kế hoạch đọc, không chạy duyệt H001f.
- `python3 -m unittest tests.test_machine_review_batches -q`: 15 kiểm thử đạt, gồm tiếp tục giữa chừng, thiếu tệp/quan sát, lời quan sát chung chung, lỗi chất lượng, âm thanh unsupported, sửa WAV, đổi manifest, hai ngôn ngữ, văn bản UTF-8 dài, phản hồi bị cắt ngắn, transcript bị sửa/xóa và thiếu ID ảnh dự kiến.
- `python3 -m unittest tests.test_workflow -q`: 27 kiểm thử quy trình đạt.

## Giới hạn

- Thử AGY thật đúng một mảnh SRT tạm (9.680 byte, 601 dòng) trả JSON hợp lệ sau 17,7 giây và tự nhận pass. Nhưng transcript `view_file` có `truncated_fields=['content']`; bộ duyệt đã **chặn**, không chấp nhận tự nhận đã xem đủ. Bằng chứng thử ở `sys/scratch/media-review-text-smoke-da39935f99/`. Rà 629 phản hồi lịch sử cho thấy cờ cắt ngắn xuất hiện gần mức 4 KB của trường log; kích thước mảnh mới dựa trên ngưỡng thấp hơn đó nhưng chưa được thử AGY lần hai.
- Việc xem đủ văn bản bằng mảnh nhỏ làm tăng lượt AGY. Chưa đo thời gian của toàn bộ 88 lô; chạy thực có thể mất lâu. Không nới kiểm tra để giảm thời gian nếu chưa có bằng chứng truy xuất đầy đủ hơn.
- Chưa chạy AGY thật trên job media mới. Dấu vết `view_file` xác nhận công cụ đã mở tệp và trả ảnh/âm thanh; nó không tự chứng minh khả năng cảm nhận/chất lượng phán đoán của mô hình. Vì vậy kết quả máy vẫn cần quan sát cụ thể từng tệp và tám tiêu chí; thiếu dấu vết hoặc lời đáp không hợp lệ thì dừng.
- Đường dẫn transcript AGY là chi tiết nội bộ có thể thay đổi; khi không đọc được, cổng duyệt fail closed. H001f đã khóa mã cũ nên bản sửa này không được chèn vào job/revision hiện tại; cần job tương thích mới hoặc đường chuyển hợp lệ được xác minh riêng.
