# Bộ nghe thử giọng truyện ma — 24/09/2026

[Mở trang nghe thử](index.html) và đánh dấu những giọng muốn dùng. Trang lưu lựa chọn trong trình duyệt trên máy này; nút **Tạo phản hồi để gửi** giúp sao chép danh sách lựa chọn.

**Đính chính:** đây là phép thử **chất giọng**, chưa phải phép thử diễn xuất. Hai đoạn khác nhau không chứng minh cùng một giọng có thể chuyển từ bình tĩnh sang sợ hãi, thì thầm hay hoảng loạn. VieNeu 3.8.1 bỏ qua `style`; ZeroTTS và Piper trong bộ này cũng không được điều khiển cảm xúc. Đang chuẩn bị phép thử biểu cảm riêng để đánh giá đúng yêu cầu kể truyện ma.

## Mẫu đã tạo

| Engine | Giọng riêng | Mẫu WAV | Máy xử lý | Ghi chú |
| --- | ---: | ---: | --- | --- |
| VieNeu v3 Turbo | 25 | 50 | RTX 3050 4 GB, CUDA FP32 | Phong cách nằm trong giọng preset. Bản `vieneu` 3.8.1 đang cài bỏ qua tham số `style`; không coi `doc_truyen` là điều khiển diễn xuất. |
| ZeroTTS | 8 | 16 | ONNX trên CPU | Có thử CUDA trên RTX 3050, nhưng hết VRAM trong nhiều đoạn. Bộ CPU chạy đủ. |
| Piper tiếng Việt | 3 | 6 | ONNX CUDA trên RTX 3050 | Hai giọng `25hours_single` và `vivos` báo thiếu một số phoneme khi đọc; cần nghe kỹ phát âm. |
| **Tổng** | **36** | **72** | | |

Mỗi giọng đọc **cùng hai đoạn nguyên văn** từ `runs/thu-5p-h007g/revisions/content/1/content.json`: đoạn tự sự ở SC02 và đoạn hồi hộp có thoại ở SC05. Đây là thí nghiệm độc lập. Không sửa job, revision, tệp giọng đã duyệt hay quyết định duyệt nào.

Các WAV đã qua kiểm tra kỹ thuật: đủ 72 tệp, mono, không rỗng, thời lượng 5,67–14,8 giây. Trang nghe thử đã được mở bằng trình duyệt, tải được audio và giữ lựa chọn sau khi tải lại. Chưa có đánh giá bằng tai người; độ tự nhiên, diễn xuất và phát âm phải do người nghe chấm.

## Máy 2 GB và 4 GB

Máy đang dùng có RTX 3050 4 GB. GPU đã chạy thực tế với VieNeu và Piper. ZeroTTS có thể khởi tạo CUDA khi VRAM trống nhưng không hoàn tất ổn định trên 4 GB; dùng CPU cho engine đó. Máy Quadro 2 GB không có trong phiên này để thử trực tiếp. Piper và ZeroTTS có đường chạy CPU, nên vẫn có phương án cho máy 2 GB; VieNeu cũng có ONNX CPU. Không suy diễn rằng mọi engine GPU sẽ vừa Quadro 2 GB.

## Khảo sát thêm

- [V-TTS](https://github.com/tronghieuit/v-tts) công bố 5 giọng CPU và 6 giọng mẫu để clone. Đã thử cài và tải checkpoint mặc định nhưng kho model trả `401 Repository Not Found`; không thể tạo mẫu từ mã nguồn công khai hiện tại. Dự án ghi giấy phép CC BY-NC 4.0.
- [F5-TTS-Vietnamese-ViVoice](https://huggingface.co/hynt/F5-TTS-Vietnamese-ViVoice) ghi rõ chỉ dùng nghiên cứu và yêu cầu email tổ chức để xin truy cập; checkpoint 5,39 GB. Không tạo mẫu khi chưa được cấp quyền.
- [VietTTS](https://github.com/dangvansam/viet-tts) có preset Việt và model CC BY-NC; riêng các trọng số công bố khoảng 2,31 GB. Đã kiểm tra mã và phụ thuộc: engine nạp đồng thời các khối mô hình vào GPU khi thấy CUDA, trong khi card hiện có 4 GB. Chưa tải và chạy trọn mô hình này, nên không khẳng định nó không thể hoạt động. Các giọng mẫu của nó gồm tên người nổi tiếng; cần kiểm tra quyền sử dụng giọng trước khi đưa vào sản phẩm.
- [KhanhTTS-OmniVoice](https://huggingface.co/kjanh/KhanhTTS-OmniVoice) hỗ trợ tạo giọng từ clip tham chiếu hoặc mô tả, nhưng model khoảng 3,26 GB và chưa được thử trong bộ mẫu này. Khi có giọng tham chiếu được phép sử dụng, đây là hướng đáng kiểm tra sau vòng chọn preset.

Không dùng dịch vụ API trả phí. Phạm vi dự kiến là thử nghiệm nội bộ, không thương mại. Nguồn chính thức: [VieNeu](https://github.com/pnnbao97/VieNeu-TTS), [ZeroTTS](https://github.com/zeroweight-ai/ZeroTTS), [Piper voices](https://huggingface.co/rhasspy/piper-voices). Mã và trọng số của VieNeu công bố Apache 2.0; ZeroTTS công bố MIT; kho Piper voices ghi MIT. Nếu định phát hành video rộng rãi hoặc kiếm tiền, cần kiểm tra lại giấy phép và nguồn từng giọng đã chọn.

## Trạng thái job

`pilot.py status thu-5p-h007g` hiện báo `Protected implementation changed. Production blocked; review changes in development mode and create a new job.` Vì vậy bộ mẫu chưa được lắp vào job này. Sau khi chọn giọng, cần giải quyết trạng thái job theo workflow v3 trước khi sản xuất media/video mới.
