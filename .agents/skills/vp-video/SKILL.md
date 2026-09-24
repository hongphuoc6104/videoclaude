---
name: vp-video
description: Video hoàn chỉnh cho Video Pilot v3; dùng khi chạy hoặc sửa phần này.
---

Đường dẫn vận hành trong skill tính từ `sys/` của dự án; chạy `cd sys` trước các lệnh. Video cho người dùng nằm ở `../video/<tên-video>/`.

# Video hoàn chỉnh

Đọc AGENTS.md và docs/workflow.md. Trước sản xuất chạy status JOB và next JOB. Hai chế độ review/auto; chỉ ba phần content/media/video. Không áp dụng hướng dẫn duyệt từng module cũ.

Chỉ run JOB video sau media được duyệt hợp lệ. 9:16 Việt có phụ đề; 16:9 Anh timeline riêng, ẩn phụ đề. Review: đưa tất cả MP4 và revision để người dùng xem. Auto: máy xem/nghe bản dựng thật; không hỗ trợ thì blocked. Chỉ quyết định video hợp lệ mới là hoàn tất.

Quyết định người dùng cần đúng phần/revision và phản hồi nguyên văn. Quyết định máy chỉ qua báo cáo kiểm tra thật. Không tự tạo bằng chứng, không sửa file đã lưu hoặc ghi SQLite trực tiếp.

Job content 3.0: dựng theo danh sách beats/images đã duyệt và timeline riêng Việt/Anh; không tự phát hiện ảnh phụ theo tên hoặc gán mốc giây cố định. Hỗ trợ hold/cut/fade/slide_left/zoom_in/zoom_out. Chữ minh họa đã nằm trong ảnh; không dựng thêm lớp từ vựng. Giữ phụ đề Việt theo quy trình. Chuyển động phóng gần phải được kiểm tra không cắt mất chữ; không tự thêm hiệu ứng ngoài kế hoạch.

Bản dựng chia đoạn khoảng `render_segment_seconds` giây tại đầu cảnh, cache ở `runs/JOB/cache/render-parts/`, nối rồi ghép âm thanh một lần (xem mục “Dựng video theo đoạn” trong docs/workflow.md). Render blocked vì một đoạn lỗi: đọc log đoạn được nêu, sửa nguyên nhân rồi chạy lại; lần sau chỉ dựng đoạn thiếu. Một đoạn nhìn sai dù đầu vào không đổi: `python3 render_parts.py forget runs/JOB/revisions/render/N/render-parts.json --part K` để đặt riêng đoạn đó sang `rejected/`, rồi reject video và resume; chỉ đoạn K được dựng lại. Không xóa tay cache hay ghép file ngoài pipeline.

Xuất qua workflow vào `video/<job>/` sau đủ ba quyết định hiện tại. Trả đường dẫn thật từ kết quả điều phối; không đoán revision hoặc dùng script dựng lại độc lập. Nếu xuất lỗi sau duyệt, resume để thử xuất lại, không duyệt giả lần nữa.
