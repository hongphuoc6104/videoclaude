# Kiểm tra dàn ý trước khi viết cảnh — 24/09/2026

Đã thêm `scripts/outline_director.py` vào đường viết kịch bản dài của brief kinh dị có bật `script_director`. Dàn ý 20 cảnh vẫn được lập trong một lượt; trước khi viết cảnh đầu tiên, agy đánh giá năm điểm: câu mở không bật mí cú lật, có nhịp yên tâm giả giữa truyện, chi tiết gieo được trả và đúng hạt giống, nhân quả/góc nhìn nhất quán, lời kết không rủ người nghe làm theo. Mỗi nhận xét phải dẫn mã cảnh và trích nguyên văn từ mục đích cảnh. Mã tự tính kết quả, không nhận cờ `pass` từ mô hình làm quyết định.

Dàn ý chưa đạt được lập lại tối đa hai lần với lỗi cụ thể; vẫn chưa đạt thì dừng trước khi viết cảnh. Bằng chứng từng lượt lưu cùng attempt. Khi chạy lại sau lỗi, chỉ dùng lại dàn ý và các cảnh đã lưu nếu quyết định đạt trước đó còn khớp hash của đúng dàn ý. Dàn ý chưa kiểm tra hoặc bị đánh trượt không được tái sử dụng. Quy trình content/media/video công khai không thêm điểm duyệt.

**Kiểm thử:** 33 bài liên quan outline, long-script, script-director và adapter agy đạt; hai outline H001 bị lỗi nằm trong fixture kiểm thử. Skill `vp-script-director` qua validator; `git diff --check` sạch.

**Thử agy thật:** cổng đã chấm dàn ý của job lịch sử `h001-auto-20260924b` là **không đạt**, nêu đúng ba lỗi có bằng chứng: SC01 tiết lộ nguồn tiếng gõ sau gương, thiếu yên tâm giả ở giữa, SC17/SC19 khẳng định ý nghĩa số người thuê khi chưa gieo căn cứ. Phản hồi ở `scratch/outline-director-probe-20260924/`. Đây là kiểm tra khả năng của cổng trên dàn ý cũ, không phải quyết định content của job mới.

Chưa chạy thử việc lập lại dàn ý bằng agy thật; job H001 mới sẽ kiểm tra nhánh đó. Nếu agy không hỗ trợ hoặc trả bằng chứng sai schema, công việc dừng có báo cáo thay vì tự cho qua.
