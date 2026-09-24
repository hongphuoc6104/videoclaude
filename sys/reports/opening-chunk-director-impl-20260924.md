# Kiểm tra nhóm cảnh mở trước khi viết tiếp — 24/09/2026

Job H001 thử `h001-auto-20260924c` đã có dàn ý đạt, nhưng nhóm SC01–SC02 nói thẳng tiếng gõ ở sau gương, mô tả mascot cười mỉm, thay trang phục nhân vật và làm ảnh kế thừa lệch bối cảnh. Job được dừng trước content revision và H001 đã release; attempt/chunk cũ giữ nguyên làm bằng chứng.

Đã thêm `scripts/opening_chunk_director.py` cho **nhóm cảnh đầu tiên** của truyện kinh dị có bật `script_director`. Sau kiểm tra cấu trúc, agy xem bốn điểm: lời mở không lộ cú lật, ngoại hình nhân vật/mascot đúng tham chiếu, ảnh `based_on` giữ liên tục, và beat khớp ảnh được chọn. Dẫn chứng phải trích đúng trường và mã cảnh/ảnh/beat; mã tự tính đạt/trượt. Nhóm đầu chưa đạt được viết lại tối đa hai lần, cùng lời dẫn, hình, coverage và anchor mới, trước khi SC03 bắt đầu. Nhóm cảnh sau không thêm lượt chấm này.

Cache nhóm đầu chỉ được dùng lại nếu bản đánh giá đạt còn khớp hash của brief, dàn ý, chunk và phiên bản cổng. Khi nhóm mở thay đổi, các nhóm sau vốn dựa trên lời dẫn/tóm tắt cũ được viết lại; bản chưa đạt vẫn lưu để tra cứu nhưng không được đánh dấu hoàn tất.

**Kiểm thử:** 23 bài kiểm tra liên quan opening, outline và long-script đạt sau sửa cuối; skill `vp-script-director` qua validator. Một lượt agy thật trên chunk SC01–SC02 lịch sử đã chỉ ra cả bốn lỗi nêu trên. Phản hồi thật ban đầu dùng ID `channel-mascot` cho dẫn chứng ảnh chuẩn; bộ kiểm tra đã được sửa để nhận đúng ID khai báo này, rồi kiểm tra lại toàn bộ dẫn chứng từ phản hồi đã lưu: hợp lệ. Bằng chứng thử ở `scratch/opening-chunk-probe-20260924/`. Đây không phải quyết định duyệt content cho job mới.

Chưa chạy nhánh viết lại bằng agy thật hoặc H001 hoàn chỉnh; hai việc này sẽ được kiểm tra khi mở job mới. Nếu agy không trả JSON hoặc dẫn chứng không đúng, cổng dừng chứ không tự coi đạt.
