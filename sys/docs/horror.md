# Kênh truyện kinh dị

Video kể truyện ma / kinh dị tiếng Việt dài 10–30 phút. Mỗi video kể một **hạt giống** trong `horror/seeds.json`: mô-típ có nguồn gốc rõ ràng, không phải lời kể. Lời kể, tên người và bối cảnh luôn viết mới và hư cấu.

## Bắt đầu một video

```bash
cd sys
python3 horror/bank.py start truyen-001
```

Không có lựa chọn mặc định. Lệnh hỏi bốn câu nếu chưa có cờ tương ứng:

| Câu hỏi | Cờ | Lựa chọn |
|---|---|---|
| Khung ngang hay dọc | `--ratio` | `16:9`, `9:16` |
| Dài bao lâu | `--length` | `10-15` (20 cảnh), `15-20` (28 cảnh), `20-30` (40 cảnh) |
| Kể truyện nào | `--seed` | mã `H001`… hoặc `auto` (truyện kế tiếp còn trống) |
| Chế độ duyệt | `--mode` | `review`, `auto` |

Trong terminal, lệnh hỏi từng câu. Khi agent chạy (không có terminal) hoặc có `--no-input`, lệnh trả `needs_input` kèm câu hỏi và lựa chọn, thoát mã 3, không giữ chỗ gì; agent hỏi người dùng rồi chạy lại với đủ cờ. Danh sách câu hỏi và lựa chọn nằm trong `horror/channel.json` (`options`).

Khung 16:9 đọc tiếng Việt (`audio_language: "vi"` trong brief); không cần lời dẫn tiếng Anh.

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

**Chưa xong:** bước tạo ảnh hiện vẫn gắn ảnh tham chiếu mascot cho mọi ảnh (`adapters.py`, lệnh `image` và `batch`), nên nhân vật truyện sẽ bị vẽ thành người que. Cần sửa để mỗi nhân vật truyện có ảnh tham chiếu riêng và thử trên Flow thật trước khi sản xuất.
