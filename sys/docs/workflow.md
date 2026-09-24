# Quy trình v3: ba phần, hai chế độ

Đây là nguồn hướng dẫn sản xuất hiện hành. Các báo cáo trong reports/ là lịch sử kiểm thử, không phải quy trình hoặc dấu duyệt hiện tại.

| Phần | Đầu ra cần xem | Chuyển bước |
|---|---|---|
| content | Kịch bản Việt/Anh, số cảnh, nhân vật, ý bắt buộc, thời lượng ước tính (tham khảo, không rào duyệt) | Người hoặc máy duyệt nội dung |
| media | WAV Việt/Anh (chạy trước), toàn bộ cảnh/ảnh, ảnh nhân vật đã đăng ký, phụ đề, thời lượng thật | Người hoặc máy duyệt chung |
| video | Video hoàn chỉnh cho các tỷ lệ đã yêu cầu | Người hoặc máy duyệt thành phẩm |

Các module control/images/audio/render vẫn là bước kỹ thuật nội bộ. Không còn lệnh duyệt công khai cho control/images/audio/render, không còn điểm duyệt ba cảnh đầu. Ảnh chuẩn được kiểm tra kỹ thuật trước khi làm toàn bộ cảnh; trong review, việc so sánh nhân vật chờ mốc media và được ghi rõ là pending, không giả là đã khớp.

`workflow.STAGES['media']` chạy audio trước images: giọng đọc chạy local, miễn phí, đo được thời lượng thật, nên kịch bản lệch khoảng thời lượng hỏng ở bước audio trước khi tốn credit Flow cho ảnh. Trong `Pilot.gate`, hai module audio và images vẫn độc lập để `flow-login`/`flow-preflight` dùng được bất cứ lúc nào; chỉ thứ tự trên đường sản xuất do STAGES quyết định.

## Chế độ Kiểm tra

```bash
python3 pilot.py new video-001 --brief examples/story-v3/brief.json --mode review
python3 pilot.py status video-001
python3 pilot.py next video-001
python3 pilot.py run video-001
```

Nếu draft/content.json chưa có, adapter Antigravity tài khoản tạo bản nháp. Nếu đã có thì dùng bản nháp đó. Máy kiểm tra kỹ thuật và dừng ở content revision N. Xem đường dẫn review do lệnh trả về. Chỉ sau phản hồi thực tế của người dùng mới gọi:

```bash
python3 pilot.py approve video-001 content --revision 1 --note 'NGUYÊN VĂN PHẢN HỒI THẬT'
python3 pilot.py run video-001
```

Thay số revision bằng giá trị hiện tại; văn bản ví dụ không phải bằng chứng đồng ý. Mốc kế tiếp là media, sau đó video; dùng cùng cú pháp approve với đúng tên phần. Không xin thêm duyệt control, ảnh chuẩn hoặc ba cảnh đầu.

Flow cần phiên đăng nhập và đúng model/tham chiếu. Mặc định flow_require_ui_evidence=false không yêu cầu screenshot trước gửi; chi phí chưa được xác minh. Sau timeout vẫn phải đối chiếu bằng chứng thật; xem M2-FLOW.md. Đây không phải mốc duyệt nội dung bổ sung.

## Chế độ Tự động

```bash
python3 pilot.py new auto-001 --brief examples/story-v3/brief.json --mode auto
python3 pilot.py run auto-001
```

Máy dùng Antigravity qua tài khoản để đánh giá nội dung và artifact, không dùng API key trả phí. Báo cáo được lưu trong machine-reviews/; quyết định ghi actor=machine. Chỉ pass khi mọi tiêu chí bắt buộc đạt và đầy đủ file được xem/nghe. Công cụ không hỗ trợ nghe WAV/xem video phải trả unsupported; không lấy metadata thay thế chất lượng.

Khả năng đánh giá đa phương thức phụ thuộc công cụ của phiên Antigravity; chưa được coi là nghiệm thu hàng loạt chỉ vì các bài test đạt. Không tự hạ tiêu chí khi thiếu khả năng đánh giá. Job thất bại giữ artifact để sửa qua reject; không tự tạo lại ảnh sau timeout.

Chạy hàng đợi hữu hạn chứa mã các job auto đã tạo:

