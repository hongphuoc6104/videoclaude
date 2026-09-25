# Rà độc lập content H001e khi đang viết — 24/09/2026

Đây là ghi chú chỉ đọc theo từng chunk trong job `h001-auto-20260924e`, **không phải quyết định duyệt**. Job vẫn đang viết; chỉ kết luận sau khi content revision và bộ đánh giá `auto` có artifact đầy đủ.

## SC01–SC02

- Cặp mở đã qua cổng nội bộ sau một lượt viết lại. SC01 không nói trước nguồn tiếng gõ. Ảnh mascot nêu nụ cười mở và lưỡi san hô; ảnh An ngoài hẻm nêu áo sơ mi caro khoác ngoài. Anchor và mật độ hình đạt.
- Lưu ý biên tập nhẹ: SC01 kể “Người thuê trước dọn đi vội vã” như một sự việc xác định dù dàn ý chưa xác lập. Kiểm xem câu chuyện sau có làm rõ hoặc để nó là cách người dẫn hình dung.

## SC03–SC04

- Phòng rẻ bất thường và bà chủ tránh nhìn An đã có; coverage, anchor, mật độ hình đạt.
- SC03_I1/SC04_I3 tự thêm áo cardigan cho bà chủ ngoài hồ sơ trang phục; ảnh SC03_I2 lại không nhắc. SC04_I3 đưa An vào ảnh kế thừa chỉ có bà chủ nhưng chưa nói rõ áo caro của An.
- SC03 nói bước chân trên “nền cát”, còn bối cảnh và ảnh là lối xi măng ẩm nứt.

## SC05–SC06

- SC04 kết với cửa phòng hé; SC05 lại mở bằng việc An tra chìa khóa. SC05_I1 bỏ áo sơ mi caro ngay lúc An vừa bước vào, chưa có động tác cởi áo.
- SC05_I3 chưa nói rõ mặt gương úp tường, dễ lệch cú phát hiện ở SC09.
- SC06 nói đêm đầu “trôi qua ... tĩnh mịch” rồi có tiếng gõ lúc hai giờ; một âm thanh còn đánh thức An trước chuỗi ba tiếng gõ, tạo hai đợt âm không chủ ý.
- SC06_I2 đặt điện thoại trên sàn gỗ, trong khi lời dẫn đặt cạnh gối và phòng đã có sàn gạch bông. SC06_I3 nói phòng không có người nhưng vẫn mang `character_ids: [CH02]`.
- Coverage, anchor và mật độ hình đạt; chưa lộ nguồn gõ hay có lời rủ người xem làm theo.

Các điểm trên cần đối chiếu với bản content hoàn chỉnh và ảnh thật, rồi sửa bằng `reject content` hoặc `reject media` đúng phần nếu còn ảnh hưởng chất lượng; không chỉnh trực tiếp chunk/revision đã lưu.

## SC07–SC10

- Ba tiếng gõ đêm đầu, hành lang trống và nhịp yên tâm giả đã có. Coverage, anchor và mật độ hình đạt; chưa có CTA hoặc lời khẳng định truyện có thật.
- SC09 cho An nhìn/sờ rõ mặt lưng gương hướng ra phòng, nhưng chưa thấy giấy vàng dán trên chính mặt lưng. Sau SC10 lật gương, mặt lưng quay vào tường nên việc thấy giấy ở SC12–SC13 càng cần động tác nhấc/nghiêng gương hoặc giải thích giấy giấu dưới mép khung.
- SC08_B4 neo giả thuyết người phòng bên gõ nhầm, nhưng dùng ảnh SC08_I2 chỉ có mái tôn rung. Ảnh mái tôn được vẽ như sự việc thật dù đây mới là suy đoán của An; `based_on` từ ảnh trong phòng sang ngoài mái cũng thiếu chuyển cảnh.
- SC07_B4 neo cửa hé khi ảnh I2 mới tả bàn tay chạm chốt; SC08_I4/SC10_I4 chưa khóa rõ mặt gương úp hoặc mã nhân vật khớp mô tả.
- SC10 khẳng định An “đảo lộn trật tự vốn có của căn phòng” dù cậu chưa thể biết cơ chế này; nên giữ ở mức cảm giác/chi tiết quan sát được.

