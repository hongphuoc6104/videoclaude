# Luồng tự động làm video truyện kinh dị — 24/09/2026

```mermaid
flowchart TD
    A[Chọn 6 thông số và hạt giống trong kho] --> B[bank.py start: giữ chỗ hạt giống, tạo brief và job]
    B --> C[doctor, status, next]
    C --> D[pilot.py run JOB content]
    D --> E[Antigravity CLI agy: lập dàn ý, viết kịch bản theo đoạn nếu dài]
    E --> F[Kiểm tra cấu trúc, chính sách kinh dị; tạo content review.md]
    F --> G{Chế độ của job}
    G -->|review| H[Người dùng đọc kịch bản và duyệt đúng revision]
    G -->|auto| I[agy đánh giá artifact thật, lưu machine-reviews]
    H --> J[Content có quyết định hợp lệ]
    I -->|pass| J
    I -->|fail hoặc unsupported| X[Dừng để sửa hoặc needs_attention]
    J --> K[pilot.py run JOB media]
    K --> L[TTS local đọc trước, đo WAV và thời lượng thật]
    L --> M[Flow tạo và đăng ký ảnh nhân vật, rồi ảnh các cảnh]
    M --> N[Tạo phụ đề, nhịp hình theo âm thanh; media review.md]
    N --> O{Chế độ của job}
    O -->|review| P[Người dùng nghe, xem ảnh và đối chiếu nhân vật]
    O -->|auto| Q[agy nghe, xem artifact thật; lưu machine-reviews]
    P --> R[Media có quyết định hợp lệ]
    Q -->|pass| R
    Q -->|fail hoặc unsupported| X
    R --> S[pilot.py run JOB video]
    S --> T[Dựng hình, trộn nhạc nền và tiếng động CC0, xuất bản dựng MP4]
    T --> U[Video review.md để xem và nghe]
    U --> V{Chế độ của job}
    V -->|review| W[Người dùng duyệt đúng revision]
    V -->|auto| Y[agy xem, nghe MP4 thật; lưu machine-reviews]
    W --> Z[Đủ 3 quyết định hợp lệ]
    Y -->|pass| Z
    Y -->|fail hoặc unsupported| X
    Z --> AA[Sao chép MP4 vào video/JOB, kiểm tra bản xuất]
    AA --> AB[bank.py mark JOB]
```

**Chỗ xem thử.** `agy --help` không liệt kê lệnh `preview`. `agy` được gọi để viết kịch bản và đánh giá trong chế độ `auto`. Mỗi mốc có `runs/<job>/reviews/<phần>/<revision>/review.md` dẫn tới artifact cần xem/nghe. Trang [nghe thử giọng](voice-audition-20260924/index.html) là thử nghiệm độc lập, không phải cổng duyệt của job. `python3 sound.py preview ID OUT.wav` chỉ tạo mẫu nghe một âm thanh nền/hiệu ứng CC0.

**Trạng thái hiện tại.** `thu-5p-h007g` là job `review` 4–6 phút, 16:9, hạt giống H007 đang giữ chỗ. Kịch bản đã có quyết định; [media revision 1](../runs/thu-5p-h007g/reviews/media/1/review.md) có WAV 298,93 giây và 22 ảnh nhưng chưa có quyết định duyệt media. Chưa có MP4 trong `video/`. Các job thử cũ hiện bị `Protected implementation changed` vì mã và cấu hình TTS đang thay đổi; không sửa integrity baseline để chạy tiếp. `doctor` nhận diện `agy`, công cụ dựng video và môi trường Gwen TTS, nhưng vẫn báo `machine_review_media_verified=false`, nên chưa thể coi nhánh tự duyệt media/video đã nghiệm thu.

Nguồn quy trình: [workflow.md](../docs/workflow.md), [horror.md](../docs/horror.md), [vp-horror](../../.agents/skills/vp-horror/SKILL.md), [workflow.py](../workflow.py), [agy_pipeline.py](../scripts/agy_pipeline.py).