```json
["auto-001", "auto-002"]
```

```bash
python3 pilot.py batch --queue queue.json
```

Các job chạy lần lượt để tránh tranh RAM trên máy 16 GB. Lỗi riêng một job được ghi needs_attention, chuyển job tiếp theo. Lỗi chung đăng nhập/CAPTCHA/preflight dừng hàng đợi; hết hạn mức tạo ảnh thì chuyển profile kế tiếp (xem experiments/b2_illustrator/CONTROLLER.md), hết mọi profile mới dừng. Chạy lại hàng đợi bỏ qua job đã hoàn tất; báo cáo từng lượt nằm trong .state/batch-results/. Không tự chạy nền vô hạn hoặc tự tạo lịch.

## Sửa và tiếp tục

```bash
python3 pilot.py reject video-001 media --revision 1 --scene SC03 --note 'Lý do sửa ảnh'
python3 pilot.py reject video-001 media --revision 1 --character C01 --note 'Lý do sửa nhân vật'
python3 pilot.py reject video-001 media --revision 1 --part audio --note 'Lý do tạo lại âm thanh'
python3 pilot.py reject video-001 media --revision 1 --part audio --scene SC03 --note 'Lý do đọc lại cảnh SC03'
python3 pilot.py reject video-001 content --revision 1 --note 'Lý do sửa lời dẫn'
python3 pilot.py reject video-001 video --revision 1 --note 'Lý do dựng lại'
python3 pilot.py resume video-001
```

Mỗi ví dụ là một lựa chọn riêng, không chạy nối tiếp trên cùng revision. `--part audio` không kèm `--scene` đánh dấu đọc lại toàn bộ; kèm `--scene` chỉ đánh dấu cảnh đó — số lần bị từ chối của từng cảnh nằm trong khoá cache TTS (và seed giọng Anh) để tránh trả lại đúng bản vừa bị chê. Sửa nội dung ở draft/content.json. Thay brief qua revise-brief, không sửa brief đã lưu. Thay ảnh giữ audio hợp lệ; mọi thay đổi media buộc duyệt lại media trước dựng. Không sửa file đã duyệt.

Mode được giữ cố định trong job. Job trước v3 chỉ đọc lịch sử; không tự đổi baseline hoặc biến duyệt cũ thành duyệt v3. Chưa có công cụ chuyển job cũ tự động.

## Kho từ vựng cho kênh học từ

Job dạy từ vựng lấy brief từ `vocab/bank.py` thay vì viết tay: mỗi video một nghĩa, ledger
giữ dấu từ đã làm, từ nhiều nghĩa tách thành nhiều mục. Dữ liệu kho (sources, bank.jsonl,
ledger) không nằm trong integrity baseline nên thêm từ không chặn job đang chạy.

Đây không còn là quy ước: `config.brief_policies` trỏ tới `vocab.policy:check`, chạy trong
`Pilot.new` và `revise_brief`. Brief có dấu hiệu dạy từ vựng mà thiếu mã mục kho, mang mã
không có thật, hoặc mang mục đang giữ chỗ cho job khác đều bị từ chối trước khi job ra đời.
Brief không dạy từ vựng không bị ảnh hưởng — bộ điều phối vẫn không gán cứng chủ đề nào,
toàn bộ hiểu biết về từ vựng nằm trong `vocab/policy.py`. Xem [vocabulary.md](vocabulary.md).

## Kịch bản đa nhịp

Job mới dùng brief/content 3.0: cảnh → hình → nhịp, chữ tạo cùng hình theo danh sách cho phép, ước tính riêng Việt/Anh, đối chiếu ý bắt buộc hai ngôn ngữ (quote/quote_en) và phản hồi sửa có đối chiếu. Không gán cứng chủ đề. Xem [story-planning.md](story-planning.md) cho cấu trúc và giới hạn thời điểm nội suy.

## Giọng đọc và đầu ra

