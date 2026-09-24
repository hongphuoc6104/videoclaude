# H001f: đường tiếp tục hợp lệ và thiết kế nhập media có nguồn gốc

Ngày 24/09/2026. Phân tích chỉ đọc trên job `h001-auto-20260924f`; không sửa revision, review, journal hoặc SQLite của job.

## Trạng thái xác minh

- `python3 pilot.py status h001-auto-20260924f` từ checkout chính trả `Protected implementation changed`. `Pilot.integrity()` so sánh toàn bộ `integrity.json` với danh sách hash mã được bảo vệ và chặn trước mọi thao tác sản xuất.
- Dấu vân tay có 126 mục; đúng một mục khác giữa job và checkout chính: `experiments/b2_illustrator/session.mjs`. Thay đổi này sửa việc mở tab khi xoay Chrome profile.
- Checkout `/home/hongphuoc/.codex/worktrees/h001f-frozen/videoclaude/sys` giữ đúng file cũ và trỏ tới `runs`/`.state` đang dùng. Từ đó `status` thành công: content revision 1 đã duyệt, media revision 1 đang chờ máy duyệt, video chưa chạy. `next` trả `machine_review` ở media.
- Media của job gồm audio revision 1 với 190 segment và WAV 877.4346458333337 giây; ảnh final revision 3 với 84 ảnh cảnh. Bản kiểm tra kỹ thuật đã tạo media review 1. Các artifact này chưa được quyết định chất lượng.

## Vì sao hiện chưa thể nhập an toàn sang job mã mới

1. CLI hiện không có lệnh nhập. `workflow.new()` tạo job mới và `Pilot.run()` gọi lại `adapters.audio()` hoặc `image_pipeline.produce()` cho media.
2. Envelope audio và ảnh ghi `input_versions.content` bằng hash revision content cũ. Revision content của job mới mang `job_id`, đường dẫn file và hash envelope mới, nên không thể sao chép envelope nguyên trạng rồi duyệt: `Pilot.validate()` bắt `input_versions` khớp job mới.
3. Ảnh còn ghi `content_hash`, `signature`, tên reference theo job cũ và các request/registration journal. `image_pipeline.check()` đối chiếu tất cả với nội dung, chỉnh sửa ảnh, prompt, ảnh được tải, xác nhận đăng ký, bằng chứng UI và base image của job hiện tại. Bằng chứng UI có đường dẫn tuyệt đối tới ảnh nguồn. Chép hoặc sửa các journal để khớp job mới sẽ làm sai xuất xứ và có thể khiến một ảnh đã tạo bị gửi lại.
4. `workflow.approved()` chỉ chấp nhận quyết định mới kèm manifest hash, báo cáo máy và event ký bởi hàm duyệt. Không được chép quyết định media cũ hoặc tạo quyết định giả. Thực tế H001f chưa có quyết định media hợp lệ.

## Đường xử lý ngay

Tiếp tục H001f bằng checkout frozen. `run h001-auto-20260924f media` chỉ đi qua cổng máy duyệt media hiện có; không gọi Flow khi media review còn hiệu lực. Sau quyết định media hợp lệ mới chạy `video`, rồi đánh giá video thật và xuất qua Pilot. Nếu AGY tiếp tục không đánh giá được, giữ job chờ xử lý; không chuyển sang duyệt giả. Không cần nhập media chỉ để vượt thay đổi của `session.mjs`.

## Thiết kế tính năng nhập chính thức nếu cần mã mới

Thêm lệnh có khóa `import-media NEW_JOB --from SOURCE_JOB`, chỉ sau content của NEW_JOB được duyệt độc lập. Lệnh chỉ đọc SOURCE_JOB; xác minh brief và nội dung byte-for-byte theo payload, nguồn content đã duyệt, envelope/audio/images và mọi file/evidence có hash khớp, nguồn ảnh có request `downloaded` và đăng ký/reference đúng chuỗi. Không dùng `Pilot.refresh()` với mã mới để ép job cũ qua integrity; xác minh theo bản manifest và baseline của nguồn.

Sao chép các byte artifact vào `runs/NEW_JOB/imports/SOURCE_JOB/<hash>/` cùng receipt chứa hash file nguồn, hash envelope, revision nguồn, mã nguồn gốc và thời điểm nhập. Không sửa request hay UI proof cũ để giả chúng thuộc NEW_JOB. Tạo revision audio/images mới bằng nhánh `imported_provenance` trong bộ kiểm tra kỹ thuật: audio vẫn đối chiếu narration, timeline, duration, WAV và SRT; ảnh vẫn đối chiếu thứ tự cảnh, prompt, ratio, nhân vật, chuỗi base image, hash tải về, journal và UI proof nguồn. Bộ kiểm tra nhập phải hiểu đường dẫn bên trong receipt là bằng chứng của SOURCE_JOB và từ chối mọi thay đổi. Ghi input_versions của NEW_JOB và event nhập riêng. Tạo media manifest/review mới, chạy machine review mới trên WAV/ảnh thực; chỉ sau quyết định hợp lệ mới mở video.

Không triển khai nửa vời nhánh này bằng cách chép envelope hoặc sửa journal. Cần kiểm thử các trường hợp content khác, ảnh thiếu, request ambiguous, source hash đổi, base image sai, xác nhận nhân vật thiếu và cố gắng dùng lại quyết định cũ.
