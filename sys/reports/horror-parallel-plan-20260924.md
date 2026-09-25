# Kế hoạch chạy song song — Tiếng gõ sau tấm gương

Job: `tieng-go-sau-guong-thu-20260924` · H001 · 16:9 · truyện 10–15 phút · lấy khoảng 5 phút đầu từ video hoàn chỉnh · chế độ `auto`.

## Nguyên tắc điều phối

Một agent giữ quyền gọi `pilot.py run/resume/reject` cho job. Các agent còn lại chỉ kiểm tra hoặc chuẩn bị độc lập; không chạy hai thao tác lên cùng job, không sửa revision, review, SQLite hay cấu hình để vượt cổng. `content → media → video` vẫn nối tiếp. Bên trong media, âm thanh chạy trước, đo thời lượng thật rồi mới đến ảnh và nhịp hình.

| Lượt | Agent Luna High | Việc có thể chạy cùng lúc | Bàn giao | Điểm phụ thuộc |
|---|---|---|---|---|
| A | Kịch bản | Rà lời dẫn 20 cảnh, câu móc đầu, ngôi kể, độ dài, cú lật, lời kết, quote/anchor/coverage và chính sách horror. Đề xuất lỗi theo cảnh và câu trích. | Danh sách lỗi cụ thể; không sửa bản đã lưu. | Có bản nháp content. |
| A | Giọng | Kiểm tra môi trường Gwen, giọng tham chiếu, GPU, bài thử TTS, cách nghe WAV và các nguy cơ phát âm. | Báo cáo sẵn sàng audio. | Không cần content duyệt. |
| A | Flow/dựng | Kiểm tra trạng thái phiên Flow, model, tham chiếu mascot, hàng đợi và cấu hình máy; rà tài nguyên renderer và cách xem preview. | Báo cáo sẵn sàng ảnh/video, blocker. | Không cần content duyệt. |
| B | Agent điều phối | Hoàn tất `run JOB content`, xem đánh giá máy và sửa bằng `reject content` nếu cần. | Content revision có quyết định hợp lệ. | Xong A phần kịch bản. |
| C | Agent điều phối | `run JOB media`: tạo giọng, đo WAV, rồi tạo/đối chiếu ảnh và phụ đề. | Media review và quyết định máy có bằng chứng nghe/xem thật. | Content đã đạt. |
| C | Agent giọng + agent ảnh | Rà WAV/phát âm và ảnh/nhân vật ngay khi artifact tương ứng có mặt, chỉ đọc và báo lỗi. | Góp ý sửa qua `reject media` đúng phần nếu cần. | Artifact media đã tồn tại. |
| D | Agent điều phối | `run JOB video`, kiểm tra video tự duyệt, xuất bản chính thức và `horror/bank.py mark JOB`. | MP4 hoàn chỉnh. | Media đã đạt. |
| D | Agent xem thành phẩm | Kiểm tra thời lượng, khung hình, đồng bộ tiếng/hình/phụ đề trên MP4; đề xuất lỗi theo mốc thời gian. | Báo cáo nghe/xem. | Bản render có thật. |
| E | Agent điều phối | Trích khoảng 5 phút đầu **từ MP4 đã hoàn tất** để người dùng nghe thử; bàn giao video đầy đủ, đoạn thử, lời dẫn và sơ đồ. | Hai MP4 có đường dẫn thật. | Video đã được duyệt và xuất. |

## Trạng thái lúc lập kế hoạch

- Revision 1 của content đã được máy duyệt nhưng bị từ chối lại vì lỗi kể chuyện ở SC01, SC16, SC19 và SC20.
- Revision 2 đang viết theo nhóm cảnh. Các nhóm SC01–SC12 đã lưu; cần tiếp tục từ nhóm còn thiếu bằng `pilot.py run JOB content`.
- Ba subagent `gpt-6-luna` mức `high` được gọi lại sau khi người dùng đăng nhập và đã hoàn tất lượt kiểm tra song song. Agent kịch bản xác nhận câu mở đầu mới vào ngay chi tiết tấm gương; còn yêu cầu sửa cách giải thích ở SC16, tính nhất quán ở SC19 và dư âm lời kết SC20. Agent giọng xác nhận Gwen/GPU/model cache sẵn sàng; 11 bài kiểm thử giả lập đạt, chưa tổng hợp lời dẫn thật cho job. Agent Flow thấy phiên vẫn `disconnected`, cấu hình máy chưa xác minh đăng nhập và nhánh auto xem/nghe media chưa được nghiệm thu. Cả ba chỉ đọc, không chỉnh file hoặc vượt cổng.
- `agy` không có lệnh `preview`; nội dung xem qua `reviews/.../review.md`, WAV/ảnh trong media review và MP4 trong video review. Trang nghe thử giọng độc lập: `reports/voice-audition-20260924/index.html`.

Không coi lỗi đăng nhập của subagent là quyết định của job. Agent điều phối vẫn có thể tiếp tục job nếu công cụ của phiên hiện tại còn hoạt động.

## Yêu cầu tăng tốc audio sau lỗi Gwen

Người dùng yêu cầu chia việc tổng hợp theo cảnh, mỗi lượt tối đa khoảng 2 phút lời đọc. Bản thử H001 có cảnh ước 30–60 giây. Một checkout riêng đang sửa Gwen để xử lý từng cảnh và lưu WAV ngay sau từng câu/cảnh thành công; lượt sau chỉ tạo phần chưa có. Không đổi mã bảo vệ của job H001 đang chạy. Nếu lượt audio hiện tại thành công, bàn giao đoạn nghe 5 phút đầu ngay; nếu thất bại, chuyển sang job mới theo quy trình integrity, không sửa baseline của job cũ.
