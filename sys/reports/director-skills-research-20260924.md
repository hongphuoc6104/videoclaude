# Nghiên cứu: skill "Đạo diễn kịch bản" và "Đạo diễn giọng" cho kênh truyện kinh dị

Ngày: 2026-09-24. Phạm vi: chỉ nghiên cứu, không sửa code, không cài gì. Mục tiêu: trả lời có sẵn skill ổn định, hợp dùng trên GitHub/marketplace cho (a) đạo diễn kịch bản (phê bình + viết lại lời dẫn kinh dị để tạo sự rợn người, nhịp, leo thang, cao trào, trả treo, văn phong kể miệng) và (b) đạo diễn giọng (biến lời dẫn đã chốt thành chỉ dẫn đọc từng câu: tốc độ, khoảng nghỉ, nhấn, cảm xúc, thì thầm) mà TTS có thể thực thi hay không.

## Bối cảnh hệ thống (đọc trước khi tìm)

- `AGENTS.md`: chỉ dẫn nội bộ dùng tiếng Anh; giữ nguyên mẫu `prompt_templates.py`; lời dẫn viết xong rồi mới đặt neo/coverage, **không sửa lời dẫn sau khi đã neo**; auto mode phải có bộ đánh giá thật xem/nghe artifact, không tự tạo báo cáo pass giả.
- `sys/docs/horror.md` + `sys/horror/narration-style.md`: đã có sẵn quy tắc viết rất chi tiết cho phần "đạo diễn kịch bản" (tỷ lệ cảnh mở 1/dựng ~20%/leo thang ~45%/cao trào ~20%/dư âm ~10%/khép 1, quy tắc gieo–trả, trả treo cuối cảnh, giới hạn sáo ngữ, độ dài câu 6–20 từ...) — đây là *tiêu chuẩn viết*, chưa có bước *phê bình và chấm điểm* độc lập trước khi khoá lời dẫn.
- `sys/scripts/delivery.py` + `channel.json.delivery`: đạo diễn giọng **đã tồn tại** nhưng là rule-based thuần (regex + bảng tốc độ/khoảng nghỉ theo mã ý R1–R6, không dùng LLM). Nó chỉ đổi ba thứ: `speed` (tốc độ), `gaps`/`tail` (khoảng lặng tính bằng giây), `gain_db` (độ to, hiện luôn = 0). **Không đổi chữ.**
- `sys/tts_worker.py` + `assets/voices/pham-tuyen-gwen/voice.json`: Gwen-TTS (Qwen3-TTS 0.6B finetune, MIT) — mỗi câu chỉ nhận `speed` (per-line) và một bộ `temperature/top_k/top_p/repetition_penalty` **cấu hình toàn cục theo voice folder**, không đọc SSML, không đọc tag cảm xúc/whisper trong text, một giọng = một thư mục tham chiếu (`reference_audio` + `reference_text`) cố định. Đây là giới hạn cứng: **bất kỳ đạo diễn giọng nào cũng phải quy về (tốc độ, khoảng nghỉ, độ to) per-line**, không có kênh nào khác để "ra lệnh" cho Gwen.

Đã đọc 3 SKILL.md (`vp-content`, `vp-horror`, `vp-media`) để nắm định dạng: front-matter `name/description` ngắn, thân bài tiếng Việt, liệt kê lệnh `pilot.py`, gate và đường dẫn tương đối `sys/`.

## Phương pháp tìm kiếm

WebSearch + WebFetch (đọc trực tiếp README/SKILL.md) + xác minh sao/license/lần push cuối qua GitHub REST API (`api.github.com/repos/...`, không cần đăng nhập) cho mọi ứng viên có vẻ nghiêm túc. Đã thử: kho chính thức `anthropics/skills`, các danh sách `awesome-claude-skills`, marketplace (Smithery, mcpmarket, claude-plugins), tìm trực tiếp bằng GitHub code/repo search cho cụm "script doctor", "voice director", "story doctor" kèm "claude"/"skill"/"tts", và tìm học thuật (arXiv) cho hướng LLM sinh chỉ dẫn prosody.

## (a) Ứng viên cho "Đạo diễn kịch bản"

