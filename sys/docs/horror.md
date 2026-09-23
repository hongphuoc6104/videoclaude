# Kênh truyện kinh dị

Video kể truyện ma / kinh dị tiếng Việt dài 10–30 phút (có mức thử 4–6 phút, 10 cảnh). Mỗi video kể một **hạt giống** trong `horror/seeds.json`: mô-típ có nguồn gốc rõ ràng, không phải lời kể. Lời kể, tên người và bối cảnh luôn viết mới và hư cấu. Lời dẫn không nói "đây là truyện hư cấu"; câu đó thuộc mô tả video khi đăng (chưa có bước tự sinh mô tả). Lời dẫn vẫn không bao giờ khẳng định hay gợi ý truyện có thật.

## Bắt đầu một video

```bash
cd sys
python3 horror/bank.py start truyen-001
```

Không có lựa chọn mặc định. Lệnh hỏi sáu câu nếu chưa có cờ tương ứng:

| Câu hỏi | Cờ | Lựa chọn |
|---|---|---|
| Khung ngang hay dọc | `--ratio` | `16:9`, `9:16` |
| Dài bao lâu | `--length` | `10-15` (20 cảnh), `15-20` (28 cảnh), `20-30` (40 cảnh) |
| Kể truyện nào | `--seed` | mã `H001`… hoặc `auto` (truyện kế tiếp còn trống) |
| Không khí | `--mood` | `seed` (theo gợi ý của truyện), `slow_burn` (rợn chậm), `psychological` (ám ảnh tâm lý), `folk` (dân gian u uất), `tense` (căng thẳng dồn dập) |
| Ai kể | `--pov` | `third` (ngôi thứ ba), `first` (nhân vật chính xưng "tôi") |
| Chế độ duyệt | `--mode` | `review`, `auto` |

Trong terminal, lệnh hỏi từng câu. Khi agent chạy (không có terminal) hoặc có `--no-input`, lệnh trả `needs_input` kèm câu hỏi và lựa chọn, thoát mã 3, không giữ chỗ gì; agent hỏi người dùng rồi chạy lại với đủ cờ. Danh sách câu hỏi và lựa chọn nằm trong `horror/channel.json` (`options`).

Khung 16:9 đọc tiếng Việt (`audio_language: "vi"` trong brief); không cần lời dẫn tiếng Anh.

## Giọng kể, không khí và văn phong

- **Giọng chung của kênh** (`channel.json` → `tone`, `pacing`): trầm, chậm, gần gũi như kể bên ánh đèn; mở nhanh bằng câu móc, giữa truyện chậm lại, cao trào ngắn.
- **Không khí** (`channel.json` → `moods`): mỗi kiểu thêm giọng, nhịp riêng vào brief. Mỗi hạt giống có `mood` gợi ý; chọn `--mood seed` để dùng gợi ý đó.
- **Ngôi kể** (`--pov`): ghi vào brief thành yêu cầu "Ngôi kể: …".
- **Văn phong kịch bản** (`horror/narration-style.md`, tiếng Anh vì là chỉ dẫn nội bộ): cách dựng nỗi sợ bằng chi tiết sai lệch nhỏ, leo thang điềm lạ, gieo chi tiết rồi trả ở cú lật, nhịp câu hợp giọng đọc máy, giới hạn sáo ngữ, cấu trúc theo tỷ lệ cảnh (mở 1 cảnh, dựng ~20%, leo thang ~45%, cao trào ~20%, dư âm ~10%, khép 1 cảnh) và cách tả hình. File này được nạp vào lời gọi viết kịch bản qua `config.json` → `narration_styles.horror_story`, sau hướng dẫn lời dẫn chung.

## Đạo diễn giọng kể

Giọng máy đọc mọi câu cùng tốc độ, cùng độ to, cùng khoảng nghỉ, nên cao trào nghe y như đoạn mở đầu. Đo trên job `thu-5p-h007g`: tốc độ giữa 10 cảnh chỉ lệch ±5%, độ to lệch 0,8 dB. Bước giọng đọc vì vậy có thêm phần đạo diễn (`scripts/delivery.py`). Phần này chỉ đổi tốc độ, độ to và khoảng lặng; không đổi chữ và vẫn giữ giọng Phạm Tuyên.

