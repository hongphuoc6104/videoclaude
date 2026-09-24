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

## Đạo diễn kịch bản

`horror/channel.json` → `script_director` được chép vào brief khi tạo job mới. Với truyện kinh dị có bật cấu hình này, bản kịch bản đầy đủ được kiểm tra cấu trúc rồi gửi cho agy chấm độc lập theo sáu tiêu chí trong `.agents/skills/vp-script-director/SKILL.md`: leo thang nỗi sợ, nhịp câu, cao trào và chi tiết được trả, giọng kể miệng, sáo ngữ, móc cuối cảnh. Mỗi tiêu chí đạt ít nhất 1/2 và tổng đạt ít nhất 10/12; mã Python tính kết quả từ điểm và bằng chứng do agy trả về.

Với truyện dài viết theo cặp cảnh, còn có **cổng dàn ý trước khi viết cảnh**. Agy đọc cả dàn ý và các điểm bắt buộc, rồi nhận xét năm điều: mở không tiết lộ cú lật, khoảng nhẹ nhõm giả có đủ nhịp ở giữa truyện, cú lật và chi tiết gieo–trả đúng hạt giống, nhân quả/ngôi kể/khẳng định có cơ sở, cảnh khép không rủ người xem làm theo. Mỗi nhận xét phải chỉ đúng mã cảnh và trích nguyên văn từ `purpose`; mã Python tính đạt/trượt, không tin cờ `pass` do agy trả về. Nếu trượt, người viết được lập lại toàn bộ dàn ý tối đa hai lượt theo yêu cầu sửa cụ thể, giữ nguyên số cảnh, mã ý bắt buộc và nhân vật. Hết lượt thì dừng `OUTLINE_DIRECTOR_NEEDS_ATTENTION` **trước khi viết cảnh đầu tiên** ở cả hai chế độ duyệt. Dàn ý và nhận xét từng lượt ở `agent-attempts/<attempt>/outline-*-round-*.json`. Dàn ý tái sử dụng từ lượt bị chặn vẫn phải qua cổng này; brief không bật `script_director` và loại video khác giữ đường đi cũ.

Nếu chưa đạt, người viết nhận nhận xét cụ thể và tạo lại toàn bộ bản nháp, tối đa hai lần. Lời dẫn mới được chốt trước khi người viết đặt lại coverage, claims và anchor; đạo diễn không sửa trực tiếp lời dẫn đã neo. Mỗi vòng lưu điểm, dẫn chứng và bản người viết tại `runs/<job>/agent-attempts/<attempt>/`. Hết hai lượt mà vẫn chưa đạt: chế độ `auto` dừng với `needs_attention`; chế độ `review` đưa nhận xét vào `open_questions` để người dùng xem ở cổng duyệt content. Brief không có `script_director` tiếp tục quy trình cũ.

Với kịch bản dài có bật `script_director`, **cặp cảnh chi tiết đầu tiên** còn được rà nghĩa ngay sau kiểm tra cấu trúc và trước khi viết cặp tiếp theo. Bốn tiêu chí là: lời mở không nói trước nguồn/cách giải của điềm lạ; hình giữ đúng mascot chuẩn và trang phục nhân vật đã khai; ảnh biến thể `based_on` giữ liên tục vật thể, vị trí và bối cảnh; mục đích nhịp hình khớp ảnh được chỉ đến. Agy phải trích chính xác lời dẫn, dàn ý/ý bắt buộc và các trường hình/nhịp liên quan; mã tính đạt từ từng tiêu chí thay vì tin cờ `pass`. Nếu trượt, chỉ cặp cảnh đầu được viết lại tối đa hai lần với ghi chú cụ thể; lời dẫn được chốt rồi mới đặt lại coverage, claims và neo. Hết lượt thì dừng `OPENING_CHUNK_DIRECTOR_NEEDS_ATTENTION` trước cặp tiếp theo. Bản đầu chỉ được dùng lại khi có kết quả đạt gắn hash của brief, dàn ý, cặp cảnh và phiên bản kiểm tra; bản cũ thiếu kết quả phải được rà lại. Nếu cặp đầu thay đổi, các cặp đã lưu phía sau phải viết lại vì tóm tắt và lời dẫn tiếp nối đã đổi. Bản ứng viên và nhận xét mỗi lượt nằm trong `agent-attempts/<attempt>/opening-chunk-*.json`. Đây là kiểm tra nội bộ, không thêm cổng duyệt công khai; các cặp sau không chịu kiểm tra này.

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
  - Thoại trong ngoặc kép được tách thành câu riêng, có khoảng lặng trước và sau.
  - Câu kết bằng "…" nghỉ khoảng 1,2 giây.
  - Câu hỏi nghỉ 1 giây.
  - Câu từ 8 tiếng trở xuống trong cảnh căng có khoảng lặng hai bên.
  - Câu cuối của cảnh căng được đọc sau một khoảng lặng và chậm hơn.
  - Độ to mọi câu giữ bằng nhau (`gain_db` = 0). Bản thử ngày 2026-09-23 đọc thoại nhỏ hơn 4 dB và câu khép cảnh nhỏ hơn 6 dB. Người nghe thấy như âm lượng tự tụt, vì giọng máy không đổi chất giọng khi nói nhỏ. Chỉ bật lại khi có giọng thì thầm thật.
