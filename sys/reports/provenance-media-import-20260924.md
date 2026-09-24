# Nhập media có nguồn gốc giữa hai job v3

Ngày 24/09/2026. Triển khai trong worktree phát triển `/tmp/videoclaude-h001-reuse`; không chạy lệnh nhập trên H001f, không sửa job/ledger/SQLite đang sống.

## Hợp đồng

`pilot.py import-media NEW_JOB --from SOURCE_JOB [--part audio|images|all]` chỉ chạy khi NEW_JOB là auto, có content revision đã duyệt độc lập và module được nhập còn nguyên trạng pending. SOURCE_JOB phải là auto, content có quyết định máy khớp manifest, báo cáo và event `machine_approved`; audio/images phải được chấp nhận kỹ thuật. Không gọi TTS, Flow hoặc AGY khi nhập.

`audio` cho phép content mới sửa kế hoạch hình nếu brief và mọi câu narration Việt/Anh giữ nguyên. `images`/`all` yêu cầu content payload giống nguồn từng trường. Bản ảnh nguồn phải qua cả checkpoint references/final, mọi request được chọn phải `downloaded`, registration/confirmation/base/UI proof hợp lệ và không có request cùng mục tiêu còn `submitted`/`ambiguous`.

Importer chạy lại kiểm tra kỹ thuật trên nguồn bằng mã hiện tại mà không gọi `Pilot.refresh(source)` hay sửa integrity cũ. Nó chép nguyên byte từng file nguồn vào `imports/`, ghi hash và đường dẫn trong receipt `vp-media-import-1`, cùng hash envelope, quyết định content và ID/hash event. Receipt được xác minh trước mỗi revision và khi validate, và đưa vào media review manifest. Revision audio/images của NEW_JOB có input_versions mới, payload chuẩn với cặp `import_kind=source-copy`/`import_receipt`; bản quyết định chất lượng media/video không được chép. Sau khi có đủ hai module, Pilot tạo media review mới nhưng chưa duyệt.

## Kiểm thử

- 12 kiểm thử mới: nhập đầy đủ, CLI audio-only, kế hoạch hình khác nhưng narration không đổi, chặn narration khác, dữ liệu nguồn sửa/thiếu, request ảnh mơ hồ, bản sao hoặc proof bị sửa/xóa, quyết định content giả thiếu event, nguồn có integrity cũ, producer tùy ý không có receipt, và nhánh Flow thường vẫn giữ kiểm tra gate/journal.
- 78 kiểm thử nhắm vào importer, workflow và image pipeline đạt. Trước các guard cuối, toàn bộ 347 kiểm thử Python đạt sau khi liên kết runtime `.venv`/`node_modules` đã cài sẵn vào worktree.

## Giới hạn cần xử lý riêng

Importer chưa ghép lại từng ảnh không đổi khi content đổi kế hoạch hình. Với H001, SC13/SC16/SC17 cần sửa hình; đường an toàn hiện tại là nhập riêng WAV rồi sản xuất ảnh mới. Một cache nhập từng ảnh cần validator riêng cho prompt, character registration và toàn bộ chuỗi `based_on`, sau đó mới có thể bỏ qua các yêu cầu Flow đã có ảnh. Không tạo journal mới giả rằng job kế nhiệm đã gửi các request cũ.

Horror ledger đang giữ H001 cho H001f. `horror.policy.check` không cho tạo job kế nhiệm cùng hạt giống khi quyền giữ chỗ chưa được chuyển bằng quy trình chính thức. Không giải phóng/sửa ledger chỉ để thử importer. Việc tạo job kế nhiệm H001 và lựa chọn chấp nhận hay thay ảnh có watermark là quyết định tách biệt trước khi nhập thật.
