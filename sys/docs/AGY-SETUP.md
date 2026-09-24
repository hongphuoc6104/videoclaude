# Antigravity tài khoản

CLI agy dùng đăng nhập tài khoản, không tự chuyển sang API trả phí. Kiểm tra kết nối bằng `.venv/bin/python scripts/agy_pipeline.py smoke`; đây chỉ là kiểm thử kết nối.

Tạo job và chạy qua `pilot.py new JOB --brief FILE --mode review|auto`, rồi `pilot.py run JOB` như docs/workflow.md. Không còn bước duyệt control.
Adapter nội dung nhận brief, sinh JSON, validate và lưu draft/revision. Bộ điều phối quyết định điểm duyệt.
Máy đánh giá ở chế độ auto phải đọc artifact thật; phiên không hỗ trợ nghe/xem media phải báo unsupported. Không coi kết quả smoke là nghiệm thu đánh giá đa phương thức.
Nhật ký ở agent-attempts/ và machine-reviews/. Timeout hoặc lỗi tài khoản giữ job chưa hoàn tất; sửa điều kiện rồi resume, không giả lập kết quả.

Lời gọi nội dung truyện kinh dị dài dùng các giới hạn riêng trên cùng CLI tài khoản: dàn ý đầy đủ 360 giây, cổng rà dàn ý 300 giây, mỗi cặp cảnh chi tiết 300 giây và cổng rà toàn truyện 600 giây. Dàn ý và hai cổng rà dùng `--effort high`; cặp cảnh giữ mức suy luận mặc định. Mỗi lời gọi còn có giới hạn tiến trình dài hơn `--print-timeout` 15 giây. Timeout chưa có JSON hoàn chỉnh được ghi chẩn đoán an toàn và chặn; không tự gửi lại yêu cầu không rõ kết quả.
