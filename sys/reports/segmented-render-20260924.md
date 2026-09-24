# Kiểm tra bộ dựng video theo đoạn — 24/09/2026

## Kết luận

Bộ dựng chia đoạn đã chạy được bằng Remotion thật trên mẫu kiểm tra ngắn. Bốn đoạn được nối bằng sao chép luồng hình, đủ 120/120 khung hình ở 30 fps; âm thanh được ghép một lần sau khi nối. Hình quanh ba điểm nối khớp rất sát với bản dựng một lượt. Cache tái sử dụng cả bốn đoạn ở lần chạy kế tiếp. Đây là kiểm tra kỹ thuật trên mẫu tổng hợp 4 giây, chưa phải nghiệm thu video H001 hoặc quy trình `auto` dài 10–15 phút.

## Phần đã khôi phục và hoàn tất

- `adapters.render` chuẩn bị kế hoạch và kiểm tra bố cục qua `renderer/render.mjs --prepare`, sau đó gọi `render_parts.py` dựng theo đầu cảnh, tạo stills và ghi `render-parts.json`.
- Mỗi đoạn lấy khoảng khung hình tuyệt đối của cùng composition, chỉ chứa luồng hình; file tiếng được ghép vào video hoàn chỉnh một lần.
- Cache khóa theo nội dung ảnh, cảnh, phụ đề hiện trên đoạn, kích thước, fps và mã/phiên bản renderer. Có kiểm tra số khung, keyframe đầu đoạn, thông số codec trước khi nối, thời lượng hình/tiếng sau ghép. Đoạn lỗi được thử lại một lần và giữ các đoạn đã đạt.
- Sửa lệnh `forget`: khi cùng đoạn bị đặt riêng nhiều lần, các bản trong `rejected/` có tên khác nhau, tránh ghi đè bằng chứng trước đó. Bài kiểm tra tương ứng đã bổ sung.

## Bằng chứng chạy thật

Mẫu tại `scratch/segmented-render-20260924/` có bốn cảnh một giây, bốn ảnh và phụ đề riêng, nhạc thử dạng sóng 220 Hz dài 4 giây. Đây là dữ liệu thử tổng hợp, không phải cảnh hoặc lời dẫn H001. Đã chạy `--prepare`, dựng bốn đoạn bằng `--parts`, rồi dựng một lượt qua chế độ cũ làm bản đối chứng.

| Kiểm tra | Kết quả |
| --- | --- |
| Số đoạn / khoảng khung | 4 đoạn: `[0,30)`, `[30,60)`, `[60,90)`, `[90,120)` |
| Dựng đoạn lần đầu | 4 đoạn mới, không lỗi; tổng lượt `--parts` 14,1 giây |
| Luồng từng đoạn | Chỉ H.264, không có audio; keyframe đầu đoạn và thông số codec đồng nhất |
| Nối / video cuối | `join: copy`; 120 khung hình, 1080×1920, 30 fps; hình và tiếng đều 4,000 giây theo ffprobe |
| Chạy lại | 4/4 đoạn đọc từ cache, 0 đoạn render mới |
| Đối chiếu hình 120 khung | PSNR thấp nhất 53,42 dB; SSIM thấp nhất 0,999329 |
| Tại điểm nối | Khung 29→30, 59→60, 89→90 chuyển đúng cảnh và phụ đề; SSIM từng khung quanh điểm nối ≥ 0,999476 |
| Âm thanh tại 1, 2, 3 giây | Bước nhảy giữa hai mẫu liền kề lần lượt 0,002166; 0,002160; 0,002167, nằm trong biên độ thay đổi thường của sóng thử (toàn file tối đa 0,002348) |

File kiểm tra: [`segmented.mp4`](../scratch/segmented-render-20260924/segmented.mp4), [`reference.mp4`](../scratch/segmented-render-20260924/reference.mp4), [`render-parts.json`](../scratch/segmented-render-20260924/sample/render-parts.json), [`segmented.log`](../scratch/segmented-render-20260924/sample/segmented.log), [`boundary-contact.png`](../scratch/segmented-render-20260924/boundary-contact.png), [`psnr.log`](../scratch/segmented-render-20260924/psnr.log), [`ssim.log`](../scratch/segmented-render-20260924/ssim.log). Audio AAC khi giải mã có thể có mẫu đệm ở cuối, nên số giây trong bảng lấy từ thời lượng stream mà trình phát sử dụng; bài kiểm tra bước nhảy chỉ xét các điểm nối nằm giữa timeline.

## Kiểm tra tự động

`.venv/bin/python -m unittest tests.test_render_parts`: **17/17 đạt**, gồm chia tại đầu cảnh, không cắt giữa phụ đề, cache theo ảnh/phụ đề/mã renderer, retry và khôi phục đoạn lỗi, chặn lệch số khung/âm thanh, giữ hai bản `rejected/`, đường gọi adapter và `--prepare` thật. `git diff --check` không báo lỗi định dạng.

## Giới hạn còn lại

Chưa chạy một video thực dài 10–15 phút hoặc bản dual qua toàn bộ Pilot; việc này cần job sản xuất mới và các cổng content/media/video hợp lệ. Mẫu 4 giây kiểm chứng tính đúng của nối đoạn trong điều kiện đã nêu, không chứng minh tốc độ hoặc độ ổn định khi có nhiều ảnh và âm thanh dài.
