# Kiểm tra hình ảnh: mascot "sticker" và mật độ ảnh — 2026-09-24

Báo cáo chỉ đọc (read-only), không sửa file hệ thống, không chạy lệnh làm đổi trạng thái `pilot.py`, không dùng Google Flow. Bằng chứng lấy từ job thật: `sys/runs/thu-5p-h007f`, `sys/runs/thu-5p-h007g`, `sys/runs/tieng-go-sau-guong-thu-20260924` (nguồn nội dung của demo `video/h001-demo-2min/h001-first-2-minutes-preview.mp4`), cùng mã nguồn `sys/renderer/index.tsx`, `sys/scripts/story_plan.py`, `sys/schemas/content-v3.json`, `sys/machine_review.py`, `sys/docs/horror.md`, `.agents/skills/vp-content/SKILL.md`.

## Câu 1: "Sticker" có nên giữ trong video không

### "Sticker" trong dự án này là gì

Grep `sticker|overlay|emoji|badge|decal` trên `sys/renderer/`, `sys/schemas/`, `sys/content_contract.py`, `sys/image_pipeline.py`, `sys/adapters.py`, `sys/prompt_templates.py` **không ra kết quả nào** — dự án không có khái niệm "sticker" như một lớp overlay kỹ thuật. `sys/renderer/index.tsx` (110 dòng) chỉ vẽ đúng ba lớp: ảnh nền (`Img` với `objectFit: contain`), phụ đề (`div` một dòng), và audio — không có logo, watermark hay lớp trang trí nào khác.

Vậy "sticker" mà người dùng hỏi chính là **nhân vật đại diện kênh (canonical mascot, CH01)** — ảnh tham chiếu `assets/characters/channel-mascot/reference-v1.png`: đầu tròn trắng viền xanh đen đậm, mắt oval đen đặc tối giản, miệng cười, người que, áo thun xanh biển nhạt. Đây đúng là phong cách "sticker" phẳng, viền dày, tối giản — khác hẳn phong cách vẽ truyện (semi-realistic, tối màu, nhiều chi tiết bút ký).

Đã trích 4 khung hình thật từ `video/h001-demo-2min/h001-first-2-minutes-preview.mp4` bằng ffmpeg (t=5s, 40s, 75s, 110s) và xem trực tiếp:

- **t=5s** (cảnh SC01, mascot dẫn chuyện trong studio tối, một luồng sáng ấm): mascot sticker phẳng, viền đen dày, mặt cười tươi.
- **t=40s, 75s, 110s** (câu chuyện chính, nhân vật Nam/bà chủ nhà): tranh vẽ tối màu, có bóng đổ, chất liệu vải/da/gỗ chi tiết, tông u ám đúng thể loại kinh dị.

Đối chiếu với `content.json` (revision 3, job `tieng-go-sau-guong-thu-20260924`): trong 20 cảnh, chỉ **SC01 (mở đầu)** và **SC20 (kết)** có `character_ids: ["CH01"]` (mascot); toàn bộ SC02–SC19 (nội dung truyện) dùng CH02/CH03 (nhân vật truyện), không có cảnh nào bị rò mascot vào giữa truyện. Kiểm tra tương tự trên `sys/runs/thu-5p-h007f` và `thu-5p-h007g`: mascot chỉ ở SC01 và SC10 (cảnh đầu/cuối), các cảnh giữa dùng nhân vật riêng. Đúng như quy tắc bắt buộc trong AGENTS.md và `.agents/skills/vp-horror/SKILL.md`: "mascot chỉ là người dẫn chuyện ở cảnh mở đầu và cảnh kết; nhân vật trong truyện là nhân vật riêng."

### Đánh giá cho kênh kể chuyện kinh dị