| Repo | Sao | License | Push cuối | Có gì | Vì sao không dùng thẳng |
|---|---|---|---|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | kho chính thức | MIT-family | đang duy trì | 17 skill (docx/pdf/pptx/xlsx, skill-creator, thiết kế, giao tiếp...) | Không có skill nào cho hư cấu/kịch bản/phê bình truyện. Không liên quan. |
| [jtydhr88/screenwriting-skills](https://github.com/jtydhr88/screenwriting-skills) | 1367 | MIT | 2026-09-22 | 26 skill kịch bản/truyền hình/kịch nghệ, đúc từ 47 sách nghề + 23 kịch bản đã xuất bản; có "genre anatomy" cho 12 thể loại | Chín, còn hoạt động, nhưng **không có skill riêng cho horror/dread**, viết cho kịch bản phim/TV (hình ảnh, đối thoại nhiều nhân vật), không phải lời kể một giọng cho TTS; không có rubric pass/fail máy chấm được; tiếng Việt không phải mục tiêu. |
| [danjdewhurst/story-skills](https://github.com/danjdewhurst/story-skills) | 241 | MIT | 2026-09-22 | 14 skill (story-init, plot-structure, scene-craft, voice-style, feedback-triage, continuity-engine bắt lỗi mâu thuẫn kiểu "compiler")... | Hạ tầng tốt (CLI, eval harness) nhưng nhắm tiểu thuyết dài nhiều chương bằng Markdown, không có skill chấm riêng "dread/pacing/escalation/payoff" theo tỷ lệ cảnh, không có ngưỡng số hoá auto-mode. |
| [haowjy/creative-writing-skills](https://github.com/haowjy/creative-writing-skills) | 482 | Apache-2.0 | 2026-09-23 | Kiến trúc "muse" điều phối 10 agent: writer, **critic** (phê bình đối kháng theo từng khía cạnh), **reader-sim** (mô phỏng phản ứng người đọc theo từng khoảnh khắc), editor, continuity-checker... | Gần nhất về *hình dạng* (có bước phê bình + viết lại tách rời), nhưng là công cụ hội thoại tương tác nhiều lượt cho tiểu thuyết tiếng Anh nói chung, không có rubric số hoá, không có ngưỡng pass/fail, không có khái niệm "khoá lời dẫn rồi mới đặt neo" như quy trình của ta. |
| [rhavekost/author-toolkit](https://github.com/rhavekost/author-toolkit) | 16 | có LICENSE nhưng GitHub báo NOASSERTION (không rõ loại chuẩn, cần đọc kỹ) | 2026-07-22 | "Fiction Workshop" có persona "Developmental Editor" chấm plot/pacing/structure/stakes | Persona hội thoại (hỏi-đáp với người dùng), không phải bộ chấm điểm lấy input/output JSON để máy gọi tự động; dự án nhỏ, license mập mờ. |
| Tìm trực tiếp "script doctor"/"story doctor" + skill/claude trên GitHub search API | **0 kết quả** | — | — | — | Không tồn tại skill nào tự xưng đúng vai trò này còn sống. |

Kết luận (a): **không có skill nào đạt cả ba tiêu chí cùng lúc** — (1) chuyên biệt cho kể chuyện kinh dị bằng lời (không phải kịch bản phim), (2) có rubric số hoá dùng được làm gate pass/fail trong `auto` mode, (3) tương thích tiếng Việt + không đổi chữ sau khi neo. `haowjy/creative-writing-skills` (critic/reader-sim) là tài liệu tham khảo tốt nhất về *cách chia vai phê bình* (đối kháng theo từng khía cạnh, phản ứng theo từng khoảnh khắc) nhưng không adopt được nguyên trạng.

## (b) Ứng viên cho "Đạo diễn giọng"

Tìm theo ba nhánh: skill Claude cho TTS/voice, chuẩn SSML/prosody-tag của các TTS engine mã nguồn mở, và nghiên cứu học thuật LLM→prosody.

- **Skill Claude cho giọng nói** (`mcp-tool-shop-org/soundboard-plugin`, `paulpreibisch/AgentVibes`, `danielrosehill/Claude-Text-To-Speech-Toolkit-Plugin`, Microsoft `tts-voiceover`...): tất cả nhắm **đọc phản hồi của Claude Code cho người dùng nghe**, hoặc tạo SSML cho Azure/ElevenLabs/macOS-say. Không phải "biên tập giọng kể chuyện kinh dị" và **không engine nào nói tới Gwen-TTS/Qwen3-TTS**.
- **Chuẩn tag prosody của TTS mã nguồn mở** (`diodiogod/TTS-Audio-Suite` cho Higgs — tag `<|emotion:...|>`, `<|style:whispering|>`; `fishaudio/fish-speech` — tag `[whisper]`, `[pause]`...): đây là dạng "đạo diễn giọng" đúng ý nhưng **tag được chính engine đó diễn giải trong lúc suy luận** (giọng nghe tag rồi tự đổi ngữ điệu). Gwen-TTS trong `tts_worker.py` không đọc tag inline kiểu này — nó chỉ nhận `speed` per-line từ code và một bộ tham số sampling cố định theo voice folder. Gắn tag `[whisper]` vào text sẽ hoặc bị đọc thành chữ, hoặc bị bỏ qua tuỳ token hoá — **không kiểm chứng được** và vi phạm "không đổi chữ" của AGENTS.md.
- **Học thuật**: paper *Computational Narrative Understanding for Expressive TTS* (arXiv 2509.04072, có mã nguồn) dùng nhãn giả (pseudo-label động từ nói) rút từ audiobook thật để **fine-tune lại mô hình TTS**, không phải một bộ tạo chỉ dẫn per-line độc lập với engine. Không áp dụng được vì ta không được huấn luyện lại Gwen và không có tập audiobook gán nhãn tiếng Việt.
- **Tìm trực tiếp GitHub** cho "voice director" + tts: 6 kết quả, tất cả 0–6 sao, dự án cá nhân nhỏ (`Yinr/tts-voice-director` không mô tả 74 KB, `TAOMA-06/emotion-voice-director` 1 sao bằng tiếng Trung cho plugin Hermes, `Loveacup/tts-voice-director` 0 sao dùng Edge SSML) — toy repo, không license rõ ràng ổn định, không phù hợp production, và vẫn giả định engine hiểu SSML.
- **Hướng dẫn lồng tiếng audiobook** (Narration Box, ElevenLabs Projects, Backstage...): hữu ích làm *tài liệu nghề* (quy tắc dấu `/` cho beat ngắn, `//` cho beat dài, gạch chân để nhấn) nhưng đều giả định một diễn viên người hoặc một TTS đọc được markup — không phải công cụ/skill có thể adopt.

Kết luận (b): **không có skill/công cụ nào tương thích với giới hạn thật của Gwen-TTS trong dự án này** (chỉ speed/pause/gain per-line + chọn clip tham chiếu, không đọc tag). `scripts/delivery.py` hiện có đã đúng hướng duy nhất khả thi (quy mọi chỉ đạo về ba tham số số hoá), chỉ là rule-based cứng theo mã ý R1–R6 chứ chưa "đọc hiểu" nội dung câu để tinh chỉnh.

## Khuyến nghị

- **(a) Viết skill riêng** (`vp-script-director` nội bộ), không fork ngoài. Dùng `haowjy/creative-writing-skills` (critic tách theo khía cạnh + reader-sim theo khoảnh khắc) và cấu trúc tỷ lệ cảnh đã có sẵn trong `sys/horror/narration-style.md` làm tài liệu tham khảo cách chia tiêu chí, không copy code/text của họ (Apache-2.0 cho phép nhưng không cần thiết — mọi quy tắc horror của ta đã khác biệt và tiếng Việt).
- **(b) Viết skill riêng** (`vp-voice-director` nội bộ), không adopt gì từ ngoài, vì không có lựa chọn nào nói được "ngôn ngữ" mà Gwen-TTS hiểu. Skill này **nâng cấp cách gọi `scripts/delivery.py`** bằng một lớp LLM đọc hiểu ngữ nghĩa từng câu (thay vì chỉ regex theo mã ý) rồi vẫn xuất ra đúng schema số hoá (speed/gaps/gain) mà `direct()` đã định nghĩa — không đổi chữ, không cần engine hiểu tag.

## Thiết kế cụ thể

### (a) `vp-script-director` — Đạo diễn kịch bản

**Vai trò**: chạy sau khi `vp-content` viết xong outline + lời dẫn nháp cho mỗi lô cảnh (hoặc toàn bộ với video ngắn), **trước khi đặt coverage/anchor** — đúng thời điểm AGENTS.md cho phép sửa lời dẫn lần cuối. Không được chạy sau khi neo đã đặt (phải reject content rồi làm lại nếu muốn sửa lúc đó).

**SKILL.md outline**:
```
---
name: vp-script-director
description: Phê bình và tinh chỉnh lời dẫn truyện kinh dị trước khi khoá (trước coverage/anchor); dùng trong phần content của video truyện kinh dị, sau khi có bản nháp lời dẫn và trước khi gọi vp-content để đặt neo.
---
```
Nội dung: đọc `horror/narration-style.md` (văn phong), gọi một lượt agy chấm điểm theo rubric bên dưới (tiếng Anh, vì là chỉ dẫn nội bộ) trên toàn bộ lời dẫn của job; nếu có mục fail, sinh **bản sửa tối thiểu** (chỉ sửa câu/đoạn bị chấm fail, giữ nguyên cấu trúc cảnh, mã ý, nhân vật, chữ hiển thị) rồi chấm lại; tối đa N lượt sửa (đề xuất 2, xem "Vòng lặp" bên dưới); ghi báo cáo `agent-attempts/<run>/script-director.json` giống cách `long_script.py` ghi bằng chứng từng lượt, để không tạo báo cáo pass giả và để review có thể tra lại.

**Input** (JSON, đọc từ bản nháp content hiện có, không viết thêm trường mới vào schema production):
```json
{
  "job_id": "string",
  "mood": "slow_burn|psychological|folk|tense",
  "pov": "third|first",
  "scenes": [
    {"scene_id": "string", "requirements": ["R1".."R6"], "narration": "string (nguyên văn tiếng Việt)"}
  ]
}
```

**Output** (JSON, không phải schema production — chỉ để nội bộ script-director dùng và ghi log):
```json
{
  "job_id": "string",
  "pass": true,
  "rounds": 1,
  "scores": {
    "dread_escalation": {"score": 0-2, "evidence": ["scene_id: câu trích ngắn"], "notes": "..."},
    "pacing_rhythm": {"score": 0-2, "notes": "..."},
    "climax_payoff": {"score": 0-2, "notes": "..."},
    "oral_storytelling_voice": {"score": 0-2, "notes": "..."},
    "cliche_budget": {"score": 0-2, "notes": "..."},
    "hook_per_scene": {"score": 0-2, "notes": "..."}
  },
  "failed_criteria": ["tên tiêu chí"],
  "revised_scenes": [
    {"scene_id": "string", "narration": "string (chỉ có nếu đã sửa)", "diff_reason": "string"}
  ]
}
```

**Rubric chấm (thang 0–2 mỗi tiêu chí, ngưỡng pass = mọi tiêu chí ≥1 và tổng ≥ 10/12)**:

| Tiêu chí | 0 (fail) | 1 (yếu) | 2 (đạt) |
|---|---|---|---|
| Dread & escalation | Không có mô-típ rợn nào tăng dần; nhảy thẳng vào quái vật | Có leo thang nhưng bước nhảy không đều hoặc thiếu "false relief" | Mỗi điềm gở gần hơn/riêng tư hơn/khó giải thích hơn cái trước, đúng có 1 false relief giữa truyện |
| Pacing & rhythm | Câu dài đều, không đổi nhịp quanh cú giật | Có chậm lại trước scare nhưng scare line không tách dòng | 2–3 câu ngắn thường trước scare, scare line 3–8 từ, câu tiếp sau dấu chấm mới |
| Climax & payoff | Twist không liên quan chi tiết đã gieo | Có gieo nhưng payoff yếu/lộ sớm | Ít nhất một chi tiết bình thường ở đầu quay lại đổi nghĩa ở twist |
| Oral storytelling voice | Văn viết/sách vở, câu phức nhiều mệnh đề | Đa phần tự nhiên nhưng còn vài câu sách vở | Đúng giọng kể miệng, câu 6–20 từ, không quá 2 dấu "…"/cảnh |
| Cliché budget | Lặp lại cùng một sáo ngữ ≥2 lần trong video | Đúng giới hạn 1 lần/loại nhưng vẫn nhiều sáo ngữ khác chưa liệt kê | Trong hoặc dưới ngân sách sáo ngữ đã định nghĩa ở narration-style.md |
| Hook mỗi cảnh | ≥2 cảnh (trừ cảnh cuối) kết không có gợi mở | 1 cảnh thiếu hook | Mọi cảnh trừ cảnh cuối kết bằng câu hỏi/chi tiết chưa giải thích/hành động bị cắt |

**Vòng lặp sửa**: tối đa 2 lượt tự sửa (round 0 = chấm nháp, round 1 = sửa rồi chấm lại, round 2 = sửa lần cuối rồi chấm lại). Hết 2 lượt vẫn fail → đưa vào `needs_attention` (auto mode) hoặc trả về `vp-content` kèm danh sách tiêu chí fail cụ thể để người viết (agy) sửa tay (review mode). **Không lặp vô hạn**, đúng nguyên tắc AGENTS.md.

**Ràng buộc bắt buộc giữ**: sửa chỉ được đổi `narration`/`narration_en` của các cảnh bị fail, **không đổi mã ý (R1–R6), không đổi số cảnh, không đổi visible_text, không đổi nhân vật**; chạy trước khi `vp-content` đặt `coverage`/`claims`/anchor — nếu neo đã tồn tại cho job này thì script-director từ chối chạy và báo lỗi rõ ràng thay vì âm thầm sửa lời dẫn đã neo (vi phạm quy tắc "không sửa lời dẫn sau khi đã neo"). Không đụng `prompt_templates.py`.

**Nối vào flow hiện có**: chèn giữa bước "viết lời dẫn" và bước "đặt coverage/anchor" trong `vp-content`/`long_script.py`, dùng agy (không API trả phí, đúng chủ trương "Không dùng API trả phí"). Vì `long_script.py` đã kiểm tra từng đoạn ngay khi nhận, script-director chạy **sau khi ghép toàn bộ** (để chấm được escalation/climax xuyên suốt, không chấm từng đoạn rời), rồi mới cho qua bước neo.

### (b) `vp-voice-director` — Đạo diễn giọng

**Vai trò**: chạy trong phần media, thay thế/nâng cấp bước gọi `scripts/delivery.py::direct()` hiện tại. Không sửa chữ; chỉ output ba tham số số hoá mà `tts_worker.py` đã biết đọc (`speeds`, `gaps`/`tail`, `gains`) cộng thêm gợi ý chọn `reference_audio` nếu về sau có nhiều voice folder.

**SKILL.md outline**:
```
---
name: vp-voice-director
description: Sinh chỉ dẫn đọc từng câu (tốc độ, khoảng nghỉ, độ to) cho lời dẫn truyện kinh dị đã khoá, đưa vào scripts/delivery.py trước khi tổng hợp giọng; dùng trong phần media, sau khi content đã có quyết định hợp lệ.
---
```
Nội dung: đọc `narration-style.md` mục "How the voice will read it" và `channel.json.delivery` (bảng mã ý R1–R6 hiện có vẫn là **baseline bắt buộc giữ**, vì đã đo đạc thật trên job `thu-5p-h007g`); skill này chỉ **thêm một lớp tinh chỉnh ngữ nghĩa per-line** phía trên baseline, không thay thế nó — với lý do bảng rule-based hiện tại không phân biệt được, ví dụ, một câu ngắn 8 từ mang tính mô tả bình thường với một câu ngắn 8 từ đúng là scare line.

**Input**: đúng cấu trúc `scenes` mà `direct()` nhận (`scene_id`, `requirements`, `texts` đã tách theo `split_dialogue`), cộng `mood`.

**Output** (JSON, khớp field-by-field với những gì `tts_worker.py` tiêu thụ qua `speeds`/`gaps`/`gain_db`, để không cần đổi schema production, chỉ đổi nguồn sinh):
```json
{
  "scene_id": "string",
  "style": "host_open|setup|rising|climax|aftermath|host_close",
  "line_directions": [
    {
      "text": "string (nguyên văn, không đổi)",
      "speed_multiplier": 0.80-1.10,
      "pause_after_s": 0.0-2.0,
      "gain_db": 0,
      "delivery_tag": "neutral|tense_short|dialogue_calm|dialogue_shout|reveal_slow|question|beat_pause",
      "reason": "string ngắn, vì sao (để review đọc được, không phải vì máy 'cảm nhận')"
    }
  ]
}
```
`delivery_tag` chỉ là **nhãn nội bộ để log/debug** — khi đưa vào `tts_worker.py` nó bị bỏ, chỉ ba số `speed_multiplier`/`pause_after_s`/`gain_db` được dùng (đúng giới hạn thật của Gwen). `gain_db` mặc định giữ 0 theo đúng phát hiện đã ghi trong `horror.md` (đổi gain nghe như vặn nhỏ nhạc, không phải đổi chất giọng) — skill không được tự ý bật lại trừ khi có giọng thì thầm thật đã kiểm chứng bằng tai.

**Rubric kiểm tra output trước khi cho qua** (pass/fail, không phải điểm mờ vì đây là kiểm tra kỹ thuật, không phải duyệt chất lượng):
- Mọi `speed_multiplier` nằm trong biên đã đo an toàn cho Gwen: 0.80–1.10 (ngoài khoảng này giọng méo/nuốt chữ theo ghi chú `tts_worker.py`) → fail nếu vượt.
- `pause_after_s` không âm, không vượt 2.0s (giữ nhịp video) → fail nếu vượt.
- Số câu output = số câu input (không được gộp/tách lại câu) → fail nếu lệch.
- `text` từng dòng so khớp tuyệt đối (string equality) với `texts` gốc từ `direct()` sau `split_dialogue` → fail nếu khác **dù chỉ một ký tự** (đây là gate cứng nhất, bảo đảm "không đổi chữ").
- Câu đã có `speeds` do baseline R1–R6 gán severity cao (climax, reveal) không được nới lỏng (chỉ được siết thêm, không được làm chậm lại) — so với baseline của `direct()`, output chỉ được di chuyển trong biên ±15%.

**Vòng lặp**: tối đa 1 lượt tự sửa nếu rubric kỹ thuật fail (ví dụ tốc độ vượt biên) — đây là sửa lỗi định dạng, không phải "duyệt chất lượng nghệ thuật", nên không cần vòng phê duyệt riêng; nếu vẫn fail sau 1 lượt, **rơi về baseline `direct()` thuần rule-based** (an toàn, đã đo đạc) thay vì chặn cả job — ghi rõ trong log là đã fallback, không giả vờ đã tinh chỉnh.

**Nối vào flow**: `pilot.py run JOB media` → bước audio hiện gọi `scripts/delivery.py::direct(scenes, profile, mood)` trực tiếp; thêm một bước tuỳ chọn trước đó gọi `vp-voice-director` (agy) lấy `line_directions`, merge vào `speeds`/`gaps`/`gains` mà `direct()` trả về (merge theo chỉ số câu, không thay cấu trúc dict), rồi mới đưa cho `tts_worker.py`. Việc merge giữ nguyên toàn bộ hợp đồng dữ liệu hiện có nên không cần sửa `tts_worker.py`. Đúng chủ trương AGENTS.md: **không sửa renderer/schema** để phục vụ một job — đây là thêm một nguồn sinh tham số tuỳ chọn, có fallback an toàn về hành vi cũ.

**Duyệt**: đây vẫn là bước nội bộ (giống "chuẩn bị ảnh nhân vật" trong AGENTS.md) — không mở điểm dừng duyệt riêng; kết quả cuối cùng vẫn chỉ hiện ở điểm duyệt `media` khi người dùng/máy nghe WAV thật.

## Vì sao không adopt/adapt bất kỳ repo ngoài nào

1. Không repo nào (a) chuyên viết/chấm truyện kinh dị kể miệng bằng tiếng Việt với rubric số hoá dùng được trong `auto` mode.
2. Không repo/chuẩn nào (b) nói được "ngôn ngữ" giới hạn thật của Gwen-TTS trong dự án (chỉ speed/pause/gain per-line, không SSML/tag cảm xúc inline) — mọi hệ sinh thái voice-direction tìm được (Higgs, fish-speech, ElevenLabs, Azure SSML) giả định engine đọc được tag, điều Gwen không làm.
3. Toàn bộ ứng viên nhỏ tự xưng đúng tên ("voice director", "script doctor") đều 0–6 sao, không license rõ, không hoạt động — rủi ro bảo trì cao hơn lợi ích tiết kiệm công viết.
4. Viết riêng cho phép giữ đúng các ràng buộc cứng của dự án (không đổi chữ sau khi neo, không sửa `prompt_templates.py`, không dùng API trả phí, giữ baseline `delivery.py` đã đo đạc thật) mà không repo ngoài nào biết tới.
