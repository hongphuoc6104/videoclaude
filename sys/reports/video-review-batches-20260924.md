# Tự duyệt video theo đoạn — 24/09/2026

Nhánh `codex/video-review-batches` bổ sung đường tự duyệt video dài. Bộ duyệt chỉ hoạt động sau khi media đã có quyết định hợp lệ và video có manifest hiện tại. Nó đọc, kiểm tra hash toàn bộ tệp trong manifest, kiểm số khung hình/âm thanh của MP4 cuối, đối chiếu manifest dựng và xác nhận các đoạn dựng phủ kín timeline.

Từ **MP4 cuối đã ghép tiếng**, bộ duyệt cắt khoảng mười lượt; lõi mỗi lượt dài tối đa 120 giây, phủ toàn bộ video không hở. Mỗi lượt có thêm hai giây ở hai đầu để xem/nghe qua ranh giới, gồm cả điểm nối dựng. Clip MP4 giữ tiếng, clip WAV được giải mã từ cùng khoảng âm thanh của MP4. Bộ duyệt xác minh số khung, kích thước, tốc độ khung hình, mẫu âm thanh và hash của clip trước khi gọi Antigravity.

Antigravity phải mở video bằng công cụ có khả năng cấp `video/*` và nghe WAV bằng công cụ cấp `audio/*`; transcript phải chứng minh hai lời gọi `view_file` thành công. Báo cáo từng lượt phải mô tả hình và âm ở đầu, giữa, cuối; nêu quan sát từng cảnh và kết luận cả năm tiêu chí video. Thiếu khả năng xem/nghe, thiếu file, quan sát chung chung hoặc một tiêu chí không đạt đều chặn duyệt. Bộ điều phối chỉ tổng hợp báo cáo `pass` sau khi mọi lõi của mọi bản video đã qua kiểm tra.

Lượt đã đạt được lưu theo hash nội dung clip và dữ liệu cảnh. Khi chạy lại, hệ thống kiểm lại hash clip cũ và transcript trước khi dùng lại, đồng thời ghi ánh xạ clip hiện tại ↔ clip thực sự đã xem. Kết quả thất bại về chất lượng được giữ để sửa qua revision mới; lỗi công cụ có thể thử lại mà không làm mất các lượt đã đạt.

**Giới hạn bằng chứng:** MIME và transcript chứng minh công cụ đã cấp video/âm thanh cho mô hình; chúng không tự chứng minh mô hình chú ý tới từng khung hình. Quan sát ở ba thời điểm, từng cảnh và từng tiêu chí là điều kiện bổ sung. Chưa chạy Antigravity thật trên MP4 H001; các kiểm thử dùng video tổng hợp và phản hồi giả của Antigravity, không phải quyết định duyệt sản phẩm.