- **Không nên bỏ hẳn mascot**: nó là tài sản thương hiệu cố định của kênh (Media ID đã đăng ký), giữ tính nhận diện xuyên suốt nhiều video — tương tự cách các kênh kể chuyện thành công vẫn dùng logo/bumper mở đầu quen thuộc dù nội dung chính nghiêm túc.
- **Không nên để mascot xuất hiện giữa truyện**: phong cách sticker phẳng, mặt cười sẽ phá vỡ hoàn toàn không khí (tương phản gay gắt với tranh tối màu ở t=40–110s). Dữ liệu thực tế cho thấy hệ thống hiện đã tuân thủ đúng giới hạn này ở cả 3 job kiểm tra — không phát hiện vi phạm.
- **Điểm cần lưu ý (không phải lỗi, nhưng đáng cân nhắc)**: ở SC01, lời dẫn mở đầu chính là câu "hook" rùng rợn nhất video ("Chiếc gương trong phòng số bảy bị úp chặt mặt vào tường. Đúng hai giờ sáng, ba tiếng gõ khô khốc vang lên...") lại phát ra trong lúc hình ảnh là mascot cười tươi đứng trên ghế đẩu dưới đèn — ngoại hình vui vẻ hơi lệch tông với nội dung câu hook. Đây là giới hạn cố hữu của việc dùng mascot cố định (miệng cười là đặc điểm bắt buộc, không được sửa theo AGENTS.md), không phải lỗi kỹ thuật.
- Phát hiện phụ, không thuộc câu hỏi "sticker" nhưng thấy khi xem ảnh gốc: các ảnh Flow gốc (ví dụ `sys/reports/h001-2min-preview/images/04883c...jpg`) có một dấu sao lấp lánh (watermark của công cụ Flow) ở gần góc dưới-phải ảnh (đã phóng to kiểm tra — xem `/tmp/.../scratchpad/frames/mascot_corner_zoom.jpg`). Không có bước "crop" nào trong mã nguồn (`sys/adapters.py`, `sys/image_pipeline.py`, `sys/renderer/*`) xử lý dấu sao này; nó biến mất khỏi khung t=5s trong bản render nhiều khả năng là hệ quả phụ của hiệu ứng `zoom_in` (phóng to quanh điểm `focus` không phải góc dưới-phải) chứ không phải một bước cắt chủ đích như README của job mô tả ("Dấu sao... đã được cắt ở khâu dựng"). Ở những nhịp dùng `effect: hold/cut` (scale=1, không zoom), dấu sao vẫn có thể lộ ra. Đây là rủi ro nhỏ về watermark rò rỉ, nằm ngoài phạm vi câu hỏi 1 nhưng nên biết.

**Khuyến nghị**: **Giữ** mascot, **giới hạn nghiêm ngặt** đúng như quy tắc hiện hành — chỉ ở cảnh mở đầu/kết thúc, không lẫn vào cảnh truyện. Hệ thống đang làm đúng điều này ở cả 3 job kiểm tra, nên không cần thay đổi. Không có căn cứ để đề xuất bỏ mascot hoàn toàn.

## Câu 2: Ảnh sinh ra có quá ít không

### Đo mật độ ảnh thật trên job đã sản xuất

Job `thu-5p-h007f`/`thu-5p-h007g` (10 cảnh, mục tiêu 240–360 giây, âm thanh đã đo thật từ `revisions/audio/1/output.json`: tổng 298,9 giây):

| Cảnh | Thời lượng đo thật | Số ảnh khác nhau | Số nhịp (beat) |
|---|---|---|---|
| SC01 | 24,9s | 2 | 4 |
| SC02 | 32,7s | 2 | 3 |
| SC03 | 32,3s | 2 | 3 |
| SC04 | 30,7s | 2 | 3 |
| SC05 | 32,6s | 2 | 3 |
| SC06 | 30,5s | 2 | 3 |
| SC07 | 32,1s | 3 | 3 |
| SC08 | 31,7s | 3 | 3 |
| SC09 | 30,2s | 2 | 2 |
| SC10 | 21,3s | 2 | 2 |
| **Tổng** | **298,9s (~5 phút)** | **22 ảnh cảnh** | **29 nhịp** |

Tính theo vị trí neo (anchor) nội suy theo tỉ lệ trong lời dẫn (giống cách `story_plan.timeline()` nội suy): **ảnh khác nhau đổi trung bình mỗi 13,9–14,0 giây**, khoảng cách xa nhất giữa hai lần đổi ảnh là **~25 giây** (SC02: từ giây 24,9 đến 50,5). Nhịp máy quay (hiệu ứng `zoom_in/zoom_out/fade/cut/hold`) đổi trung bình mỗi **~10,3 giây** — vẫn là camera move trên cùng một ảnh tĩnh phần lớn thời gian.

Job dài hơn (`tieng-go-sau-guong-thu-20260924`, content revision 3, mục tiêu 600–900s, 20 cảnh): 40 ảnh cảnh / 65 nhịp — cùng khuôn mẫu đúng **2 ảnh/cảnh** (một số cảnh 3 ảnh), suy ra ảnh mới đổi trung bình mỗi **~18–19 giây** trên video dài — còn thưa hơn job 5 phút.

Tổng số lệnh sinh ảnh Flow thật đã thực hiện cho `thu-5p-h007g` (đếm trong `flow/attempts/`): 30 lượt gửi, 27 tải về thành công (4 ảnh tham chiếu nhân vật + 22 ảnh cảnh + biến thể lỗi/thử lại). `thu-5p-h007f`: 28 lượt gửi, 18 tải về thành công (job này dừng giữa chừng).

### Vì sao mật độ thấp — nguyên nhân trong mã nguồn