- **Hồ sơ đạo diễn** ở `channel.json` → `delivery`. Khi mở job, `bank.py start` chép hồ sơ này vào brief (`brief.delivery`, kèm không khí đã chọn). Sửa `channel.json` chỉ có tác dụng với job mở sau đó.
- **Kiểu đọc từng cảnh** lấy theo mã ý của cảnh:

  | Mã ý | Kiểu đọc | Cách đọc |
  |---|---|---|
  | R1 | mở đầu (người dẫn) | chậm |
  | R2 | dựng truyện | chậm nhất |
  | R3 | leo thang | chậm, nhiều khoảng lặng |
  | R4 | cao trào | nhanh nhất, nghỉ ngắn |
  | R5 | dư âm | chậm, nặng |
  | R6 | khép lại (người dẫn) | chậm |

  Cảnh gắn nhiều mã ý thì lấy kiểu mạnh nhất (thứ tự trong `priority`). Không khí truyện nhân thêm hệ số: `tense` nhanh hơn và nghỉ ít hơn; `slow_burn` và `folk` chậm hơn, nghỉ dài hơn.
- **Chỉnh từng câu** theo dấu hiệu trong chữ:
  - Thoại trong ngoặc kép được tách thành câu riêng, có khoảng lặng trước và sau, đọc nhỏ hơn 4 dB. Thoại kết bằng "!" giữ gần nguyên độ to.
  - Câu kết bằng "…" nghỉ khoảng 1,2 giây.
  - Câu hỏi nghỉ 1 giây.
  - Câu từ 8 tiếng trở xuống trong cảnh căng có khoảng lặng hai bên.
  - Câu cuối của cảnh căng được đọc sau một khoảng lặng, nhỏ hơn 6 dB và chậm hơn.
- **Màu giọng** (`delivery.fx`): ấm phần trầm, bớt chói phần cao, thêm chút vang phòng nhỏ. Hiệu ứng này áp lúc hoàn thiện lời dẫn và không làm đổi độ dài file.
- **Nhạc nền**: mỗi đoạn lời dẫn ghi `speech_end` (chỗ giọng dừng). Nhờ đó nền chỉ nhỏ xuống khi đang có tiếng nói và lớn dần lên trong các khoảng lặng. Tiếng động và nhịp hình cũng neo theo phần có tiếng nói.
- **Thời lượng**: đọc có đạo diễn dài hơn, 1169 chữ mất 347 giây thay vì 299 giây. Brief kinh dị vì thế dùng tốc độ đã đo là 3,3 chữ/giây (đã tính khoảng lặng) để đặt số chữ mỗi cảnh.
- Brief không có `delivery` (job cũ, video không phải kinh dị) vẫn đọc như trước, và bộ đệm giọng cũ vẫn dùng lại được.

## Kịch bản dài (viết theo từng đoạn)

Một lần gọi agy chỉ có tối đa 180 giây, không đủ viết 20–40 cảnh. Khi brief có nhiều cảnh hơn `config.json` → `content_chunk_scenes` (mặc định 6), `pilot.py run JOB content` tự làm theo `scripts/long_script.py`:

1. **Lượt lập kế hoạch:** dàn ý đủ mọi cảnh (mục đích cụ thể, mã ý, chuyển cảnh) và danh sách nhân vật dùng chung.
2. **Các lượt viết cảnh:** mỗi lượt viết 6 cảnh. Mỗi lượt nhận dàn ý, danh sách nhân vật, tóm tắt các đoạn trước (`story_so_far`), lời dẫn hai cảnh liền trước, và số chữ cần viết mỗi cảnh (tính từ thời lượng và tốc độ đọc trong brief).
3. **Kiểm tra từng đoạn ngay khi nhận:** đúng mã cảnh, đúng dàn ý, không thêm nhân vật, điểm neo hợp lệ, đủ câu trích cho ý bắt buộc, mã ảnh/nhịp không trùng, lời dẫn không quá ngắn (dưới 60% mục tiêu thì dừng). Đoạn hỏng thì dừng ngay, không gọi tiếp.
4. **Ghép và kiểm tra** như bản viết một lần, rồi mới tới duyệt.

Không tự thử lại. Nếu một lượt hết giờ hoặc bị chặn, chạy lại `pilot.py run JOB content`: các lượt đã xong của lần trước (cùng brief, cùng phản hồi, cùng prompt) được dùng lại, chỉ gọi phần còn thiếu. Bằng chứng từng lượt nằm trong `agent-attempts/<lần chạy>/long-script.json`.

## Nhạc nền và tiếng động (chỉ CC0)

