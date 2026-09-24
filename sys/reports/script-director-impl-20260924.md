# Triển khai đạo diễn kịch bản — 24/09/2026

## Phạm vi

Đã thêm skill nội bộ `.agents/skills/vp-script-director/SKILL.md` và bước chấm độc lập cho brief `horror_story` có `script_director.enabled`. `horror/bank.py` chép cấu hình từ `horror/channel.json` vào brief mới; schema brief-v3 cho phép trường này. Brief không bật đạo diễn giữ luồng cũ.

## Hành vi

Sau khi người viết hoàn thành bản nháp và `validate_content` đạt, agy chấm sáu tiêu chí 0–2 trên toàn truyện. Mã kiểm tra bằng chứng là câu trích nguyên văn có mã cảnh, tính ngưỡng mỗi tiêu chí ≥1 và tổng ≥10/12, rồi lưu `script-director-round-N.json`. Lượt viết tương ứng lưu `writer-round-N.json`.

Nếu chưa đạt, người viết nhận yêu cầu sửa cụ thể và sinh lại bản nháp đầy đủ. Lời dẫn được chốt trước khi đặt coverage/claims/anchor mới; bộ chấm không sửa bản đã neo. Tối đa hai lượt viết lại. Khi vẫn chưa đạt, `auto` dừng với `SCRIPT_DIRECTOR_NEEDS_ATTENTION` và không nộp draft; `review` chèn nhận xét vào `open_questions` rồi đưa bản cuối tới cổng duyệt content. Bước này không duyệt thay người hay máy của ba phần công khai.

Hiệu chỉnh sau rà soát: từng nhận xét sửa của đạo diễn được đổi thành `revision_requests` chính thức có mã `SD1-pacing_rhythm` (thêm hậu tố nếu cùng tiêu chí có nhiều yêu cầu). Cả đường viết một lượt và viết theo lô cảnh đều nhận mã này. Người viết phải trả `revision_response` tương ứng với trạng thái, giải thích và mã cảnh; mã báo đã xử lý phải chỉ tới cảnh thực sự đổi lời dẫn. Đường chia lô kiểm tra phản hồi thô từng lô trước khi gộp, nên phản hồi `unresolved` do bộ gộp tự điền không thể che việc người viết đã bỏ sót. Phản hồi `SD…` được lưu ở `script-director-revision-round-N.json` rồi bỏ khỏi bản content nộp, để `revision_response` công khai vẫn chỉ ứng với phản hồi người dùng. Mục chưa xử lý được đưa vào `open_questions` trong review; auto dừng `needs_attention`.

## Kiểm tra

- Skill qua `quick_validate.py`.
- 25 kiểm thử có agy giả đạt: luồng ngắn và chia đoạn, điểm đạt sau sửa, anchor mới, phản hồi `SD…` đầy đủ, chặn bỏ sót ở cả hai đường viết, chặn báo đã sửa khi lời dẫn không đổi, mục chưa xử lý hiện trong review và dừng auto, `auto` hết lượt không nộp draft, và hồi quy adapter/long_script.
- `horror/bank.make_brief` sinh brief hợp schema với cấu hình mới.
- `py_compile` và `git diff --check` đạt.
- Probe agy thật với mẫu một cảnh thử hoàn tất trong 69,38 giây: `status=SUCCESS`, có `structured_output`, hợp schema sáu tiêu chí, và câu trích bằng chứng đúng nguyên văn. Phản hồi thô ở `reports/script-director-agy-probe-20260924.json`; đây không phải đánh giá hay duyệt H001.

Chưa chạy agy trên kịch bản đầy đủ hoặc job sản xuất. Trên truyện 20–40 cảnh, mỗi lượt sửa có thể viết lại toàn bộ lô cảnh nên tăng thời gian và số lượt gọi agy. Nếu agy trả điểm hoặc bằng chứng sai schema/nguyên văn, attempt bị chặn để xem lại thay vì tự coi đạt.