- **`sys/scripts/story_plan.py` `validate_plan()`** chỉ kiểm tra: mỗi ảnh phải được ít nhất một nhịp dùng (`IMAGE_USAGE`), neo (anchor) phải đúng thứ tự tăng dần, và **không có bất kỳ ràng buộc số lượng ảnh/nhịp tối thiểu nào theo thời lượng cảnh**.
- Hàm `estimates()` (cùng file) chỉ cảnh báo khi `seconds/len(beats) < 1.5` (nhịp **quá nhanh**) — hoàn toàn không có cảnh báo khi nhịp/ảnh **quá thưa**. Đây là "sàn" chặn dưới, không có "trần" ở trên, nên agent viết nội dung mặc định dùng đúng 2 ảnh/cảnh (mức tối thiểu hợp lý theo hướng dẫn) mà không bị ép tăng thêm.
- **`sys/schemas/content-v3.json`**: cả `images` và `beats` đều chỉ có `minItems: 1` — schema tĩnh, không biết thời lượng cảnh nên không thể tự đặt ngưỡng theo giây.
- **`.agents/skills/vp-content/SKILL.md`** (dòng chỉ dẫn viết kịch bản) có câu định tính: "Đủ bối cảnh phải có đủ ảnh và visual beats (ví dụ nêu 3 tình huống phải có đủ 3 ảnh)" — đúng là nguyên tắc AGENTS.md nhắc lại, nhưng **không có con số giây/ảnh cụ thể** nên agent tự diễn giải "đủ" theo số ý được nêu trong lời dẫn (thường 2 ý → 2 ảnh), không theo độ dài thời gian thực tế của cảnh.
- **`sys/machine_review.py`**: tiêu chí đánh giá máy `visual_beats_and_text_policy` (content) và `beat_timing` (media) chỉ là tên phạm trù gửi cho bộ đánh giá LLM, phần prompt chính (dòng 40–52) không có hướng dẫn số giây/nhịp cụ thể nào — nên bộ đánh giá tự phán đoán định tính, không có ngưỡng để bắt lỗi "quá thưa ảnh".

### So sánh với kênh kể chuyện thành công (tham khảo nhanh trên web)

Tìm kiếm nhanh về best practice của kênh "faceless narration" (Reddit story, true crime, horror kể chuyện) cho thấy khuyến nghị phổ biến là **đổi hình ảnh (cắt cảnh/pan/zoom/B-roll) mỗi 3–5 giây** để giữ chú ý người xem, hook phải rõ trong 30 giây đầu, và có "pattern interrupt" định kỳ. Mức 3–5 giây này thường đạt được bằng B-roll rẻ (gameplay nền, ảnh stock) chứ không phải tranh minh họa vẽ riêng từng cảnh như dự án này — áp fix cứng 3–5s/ảnh mới sẽ đội chi phí Flow rất lớn và không phù hợp phong cách kênh. Mức khoảng cách hiện tại của dự án (14–19 giây/ảnh mới, đỉnh tới 25 giây) rõ ràng thưa hơn nhiều so với ngưỡng khuyến nghị chung của thể loại, kể cả khi tính thêm hiệu ứng Ken Burns giữa các lần đổi ảnh.

*(Nguồn tham khảo: framesail.com/blog/high-retention-faceless-youtube-videos; các bài tổng hợp trên Medium về kênh horror faceless — mang tính định hướng chung của ngành, không phải số đo riêng cho kênh này.)*

### Đề xuất mục tiêu cụ thể

Hai đòn bẩy tách biệt, không cần sinh thêm ảnh AI cho đòn bẩy đầu:

1. **Nhịp máy quay (không tốn thêm ảnh Flow)**: dùng lại các hiệu ứng đã có sẵn trong renderer (`hold/cut/fade/slide_left/zoom_in/zoom_out` — xem `sys/renderer/index.tsx` dòng 30–37) nhưng đặt nhiều nhịp hơn trên cùng một ảnh. Mục tiêu: trung bình **~5–7 giây/nhịp** (so với ~10,3 giây hiện tại) — gần hơn ngưỡng ngành mà không tốn thêm Flow credit.
2. **Ảnh mới thật sự (tốn thêm Flow)**: mục tiêu trung bình **~8–10 giây/ảnh mới**, không để khoảng trống nào vượt **~12–15 giây** (so với hiện tại 14 giây trung bình, đỉnh 25 giây). Với cảnh dài ~30 giây, cần khoảng **3 ảnh/cảnh** thay vì 2.

### Thay đổi cụ thể (không đụng `prompt_templates.py`, không đụng renderer's core logic)