- Thư viện `assets/audio/library.json` chỉ nhận mục có `license: "CC0-1.0"`; `sound.py` từ chối mọi giấy phép khác.
- Có sẵn 3 nền (`drone`, `wind`, `pulse`) và 5 tiếng động (`low_hit`, `heartbeat`, `knock`, `gust`, `creak`). Tất cả **tạo bằng code** trong `sound.py` từ công thức và seed cố định, không tải gì từ mạng. Dự án phát hành chúng theo CC0-1.0.
- Muốn thêm file CC0 thật (ví dụ tiếng mưa): đặt WAV 16-bit vào `assets/audio/cc0/`, thêm mục `source: "file"` kèm `author`, `source_url`, `sha256`. Thiếu một trường là bị từ chối.
- Brief truyện kinh dị có `sound: {bed, sfx}`. Nền theo không khí đã chọn (`channel.json` → `moods.*.music`). Người viết kịch bản được phép gắn tối đa một tiếng động mỗi cảnh, chỉ ở chỗ lời dẫn tả đúng âm thanh đó, và neo vào nguyên văn như nhịp hình.
- Trộn ở bước video (`adapters.render` → `sound.build`): nền lặp suốt video, tự nhỏ xuống khi có lời đọc (nền nhỏ hơn giọng khoảng 25 dB khi đang đọc, khoảng 16 dB lúc nghỉ; đo trên bản render thử), vào và ra từ từ; tiếng động đặt đúng câu được neo. File lời dẫn đã duyệt giữ nguyên; video dùng `mix.wav`. Mỗi lần render ghi `sound.json` liệt kê mọi âm thanh đã dùng kèm giấy phép và nguồn.
- Nghe thử một âm thanh: `python3 sound.py preview drone /tmp/drone.wav`. Kiểm tra thư viện: `python3 sound.py check`.

## Lệnh khác

```bash
python3 horror/bank.py status            # số truyện todo/reserved/done
python3 horror/bank.py next              # truyện còn trống
python3 horror/bank.py show --seed H004  # xem một hạt giống
python3 horror/bank.py mark JOB          # sau khi video được duyệt và xuất
python3 horror/bank.py release JOB       # trả truyện về kho khi huỷ job
```

## Thêm hạt giống

Thêm mục vào `horror/seeds.json` với id kế tiếp (không đổi id cũ). Bắt buộc: `title`, `subgenre`, `setting` (tả chung, không địa danh thật), `premise`, ít nhất ba `dread`, `twist`, `basis`.

`basis.type`:
- `public_domain`: tác phẩm đã hết bảo hộ; ghi `work`, `author`, `year`. Chỉ mượn mô-típ; không dùng bản dịch hiện đại (bản dịch có thể còn bản quyền).
- `folklore`: mô-típ dân gian; không mô tả nghi lễ hay hướng dẫn tín ngưỡng.
- `original`: tự viết.

## An toàn nội dung

- Brief: cổng `horror.policy:check` chặn brief truyện kinh dị viết tay hoặc dùng hạt giống không giữ chỗ cho job.
- Nội dung: cổng `horror.policy:lint` (cấu hình `content_policies`) chặn lời dẫn/hình có câu khẳng định chuyện có thật, hướng dẫn nghi lễ hay rủ làm theo, máu me/tự hại, và địa danh thật. Câu bị phủ định ngay trước ("không phải chuyện có thật", "không máu me") được bỏ qua. Danh sách từ ở `horror/channel.json` → `blocked_terms`.
- Đây chỉ là lưới an toàn thô; người duyệt vẫn đọc toàn bộ kịch bản. Kênh không dành cho trẻ em: khi đăng YouTube chọn "Không, nội dung này không dành cho trẻ em".

## Người dẫn chuyện

Nhân vật đại diện kênh (người que áo xanh #8CCFE8) chỉ xuất hiện ở cảnh mở đầu và cảnh kết, như người kể chuyện. Các cảnh trong truyện dùng nhân vật riêng của truyện.

Cách bước tạo ảnh chọn ảnh tham chiếu (`image_pipeline.py`, `adapters.py`, `b2_bridge.py`, `queue-runner.mjs`):

| Ai trong hình | Ảnh tham chiếu gửi Flow | Ghi chú |
|---|---|---|
| Người dẫn chuyện (nhân vật có id trùng `config.json` → `canonical_character.id`) | Ảnh mascot cố định và media id của nó | Chỉ lúc này mới thêm mô tả giải phẫu người que vào prompt |
| Nhân vật truyện | Ảnh tham chiếu riêng Flow đã vẽ ở bước `references` | "Đăng ký" chỉ giữ ảnh đó và media id, không tạo ảnh mới |
| Không có ai (cảnh vắng, đồ vật) | Không có | Tạo ảnh chỉ từ chữ (`--no-character` / `noCharacter`) |

Không còn đường lui về mascot: thiếu ảnh hoặc media id của nhân vật thì dừng với `CHARACTER_REFERENCE_UNRESOLVED`. Công cụ trên Flow chỉ có một ô nhân vật, nên cảnh có hai người thì gắn ảnh người đầu tiên trong `character_ids`; người thứ hai vẽ theo mô tả ngoại hình trong prompt. Hãy đặt nhân vật chính lên đầu danh sách.
