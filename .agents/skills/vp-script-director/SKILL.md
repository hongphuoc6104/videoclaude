---
name: vp-script-director
description: Check the opening chunk and critique a complete Vietnamese horror narration draft before content submission; use for horror_story briefs with script_director enabled.
---

# Horror script director

The writer owns the draft. Score the entire spoken Vietnamese story after structural validation. Preserve quoted Vietnamese evidence exactly. This critique is internal; it never approves content or changes its words, outline, coverage, claims, images, or anchors. A failed draft returns to the writer for a complete regeneration: finalize narration first, then place fresh quotes and anchors. The existing content review gate still applies.

## Cổng dàn ý truyện dài

Với brief `horror_story` có bật `script_director`, `scripts/long_script.py` kiểm tra dàn ý đầy đủ **trước khi viết bất kỳ cặp cảnh nào**. Đây là một bước nội bộ, không thêm cổng duyệt công khai. Bộ phê bình đọc tất cả `purpose`, các điểm bắt buộc trong brief và văn phong truyện; chấm năm điều: câu móc không tiết lộ cú lật, khoảng nhẹ nhõm giả thực sự ở giữa truyện, trình tự cú lật và chi tiết gieo–trả theo hạt giống, nhân quả/ngôi kể/khẳng định có cơ sở, lời khép của người dẫn không rủ người xem thử làm theo.

Mỗi điều cần mã cảnh và câu trích **nguyên văn từ `purpose`**. Mã Python kiểm tra câu trích thuộc đúng cảnh, tính kết quả từ từng mục thay vì tin cờ `pass` của bộ phê bình. Mục chưa đạt phải có yêu cầu sửa cụ thể cho cảnh liên quan. Người viết được lập lại **toàn bộ dàn ý tối đa hai lần**, giữ số cảnh, mã ý bắt buộc và danh sách nhân vật nhất quán. Mỗi dàn ý và nhận xét được lưu trong `agent-attempts/<attempt>/outline-*-round-*.json`. Hết lượt vẫn chưa đạt thì dừng với `OUTLINE_DIRECTOR_NEEDS_ATTENTION`; không viết cảnh, không đưa dàn ý lỗi sang bước duyệt content. Dàn ý tái sử dụng từ lượt bị chặn cũng phải qua cổng này trước khi viết tiếp.

## Cổng cặp cảnh chi tiết đầu tiên

Với truyện dài đã qua cổng dàn ý, kiểm tra nghĩa **chỉ cặp cảnh đầu** sau kiểm tra cấu trúc, trước khi lưu cặp đó và viết cặp tiếp theo. Agy xét lời mở có hé nguồn/cách giải điềm lạ ở cao trào không; mô tả hình có giữ mascot chuẩn và trang phục đã khai không; ảnh `based_on` có liên tục vật thể, vị trí và bối cảnh không; mục đích từng nhịp có khớp ảnh tham chiếu không. Tên truyện và brief có thể chứa cú lật nhưng chỉ là dữ liệu nội bộ, không được tự đưa lời giải vào lời mở. Không bắt mọi chữ trong lời dẫn phải hiện trên ảnh; chỉ bắt đồ vật/hành động nổi bật mà nhịp hứa sẽ cho xem.

Mỗi kết luận cần câu trích **nguyên văn từ đúng trường nguồn** và mã cảnh/ảnh/nhịp. Lỗi lời mở phải đối chiếu lời dẫn cảnh đầu với ý bắt buộc hoặc `purpose` của cảnh lật ở sau; lỗi nhân vật phải đối chiếu hình với hồ sơ nhân vật hoặc mascot chuẩn; lỗi ảnh biến thể phải trích cả ảnh gốc lẫn ảnh biến thể; lỗi nhịp phải trích mục đích nhịp và mô tả của ảnh đúng mã. Mã Python xác thực câu trích, tính kết quả từ từng tiêu chí thay vì tin cờ `pass`. Nếu trượt, người viết chỉ viết lại cặp đầu tối đa hai lần theo ghi chú cụ thể: chốt lời dẫn mới rồi đặt lại coverage, claims và mọi neo theo câu chữ cuối. Không sửa tay các trường của bản đã neo. Hết lượt dừng `OPENING_CHUNK_DIRECTOR_NEEDS_ATTENTION` trước cảnh tiếp theo. Không thêm lượt phê bình này cho các cặp sau, không tạo cổng duyệt mới.

Use `horror/narration-style.md` and the brief's mood and point of view. Give each criterion an integer score from 0 to 2, at least one scene-specific quote as evidence, and concrete notes:

| Criterion | 0 | 1 | 2 |
| --- | --- | --- | --- |
| `dread_escalation` | No rising omen, or a monster is fully exposed at once | Omens rise unevenly or false relief is missing | Each omen is closer, more personal, or harder to explain; one midstory false relief |
| `pacing_rhythm` | Flat, uniformly long sentences around scares | Slows before a scare, but the scare line stays buried | Two or three short ordinary sentences precede a separate 3–8 word scare line |
| `climax_payoff` | Twist is unrelated to planted detail | The detail returns weakly or too early | An ordinary early detail returns and changes meaning at the twist |
| `oral_storytelling_voice` | Literary prose or many tangled clauses | Mostly speakable with a few bookish lines | Natural spoken Vietnamese, mostly 6–20 words per sentence, at most two ellipses per scene |
| `cliche_budget` | A listed cliché repeats at least twice | No listed phrase repeats, but clichés crowd the narration | At or under the per-phrase budget in the style guide, with specific physical detail instead |
| `hook_per_scene` | Two or more nonfinal scenes end without a hook | One nonfinal scene lacks a hook | Every nonfinal scene ends on a question, unexplained detail, or interrupted action |

The code computes pass: every criterion at least 1 and total at least 10 of 12. Supply `revision_requests` for weak spots with criterion, affected scene IDs, and a specific rewrite instruction. The adapter assigns each request an `SD…` ID, sends it to the writer, and requires a matching `revision_response` with the scene IDs. An unresolved request reaches `open_questions` in review mode and stops auto mode. Never claim the draft passes in prose. The adapter allows at most two complete writer rewrites; in auto mode exhaustion stops with `needs_attention`, while review mode shows the findings in `open_questions` for the human review. Every round's scored evidence and writer response are saved under the job's `agent-attempts` directory.