- **`sys/scripts/story_plan.py`**: thêm ràng buộc định lượng vào `validate_plan()`/`estimates()` — ví dụ fail nếu `seconds_ước_tính_của_cảnh / số_ảnh_khác_nhau > 12` hoặc `seconds/len(beats) > 7`, đối xứng với ràng buộc "quá nhanh" (`< 1.5`) đã có sẵn. Đây là nơi tự nhiên nhất vì đã có sẵn `estimates(b, c)` tính giây ước lượng theo cảnh.
- **`sys/schemas/content-v3.json`**: không đổi `minItems` tĩnh (không biết thời lượng), giữ nguyên; ràng buộc động nên nằm ở `story_plan.py` như trên.
- **`sys/machine_review.py`** (dòng ~40–52, phần prompt cho bộ đánh giá máy chế độ `auto`): bổ sung câu hướng dẫn định lượng cho `visual_beats_and_text_policy` và `beat_timing`, ví dụ nêu rõ ngưỡng ~8–10 giây/ảnh mới và ~5–7 giây/nhịp, để bộ đánh giá có căn cứ chấm fail thay vì chỉ phán đoán định tính. File này không phải `prompt_templates.py` nên được phép sửa khi người dùng yêu cầu phát triển mã.
- **`.agents/skills/vp-content/SKILL.md`**: thay câu định tính "đủ ảnh và visual beats" bằng con số cụ thể (ví dụ khoảng giây/ảnh, khoảng giây/nhịp) để agent viết kịch bản tự đặt đúng số ảnh ngay từ đầu, không phải chờ bị `reject`.
- **`sys/scripts/story_plan.py` `review_plan()`**: hiện đã in ra "`X cảnh · Y hình logic · Z nhịp`" trong bản duyệt — có thể bổ sung số liệu "giây trung bình giữa các ảnh" để người duyệt (chế độ `review`) nhìn thấy mật độ ngay khi đọc `review.md`, không cần tính tay.

Tất cả thay đổi trên đều là mã điều phối/kiểm tra nội bộ (story_plan, schema, machine_review, skill hướng dẫn) — không đụng `prompt_templates.py`, không bật video AI, không đổi renderer, đúng ràng buộc AGENTS.md. **Đây là đề xuất, chưa thực hiện** — task hiện tại chỉ đọc, không sửa mã.

### Tác động chi phí Flow

- Job 5 phút hiện tại: **22 ảnh cảnh** (+4 ảnh tham chiếu nhân vật = ~26 lượt sinh ảnh thành công, 28–30 lượt gửi kể cả thử lại).
- Với mục tiêu ~3 ảnh/cảnh (thay vì ~2,2 ảnh/cảnh hiện tại): job 5 phút cần khoảng **30–32 ảnh cảnh** (+4 tham chiếu ≈ 34–36 lượt) — tăng khoảng **+40–50%** số lượt gọi Flow so với hiện tại.
- Job dài 10–15 phút (20 cảnh, hiện 40 ảnh cảnh) sẽ cần khoảng **55–60 ảnh cảnh** ở mật độ đề xuất — cũng tăng **~40–50%**.
- Vì cấu hình `flow_batch=true` gửi ảnh theo từng "wave" (đợt) qua hàng đợi của công cụ Flow, và hàng đợi đó hiện đầy localStorage ở khoảng 20–22 ảnh/đợt (đang được sửa riêng, ngoài phạm vi báo cáo này), tăng mật độ ảnh theo đề xuất trên sẽ cần **nhiều đợt (wave) hơn** cho mỗi video — ví dụ job 5 phút từ 2 đợt lên có thể 2–3 đợt, job dài từ ~2–3 đợt lên ~3–4 đợt. Nên triển khai tăng mật độ ảnh **sau khi** giới hạn hàng đợi 20–22 ảnh/đợt được khắc phục, để tránh chồng hai vấn đề cùng lúc.
- Chi phí ghi trong hệ thống hiện là **giả định do người dùng chỉ định** (`flow_require_ui_evidence=false`), không phải đã xác minh — con số Flow-call ở trên chỉ là số lượt gọi, không quy đổi tiền/credit vì dự án không xác nhận đơn giá.

## Tệp bằng chứng đã dùng

- `video/h001-demo-2min/h001-first-2-minutes-preview.mp4` — 4 khung hình trích bằng ffmpeg
- `sys/reports/h001-2min-preview/images/*.jpg`, `README.md`
- `sys/runs/tieng-go-sau-guong-thu-20260924/revisions/content/3/content.json`
- `sys/runs/thu-5p-h007f/revisions/content/1/content.json`, `sys/runs/thu-5p-h007g/revisions/content/1/content.json`
- `sys/runs/thu-5p-h007g/revisions/audio/1/output.json` (thời lượng đo thật)
- `sys/runs/thu-5p-h007f/flow/attempts/`, `sys/runs/thu-5p-h007g/flow/attempts/` (số lượt gọi Flow thật)
- `sys/renderer/index.tsx`, `sys/scripts/story_plan.py`, `sys/schemas/content-v3.json`, `sys/machine_review.py`, `sys/docs/horror.md`, `.agents/skills/vp-content/SKILL.md`, `sys/config.json`
