---
name: vp-horror
description: Tạo hoặc tiếp tục video kể truyện kinh dị / truyện ma tiếng Việt dài 10–30 phút từ kho hạt giống horror của Video Pilot; dùng khi người dùng muốn làm video truyện ma, truyện kinh dị, truyện rùng rợn.
---

# Điều phối video truyện kinh dị

Lệnh tính từ `sys/`. Đọc `AGENTS.md`, `docs/workflow.md` và `docs/horror.md`. Một video kể đúng một hạt giống trong `horror/seeds.json`; giữ chỗ và đánh dấu qua `horror/bank.py`, không viết brief hay ledger bằng tay.

## Hỏi trước, không tự chọn

Bốn lựa chọn không có mặc định: tỷ lệ khung (16:9 hay 9:16), thời lượng (10-15, 15-20, 20-30 phút), truyện (mã hạt giống hoặc auto) và chế độ (review hay auto). Chỉ điền cờ cho lựa chọn người dùng đã nói rõ trong cuộc trò chuyện.

1. Chạy `python3 horror/bank.py start JOB --no-input` kèm các cờ đã biết (`--ratio`, `--length`, `--seed`, `--mode`).
2. Nếu kết quả có `needs_input` (mã thoát 3): hỏi người dùng đúng các câu trong đó, đưa đúng các lựa chọn được trả về (dùng công cụ hỏi lựa chọn nếu có). Không đoán, không lấy lựa chọn đầu tiên, không nhớ từ job trước.
3. Chạy lại lệnh trong `hint` với câu trả lời thật. `start` tự tạo job với đúng chế độ đã chọn.

Muốn xem kho trước: `python3 horror/bank.py next`, `python3 horror/bank.py show --seed H00x`.

Khi tiếp tục job, không start/draw lại. Chạy `python3 pilot.py status JOB` và `python3 pilot.py next JOB`.

## Thứ tự

1. Đọc `vp-content/SKILL.md`; chạy `python3 pilot.py run JOB content`. Người dẫn chuyện (mascot) chỉ ở cảnh đầu và cảnh cuối; nhân vật truyện là người riêng của truyện. Chốt lời dẫn trước coverage/anchor. Cổng `horror.policy:lint` chặn lời khẳng định có thật, hướng dẫn nghi lễ, máu me/tự hại và địa danh thật; sửa lời dẫn, không sửa danh sách chặn để qua cổng.
2. Sau quyết định content hợp lệ, đọc `vp-media/SKILL.md`; chạy `python3 pilot.py run JOB media`. Giọng mặc định Phạm Tuyên, chạy GPU khi có.
3. Sau quyết định media hợp lệ, đọc `vp-video/SKILL.md`; chạy `python3 pilot.py run JOB video`.
4. Khi video đã có quyết định hợp lệ và xuất thành công, chạy `python3 horror/bank.py mark JOB`. Trả đường dẫn MP4 thật trong `video/<job>/`.

Review dừng đúng ba điểm content/media/video. Auto dùng báo cáo xem/nghe artifact thật; unsupported hoặc lỗi đăng nhập/CAPTCHA/hạn mức thì dừng. Job bị huỷ trước khi xong: `python3 horror/bank.py release JOB` để trả truyện về kho.