## SC11–SC14

- Đêm thứ hai rồi đêm thứ ba đúng thứ tự; coverage, anchor và mật độ hình đạt.
- SC12 chỉ thấy mép giấy qua khe hẹp sau gương đã lật, nhưng SC13 không nhấc/nghiêng gương mà soi rõ cả tờ giấy, mực và ba vạch; ảnh I3/I4 còn cho cận cảnh trọn tờ giấy. SC09 trước đó đã nhìn/sờ mặt lưng gương mà không thấy giấy. Đây là lỗi vị trí/khả năng quan sát của lời dẫn, cần sửa ở content.
- SC12 gọi góc gương là “nơi phát ra tiếng động” trước cú lật; SC13 diễn giải ba vạch là để “đếm” sớm hơn cao trào. Cả hai nên giữ ở mức quan sát hoặc nghi vấn để bảo vệ cú lật.
- SC11 mở bằng “Đêm thứ hai ... trôi qua” rồi cảnh vẫn ở trước hai giờ cùng đêm. SC14_I5/B7 muốn hiện thời gian trên điện thoại nhưng `visible_text: []`, nên ảnh không có số để người xem đọc mốc giờ.

## SC15–SC16

- Nguồn ba tiếng gõ và tiếng thứ tư đều là phía gương, nhưng từ “Cốc… cốc… cốc.” ở đầu SC15 đến “Tiếng gõ thứ tư vang lên” trong SC16 còn 119 từ lời dẫn (ước hơn 36 giây), trong khi lời dẫn nói chỉ hai giây trôi qua. Cần đưa ba tiếng và nhịp thứ tư về gần nhau để nghe là cùng một chuỗi đếm.
- SC16 khẳng định chắc thực thể sau gương “đang đếm từng người” dù dàn ý chỉ cho An nảy ra một suy đoán; ba vạch chưa chứng minh quy luật đó. Giữ góc nhìn và bí ẩn bằng cách cho thấy ý nghĩ của An, không tuyên bố sự thật khách quan.
- SC16 không có SFX riêng ở tiếng gõ thứ tư, trong khi SC15 đã gắn hiệu ứng gõ cho ba tiếng. Cần xem khả năng neo một cú gõ riêng khi sửa content/video.
- Vị trí gương đổi từ “bên cạnh bàn” sang “directly above the desk” ở SC15_I3. SC16_I4 kế thừa một ảnh cận mặt An nhưng muốn giữ cả bàn/gương/phòng chưa hiện trong ảnh gốc. Anchor, coverage và mật độ hình vẫn đạt.

## SC17–SC18

- **Mâu thuẫn cú lật:** SC16 nói tiếng thứ tư đếm thêm An; SC17 lại gọi bóng đen trong gương là “Người thứ tư mà tiếng gõ vừa đếm”. Cần giữ một nghĩa nhất quán hoặc gieo rõ một cú đảo nghĩa có chủ ý.
- SC17 khẳng định bóng đen “ngay trong phòng” khi An mới chỉ thấy trong gương. An nhìn thẳng vào gương nhưng lời dẫn và SC17_I4 nói bóng hiện sau “lưng phản chiếu” của cậu; góc nhìn đúng là phía sau vai/hình mặt An trong gương.
- SC18 chạy thoát và bỏ đồ nối hợp lý; nhưng SC18_I2 đổi sàn hành lang từ xi măng ẩm sang gạch hoa, SC18_I4 cho An nhìn lại dù lời dẫn nói không ngoái đầu. Coverage, anchor và mật độ hình đạt.