- **Màu giọng** (`delivery.fx`): ấm phần trầm, bớt chói phần cao, thêm chút vang phòng nhỏ. Hiệu ứng này áp lúc hoàn thiện lời dẫn và không làm đổi độ dài file.
- **Tinh chỉnh theo nghĩa câu** (`delivery.voice_director`): agy đọc lời dẫn đã chốt rồi đề xuất tốc độ và khoảng nghỉ cho từng câu trên nền `scripts/delivery.py`. Chữ phải giữ nguyên; tốc độ trong khoảng 0,8–1,1 và lệch tối đa 15% so với nền, khoảng nghỉ 0–2 giây, độ to vẫn bằng 0 dB. Đầu ra sai được thử lại một lần; vẫn sai thì dùng kế hoạch quy tắc của nhóm cảnh đó và ghi rõ trong `voice-direction.json`. Duyệt media vẫn dựa vào WAV thật, không dựa vào nhãn chỉ dẫn.
- **Nhạc nền**: mỗi đoạn lời dẫn ghi `speech_end` (chỗ giọng dừng). Nhờ đó nền chỉ nhỏ xuống khi đang có tiếng nói và lớn dần lên trong các khoảng lặng. Tiếng động và nhịp hình cũng neo theo phần có tiếng nói.
- **Thời lượng**: đọc có đạo diễn dài hơn, 1169 chữ mất 347 giây thay vì 299 giây. Brief kinh dị vì thế dùng tốc độ đã đo là 3,3 chữ/giây (đã tính khoảng lặng) để đặt số chữ mỗi cảnh.
- Brief không có `delivery` (job cũ, video không phải kinh dị) vẫn đọc như trước, và bộ đệm giọng cũ vẫn dùng lại được.

## Mật độ hình

- Đo trên thu-5p-h007g: trung bình khoảng 14 giây mới có một ảnh mới, có chỗ tới 25 giây, và mỗi cảnh luôn chỉ có 2 ảnh dù cảnh dài bao nhiêu.
- `horror/channel.json` → `visual_density`, được chép vào brief (`planning.visual_density`), đặt mục tiêu: khoảng 10 giây một ảnh khác nhau và 6 giây một nhịp hình. Biến thể `based_on` (góc khác, cận hơn, cùng chỗ một lúc sau) được tính là ảnh mới.
- Khi viết chi tiết, agy được báo mỗi cảnh cần bao nhiêu chữ cho một ảnh và một nhịp.
- `story_plan.validate_plan` chặn cảnh nào chậm hơn 1,3 lần mục tiêu (lỗi `IMAGE_DENSITY` hoặc `BEAT_DENSITY`). Độ dài cảnh được ước tính theo tốc độ đọc trong brief.
- Truyện 5 phút cần khoảng 35–40 ảnh thay vì 22, nên phải gửi Flow nhiều đợt hơn.

## Kịch bản dài (viết theo từng đoạn)

Một lần thử H001 viết 6 cảnh đã chạm giới hạn CLI 180 giây trước khi trả `structured_output`; log ghi khoảng 27.493 token đầu vào, 43.452 token suy luận và phần lời đáp đã nhìn thấy tới cảnh thứ hai. Vì thế lượt viết chi tiết truyện kinh dị hiện chia tối đa 2 cảnh (`config.json` → `content_chunk_scenes_by_video_type.horror_story`) và cho phép tối đa 300 giây; lượt dàn ý vẫn dùng 180 giây. Đây là giới hạn vận hành, chưa phải bảo đảm lượt viết thật sẽ đạt. `pilot.py run JOB content` tự làm theo `scripts/long_script.py`:

1. **Lượt lập kế hoạch:** dàn ý đủ mọi cảnh (mục đích cụ thể, mã ý, chuyển cảnh) và danh sách nhân vật dùng chung. Với truyện có `script_director`, cổng dàn ý ở trên chạy ngay sau kiểm tra cấu trúc.
2. **Các lượt viết cảnh:** mỗi lượt viết tối đa 2 cảnh. Mỗi lượt nhận dàn ý, danh sách nhân vật, tóm tắt các đoạn trước (`story_so_far`), lời dẫn hai cảnh liền trước, và số chữ cần viết mỗi cảnh (tính từ thời lượng và tốc độ đọc trong brief).
3. **Kiểm tra từng đoạn ngay khi nhận:** đúng mã cảnh, đúng dàn ý, không thêm nhân vật, điểm neo hợp lệ, đủ câu trích cho ý bắt buộc, mã ảnh/nhịp không trùng, lời dẫn không quá ngắn (dưới 60% mục tiêu thì dừng). Đoạn hỏng thì dừng ngay, không gọi tiếp.
4. **Ghép và kiểm tra** như bản viết một lần, rồi mới tới duyệt.

Ngoại trừ tối đa hai lần lập lại dàn ý sau nhận xét của đạo diễn, đoạn cảnh lỗi không được tự thử lại trong cùng lượt. Nếu một lượt hết giờ hoặc bị chặn, cần xem nguyên nhân trước khi quyết định chạy lại `pilot.py run JOB content`: các lượt đã xong của lần trước (cùng brief, cùng phản hồi, cùng prompt) được dùng lại khi dàn ý đã đạt và mã băm còn khớp. Thông tin chẩn đoán CLI được lưu an toàn ở `agent-attempts/<lần chạy>/agy-diagnostic-*.json`; trạng thái các đoạn đã hoàn tất ở `long-script.json`. Không lấy phản hồi chưa đầy đủ từ log làm kịch bản đã kiểm tra.

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