Việt: Gwen-TTS nhân bản giọng `assets/voices/pham-tuyen-gwen` qua `.venv-gwen` (GPU CUDA, cần khoảng 2,5 GB VRAM, đọc từng câu, xuất 48 kHz). Anh: Alba / Pocket TTS CPU INT8, tốc độ gốc (cần cài lại `.venv-en`). Bản 9:16 có tiếng Việt/phụ đề; 16:9 có tiếng Anh, timeline riêng và ẩn phụ đề. Dual tạo cả hai. Phụ đề cắt một lần ở Python (adapters.subtitle_cues); .srt và khung hình dùng chung danh sách cue nên luôn khớp nhau. Thời lượng kiểm tra theo brief, không nới bằng config. Tạo video AI bị khóa.

## Dựng video theo đoạn

Video không dựng một lần cả timeline. `adapters.render` chạy `renderer/render.mjs DIR --prepare` (kiểm tra bố cục phụ đề, ghi `plans.json`, chưa dựng), rồi `render_parts.py` chia từng bản đầu ra thành đoạn khoảng `render_segment_seconds` giây (config, mặc định 120; video 20 phút ≈ 10 đoạn). Chỉ cắt ở đầu cảnh, không cắt giữa một câu phụ đề; cảnh dài hơn mức mục tiêu giữ nguyên trong một đoạn, đoạn đuôi quá ngắn gộp vào đoạn trước.

Mỗi đoạn là khung [đầu, cuối) của đúng composition đầy đủ (`frameRange` của Remotion), dựng không tiếng. Khung hình chỉ phụ thuộc số khung tuyệt đối nên chuyển cảnh, zoom/trượt và phụ đề giống hệt bản dựng một lần. Các đoạn được nối bằng concat demuxer của ffmpeg, sao chép luồng không mã hóa lại khi mọi đoạn cùng thông số (codec, profile, kích thước, pix_fmt, fps, time_base, extradata); khác thông số thì nối bằng mã hóa lại và ghi `join: reencode`. Toàn bộ bản âm thanh đã master (mix.wav hoặc narration.wav) được ghép một lần sau cùng, AAC 320k 48 kHz như trước, nên chỗ nối không thể có tiếng click hay lệch.

Cache đoạn nằm ở `runs/JOB/cache/render-parts/<hash>.mp4`. Hash gồm lát cảnh/phụ đề mà đoạn hiển thị (ảnh tính theo nội dung file), thuộc tính dựng của bản đầu ra, khoảng khung, mã nguồn renderer, phiên bản Remotion và `fps`. Chạy lại chỉ dựng đoạn thiếu hoặc đã đổi: thay ảnh một cảnh chỉ dựng lại đoạn chứa cảnh đó. Đổi độ dài âm thanh của một cảnh làm mọi đoạn phía sau lệch thời điểm nên phải dựng lại các đoạn đó.

Đoạn lỗi tự thử lại một lần. Lỗi lần hai thì render bị blocked, thông báo nêu số thứ tự đoạn, khoảng khung, cảnh và log `revisions/render/N/parts/<file>-part-NN.log`; các đoạn đã đạt vẫn nằm trong cache, lần chạy sau chỉ dựng đoạn còn thiếu. Kiểm tra bắt buộc: số khung mỗi đoạn đúng khoảng, đoạn bắt đầu bằng keyframe, file nối đủ số khung của timeline, âm thanh nguồn dài đúng timeline và luồng âm thanh/hình sau ghép lệch không quá 0,05 giây. Kết quả ghi ở `render-parts.json` trong revision. Các cổng render cũ trong pilot.py giữ nguyên.

Một đoạn nhìn sai dù đầu vào không đổi (hash giữ nguyên): chạy `python3 render_parts.py forget runs/JOB/revisions/render/N/render-parts.json --part K` (thêm `--file video_16x9.mp4` với dual). Lệnh chuyển file cache của đoạn K sang `cache/render-parts/rejected/`, không xóa; sau đó `reject JOB video` rồi `resume JOB`, bản mới chỉ dựng lại đoạn K.

`node renderer/render.mjs DIR` không kèm chế độ vẫn là đường dựng một lần cũ, chỉ dùng cho benchmark/script lịch sử, không dùng cho job.

## Dọn dẹp

Không xóa lịch sử, bằng chứng Flow hoặc model đang dùng để làm sạch mã cũ. Script dọn cũ xóa toàn bộ attempts đã được bỏ. Xuất thành phẩm chỉ sau video được duyệt; chưa tự dọn artifact của job.
