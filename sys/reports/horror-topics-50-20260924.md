# Khảo sát chủ đề kênh truyện kinh dị lớn và 50 ý tưởng mới

Ngày thực hiện: 2026-09-24. Nguồn: trang kênh YouTube công khai (không đăng nhập, không dùng API trả phí), đọc qua trình duyệt đã render và WebSearch để xác định kênh. Dữ liệu thô đầy đủ: `sys/reports/horror-topics-raw-20260924.json` (240 tiêu đề thật từ 11 kênh). 50 ý tưởng ở dạng máy đọc: `sys/reports/horror-topics-50-20260924.json`.

## 1. Các kênh đã khảo sát

| Kênh | Kênh/ngôn ngữ | Subscriber | Số tiêu đề lấy | Đặc điểm |
|---|---|---|---|---|
| [HẺM Truyện Ma](https://www.youtube.com/@HEMTruyenMaNP) | vi | 1.5M | 30 | MC Đình Soạn & MC Ngọc Lâm; billed as 'truyện ma có thật' (claims-true framing, which our channel must not use) |
| [Truyện Ma Việt](https://www.youtube.com/channel/UCoYx3yrBnPkRyMk_kLMt6qg) | vi | 44.3K | 30 | Reads classic named authors (Nguyễn Ngọc Ngạn, Người Khăn Trắng); long-form (1-3h) full-story uploads |
| [Đất Đồng Radio (Nguyễn Huy)](https://www.youtube.com/@datdongradio) | vi | 966K | 30 | Strong rural/Mekong-delta ('miền Tây') folk-sorcerer serial format with a recurring character ('đệ tam pháp sư Toàn') |
| [Truyện ma Quàng A Tũn](https://www.youtube.com/@truyenmaquangatun22h) | vi | 810K | 17 | Long multi-part 'pháp sư diệt cương thi / trừ quỷ' martial-sorcerer serials, nightly 22:00 livestream format |
| [Truyện Ma Đình Soạn - Official Channel](https://www.youtube.com/@OfficialTruyenMaDinhSoan) | vi | 9 | 13 | Small/new channel but useful for current title-formula patterns: 'Truyện Ma [tag] | Hook line A | Hook line B' |
| [Truyện Ma Hay Nhất Mọi Thời Đại](https://www.youtube.com/@truyenhaydaiky) | vi | 35.6K | 15 | Domestic-crime-horror subgenre: titles foreground a family member's violent crime, resolved as karmic ghost revenge |
| [Mr. Nightmare](https://www.youtube.com/@mrnightmare) | en | 7.14M | 24 | Numbered/location-based 'TRUE horror stories' compilations; new setting each release (mall, fair, first day of school...) |
| [Lazy Masquerade](https://www.youtube.com/@LazyMasquerade) | en | 1.9M | 21 | Unsolved-mystery / disturbing-photo / compilation format; 'Top N ... Compilation' is the dominant high-view pattern |
| [Dr. NoSleep Animations](https://www.youtube.com/@DrNoSleepAnimations) | en | 657K | 19 | Animated horror; single scenario repeated across many episodes/compilations (lockdown, skinwalker, oil rig, submarine) |
| [Chilling Scares](https://www.youtube.com/@ChillingScares) | en | 2.86M | 17 | 'Found footage / caught on camera' documentary-style format; not narrated fiction but shares the hook formula |
| [MrCreepyPasta](https://www.youtube.com/@MrCreepyPasta) | en | 1.72M | 24 | Fiction narration of named creepypasta characters/urban legends (Jeff the Killer, Smile Dog, The Rake...) — closest English analogue to our fiction-only, oral-narration format |

Tổng cộng **240 tiêu đề thật** (yêu cầu tối thiểu 150). Dữ liệu gồm tiêu đề, lượt xem hiển thị và tuổi video tại thời điểm khảo sát, sắp theo thẻ "Popular" của từng kênh khi có (tức là các video nhiều lượt xem nhất mọi thời của kênh đó).

## 2. Mô-típ và công thức đặt tên lặp lại

### 2.1 Kênh truyện ma tiếng Việt

- **Khung "chuyện có thật"**: gần như mọi kênh lớn (HẺM Truyện Ma, Truyện Ma Việt, Truyện ma Quàng A Tũn, Đất Đồng Radio) gắn nhãn "truyện ma có thật", "TG ... viết", "kể lại người từng gặp" ngay trong tiêu đề — đây là công thức thu hút số 1 của thị trường, nhưng kênh của chúng ta **không được dùng** (luôn là hư cấu).
- **Oan hồn báo oán / nhân quả báo ứng**: mô-típ xuyên suốt — vong hồn quay lại đòi công bằng cho một cái chết oan. Đây là phần lõi cảm xúc có thể giữ lại (phù hợp mood `folk`/`slow_burn`), chỉ bỏ khung "có thật" và mọi chi tiết bạo lực.
- **Serial pháp sư/thầy cúng trừ tà, cương thi**: các bộ nhiều tập theo một nhân vật thầy pháp cố định ("đệ tam pháp sư Toàn", "Mao Sơn tróc quỷ nhân") rất ăn khách nhưng đi kèm rủi ro chính sách: dễ trôi thành "hướng dẫn nghi lễ/trừ tà" nếu kể chi tiết cách hành lễ. Ý tưởng mới trong báo cáo này tránh nhân vật thầy pháp hành lễ, giữ lại chỉ phần điềm báo và hậu quả.
- **Bạo lực gia đình/hình sự hoá**: nhóm tiêu đề đang lên rất mạnh trên kênh nhỏ hơn (Truyện Ma Hay Nhất Mọi Thời Đại) là "GIẾT VỢ HIẾP CON", "Mổ Bụng Con Dâu", "Cưỡng Hiếp Xác Chết" — đây là vùng cấm tuyệt đối theo `blocked_terms.gore_self_harm` và chuẩn nội dung của kênh. Bài học rút ra: giữ **chủ đề bí mật/tội lỗi gia đình** (rất ăn khách) nhưng chuyển hoàn toàn sang ám ảnh tâm lý và im lặng, không mô tả hành vi bạo lực.
- **Địa danh thật**: nhiều tiêu đề top-view gắn tên tỉnh/thành thật (Sông Tô Lịch Hà Nội, Bắc Ninh, Hà Tây, Cần Thơ, Hải Phòng, Đà Nẵng) để tăng độ tin — vi phạm trực tiếp `real_places`; mọi ý tưởng mới dùng bối cảnh hư cấu tả chung.
- **Thẻ cường điệu trong ngoặc**: "[HÃI LẮM]", "[RUN SỢ]", "[TRỌN BỘ]", "Siêu Phẩm HOT" — công thức giật tít bằng thán từ; kênh của chúng ta không dùng thẻ viết hoa toàn bộ (đúng quy tắc Vieneu TTS không viết hoa toàn bộ để tránh đọc đánh vần), nên tiêu đề mới ưu tiên một cụm danh từ hình ảnh cụ thể thay vì thán từ.
- **Vật/nơi neo nỗi sợ**: gương, giếng, cây đa/cây gạo, nhà trọ ma ám, mộ, sông nước, bùa ngải — đều là chất liệu tốt, phần lớn ý tưởng mới đổi vật thể hoặc cơ chế để không trùng 16 hạt giống đã có trong `horror/seeds.json`.

### 2.2 Kênh tiếng Anh

- **Mr. Nightmare**: công thức "N + [Terrifying/Scary/Disturbing] + TRUE + [bối cảnh] + Horror Stories", đổi bối cảnh mỗi kỳ (mall, fair, first day of school, night walk, garage sale, rest area, stalker...). Bài học: **một bối cảnh sinh hoạt quen thuộc + một chi tiết lệch chuẩn** là công thức hook mạnh nhất, tách khỏi khung "TRUE" ta vẫn dùng được ý tưởng bối cảnh.
- **Lazy Masquerade**: "Top N ... Mysteries/Compilation", ảnh cũ kèm hậu cảnh rợn, "unsolved mystery". Bài học: mở đầu bằng một chi tiết cụ thể chưa lý giải được (ảnh, cuộc gọi, ghi âm) rồi giữ sự mơ hồ tới cuối — khớp thẳng với yêu cầu "escalation rule" và "ending stays open" của mood `psychological`.
- **Dr. NoSleep (animated)**: một kịch bản/bối cảnh cố định lặp lại thành nhiều tập (lockdown trường học, giàn khoan, tàu ngầm, Skinwalker Ranch). Bài học: bối cảnh nghề nghiệp/không gian đặc thù (ca trực, nhà kho, bệnh viện) tạo cảm giác quen mà vẫn mới; nhóm ý tưởng "Ca đêm / công việc khuya" trong báo cáo này khai thác hướng này.
- **Chilling Scares**: khung "tài liệu" — "N Most Disturbing Things Caught on [loại camera] Footage", "... That Turned Out to Be True". Không phải kể chuyện hư cấu nên không dùng trực tiếp, nhưng hook "thiết bị ghi hình ghi lại thứ không giải thích được" chuyển hoá tốt sang chi tiết cảm biến/đồng hồ/camera an ninh trong bối cảnh đô thị.
- **MrCreepyPasta**: tường thuật nhân vật/truyền thuyết cố định trong ngoặc kép ("Jeff the Killer", "The Rake", "Smile Dog") dưới thương hiệu "CreepyPasta Storytime" — đây là kênh tiếng Anh **gần nhất về bản chất** với kênh của chúng ta: kể chuyện hư cấu bằng giọng đọc, không tuyên bố có thật. Khác biệt: họ xây nhân vật quái vật lặp lại xuyên nhiều video (thương hiệu hoá quái vật), còn kênh của chúng ta theo đúng chuẩn "mỗi video một hạt giống", nhân vật viết mới mỗi lần.

## 3. Chủ đề phổ biến nhưng nằm ngoài giới hạn — và cách viết lại an toàn

| Chủ đề ăn khách trong dữ liệu thô | Vì sao không dùng trực tiếp | Cách chuyển hoá cho kênh |
|---|---|---|
| "Truyện ma có thật", "TRUE stories", "turned out to be true" | Vi phạm quy tắc hư cấu tuyệt đối và `blocked_terms.claims_true` | Bỏ hẳn khung xác nhận thật; giữ cảm giác gần gũi bằng giọng kể ngôi thứ nhất/thứ ba bám sát một nhân vật |
| Serial thầy pháp/đạo sĩ trừ tà, bùa ngải, cương thi | Dễ trôi thành hướng dẫn nghi lễ (`ritual`) nếu mô tả cách hành lễ, bùa chú | Giữ hậu quả và không khí bùa ngải như bối cảnh nền, không mô tả các bước làm bùa/gọi hồn; nhân vật thầy pháp nếu có chỉ được nhắc tới, không trình diễn nghi lễ |
| Tội ác gia đình graphic (giết, hiếp, mổ, chặt) | Vi phạm `gore_self_harm` và tiêu chí không máu me/tự hại của kênh | Giữ mô-típ "bí mật/tội lỗi gia đình bị giấu kín" nhưng chuyển hẳn sang ám ảnh tâm lý, vật chứng im lặng (thư, ảnh, sổ) thay vì mô tả hành vi |
| Tên tỉnh/thành, địa danh du lịch thật để tăng tin cậy | Vi phạm `real_places` và domain_requirements | Bối cảnh luôn hư cấu, tả chung ("một xóm ven sông", "một trạm dừng ven quốc lộ") |
| Thử thách/rủ người xem làm theo (advent trong một số video tâm linh) | Vi phạm quy tắc "không thách đố người xem" | Không có lời mời gọi hành động nào hướng ra ngoài câu chuyện; mọi hành động chỉ thuộc về nhân vật |
| "Rules horror" kiểu quốc tế (danh sách quy tắc sinh tồn) | Dễ đọc như hướng dẫn làm theo nếu trình bày thành danh sách tách rời | Chỉ kể quy tắc như một chi tiết trong lời dặn của câu chuyện, không trình bày thành danh sách/thử thách |
| Hình ảnh treo cổ, thắt cổ ("cây đa thắt cổ", "treo cổ" xuất hiện trong dữ liệu gốc) | Nằm trong yêu cầu cấm rõ ràng của người dùng: không hình ảnh treo cổ | Không ý tưởng nào trong 50 ý tưởng dùng hình ảnh treo/thắt cổ; các mô-típ cây cổ thụ chuyển sang hướng khác (ánh sáng, âm thanh, rễ cây) |

## 4. 50 ý tưởng gốc

Mỗi ý tưởng độc lập với 16 hạt giống hiện có trong `horror/seeds.json` (đối chiếu ở cột "Mô-típ tham khảo"); đây là **gợi ý để chọn lọc**, chưa phải hạt giống chính thức — muốn dùng, người viết cần thêm vào `horror/seeds.json` theo đúng định dạng (`title`, `subgenre`, `setting`, `premise`, ≥3 `dread`, `twist`, `basis`) rồi mới `bank.py start` được job.

### Làng quê / dân gian (8 ý tưởng)

**I01. Giếng Không Đáy Cuối Vườn**
- Bối cảnh: Xóm nhỏ ven sông hư cấu, ruộng khô nứt nẻ, không tên tỉnh thành thật.
- Tiền đề: Một gia đình đào giếng mới giữa mùa hạn, nhưng nước không bao giờ dâng lên, chỉ có hơi lạnh bốc lên mỗi khi trăng khuyết.
- Cốt lõi nỗi sợ: Giếng dường như "nghe" được tên người ta thì thầm khi cúi xuống múc nước.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Đêm giếng bất ngờ đầy nước trở lại, đúng đêm một cái tên vọng lên từ đáy giếng — tên của chính người đào giếng.
- Mô-típ tham khảo: Mô-típ giếng cổ/oan hồn dưới đất phổ biến ở serial dân gian miền Tây (Đất Đồng Radio); bỏ khung "có thật" và mọi địa danh thật.

**I02. Tiếng Mõ Canh Ba Đổi Nhịp**
- Bối cảnh: Xóm nhỏ còn giữ lệ gác đêm cũ, nhà tranh vách đất.
- Tiền đề: Người giữ mõ báo canh trong xóm nhận ra nhịp gõ ba tiếng quen thuộc bỗng đổi thành bốn, rồi năm, mỗi đêm một nhịp lạ hơn.
- Cốt lõi nỗi sợ: Số nhịp mõ tăng dần báo hiệu có ai đó trong xóm sắp bị "gọi tên".
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Đêm mõ đổi nhịp trùng đúng nhịp tim của người giữ mõ — không ai gõ mà mõ vẫn kêu.
- Mô-típ tham khảo: Điềm báo bằng âm thanh lặp lại và leo thang, biến thể từ serial pháp sư của Đất Đồng Radio nhưng bỏ hẳn yếu tố trừ tà/nghi lễ.

**I03. Người Gánh Hàng Phiên Chợ Lẻ**
- Bối cảnh: Chợ phiên hư cấu họp ở bãi đất trống đầu làng.
- Tiền đề: Một gánh hàng rong chỉ xuất hiện đúng những phiên chợ lẻ, bán đủ thứ đồ cũ của người trong làng — kể cả đồ của người còn sống.
- Cốt lõi nỗi sợ: Nhìn thấy đồ của mình trong gánh hàng nghĩa là sắp mất nó thật.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Cô gái tìm thấy đúng chiếc khăn mình đang đội trong gánh hàng, dù chưa hề đánh mất.
- Mô-típ tham khảo: Mô-típ "chợ ma" dân gian; đổi từ format nhân vật lặp lại (đệ tam pháp sư) sang một hiện tượng đơn lẻ, không có ai trừ tà.

**I04. Cây Gạo Không Đổ Lá Mùa Đông**
- Bối cảnh: Bến sông nhỏ đầu làng, hư cấu.
- Tiền đề: Cây gạo đầu làng xanh tốt bất thường suốt mùa đông trong khi mọi cây khác trụi lá, và không con vật nào dám lại gần gốc cây.
- Cốt lõi nỗi sợ: Rễ cây ôm quanh một điều gì đó chưa ai dám đào lên.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Cơn bão quật cây gạo bật gốc, lộ ra một khoảng đất trống hình người dưới rễ cây — chỉ gợi qua hình dáng đất, không tả gì thêm.
- Mô-típ tham khảo: Biến thể mô-típ "cây gạo/cây đa" quen thuộc, khác seed H001 đã có bằng cách đổi từ chuyện tình sang bí ẩn im lặng của đất.

**I05. Bà Đỡ Không Ai Mời** — *có yếu tố cần cân nhắc thêm*
- Bối cảnh: Xóm nhỏ hẻo lánh, nhà tranh mái rạ.
- Tiền đề: Mỗi khi xóm có người sắp sinh, một bà lão lạ mặt luôn có mặt trước cửa, dù không ai gọi bà đến.
- Cốt lõi nỗi sợ: Bà đỡ luôn biết trước điều mà chính người mẹ chưa kịp nói ra.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Đêm bà đỡ xuất hiện trước cửa nhà chính nhân vật, dù cô chưa hề mang thai.
- Mô-típ tham khảo: Điềm báo trước sinh — biến thể độc lập, không dùng danh xưng thầy pháp để tránh gợi ý nghi lễ.
- ⚠️ Lưu ý khi viết: Chủ đề sinh nở/trẻ sơ sinh cần giữ mơ hồ, không gợi ý tổn hại tới mẹ hoặc trẻ.

**I06. Đường Ruộng Không Có Lối Ra**
- Bối cảnh: Cánh đồng lúa ngoài xóm, không tên địa danh.
- Tiền đề: Một con đường mòn giữa cánh đồng luôn dẫn người đi đêm quay lại đúng chỗ họ xuất phát, dù đã rẽ bao nhiêu lần.
- Cốt lõi nỗi sợ: Mất phương hướng ngay trên đất quen — nỗi sợ lạc giữa chốn quá thân thuộc.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Nhân vật nhận ra dấu chân mình đang đi theo chính là dấu chân của mình từ đêm hôm trước.
- Mô-típ tham khảo: Mô-típ "ma dẫn đường/lạc đường" trong truyện làng quê; khác twist so với seed H011 (khúc sông đòi người).

**I07. Con Số Trên Cột Đình**
- Bối cảnh: Đình làng cũ, sân đất nện.
- Tiền đề: Cột đình làng có một hàng vạch khắc đếm số người mất trong xóm mỗi năm; năm nay vạch khắc đã vượt số người thật đã mất.
- Cốt lõi nỗi sợ: Con số biết trước thay vì ghi lại — nỗi sợ bị đếm trước khi kịp xảy ra.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật đếm lại vạch khắc lúc nửa đêm và thấy có thêm một vạch mới ngay khi đang đếm.
- Mô-típ tham khảo: Biến thể mô-típ "sổ sinh tử/con số định mệnh"; giữ phần dự báo, bỏ hẳn yếu tố bói toán/nghi lễ.

**I08. Tiếng Ru Không Có Con Nít**
- Bối cảnh: Nhà tranh bỏ hoang cuối xóm.
- Tiền đề: Mỗi đêm mưa, xóm nhỏ nghe tiếng ru con vọng ra từ căn nhà đã bỏ hoang nhiều năm không ai ở.
- Cốt lõi nỗi sợ: Âm thanh gia đình ấm áp phát ra từ nơi không còn ai sống.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật bước vào nhà hoang tìm nguồn tiếng ru và nhận ra tiếng ru đang phát ra ngay trong căn phòng cô đang đứng — không loa, không người.
- Mô-típ tham khảo: "Âm thanh không nguồn gốc" — phổ biến ở cả truyện ma VN lẫn dòng animated lockdown của Dr. NoSleep (không gian quen hoá lạ).

### Chung cư / trọ đô thị (7 ý tưởng)

**U01. Căn Hộ Tầng Không Có Số**
- Bối cảnh: Chung cư cũ giữa hẻm phố, không tên thành phố thật.
- Tiền đề: Chung cư cũ có một tầng không hiện trên bảng điều khiển thang máy, nhưng thang máy vẫn đôi khi dừng ở đó.
- Cốt lõi nỗi sợ: Nút bấm cho tầng không tồn tại bỗng sáng lên dù không ai bấm.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Thang máy mở cửa ở "tầng đó" đúng lúc nhân vật một mình; hành lang y hệt tầng của cô nhưng cửa nhà cô lại đóng kín từ bên trong.
- Mô-típ tham khảo: Biến thể "tầng bí ẩn thang máy" — gần với các "school lockdown" của Dr. NoSleep (không gian quen thuộc hoá lạ).

**U02. Người Hàng Xóm Không Bao Giờ Ra Cửa**
- Bối cảnh: Chung cư tầng trung, hành lang hẹp.
- Tiền đề: Căn hộ đối diện luôn sáng đèn, luôn có tiếng ti vi, nhưng chưa ai từng thấy người ở đó bước ra ngoài suốt nhiều năm.
- Cốt lõi nỗi sợ: Sự hiện diện liên tục mà không có sự sống — nỗi sợ về thói quen lặp lại vô hồn.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật gõ cửa và nghe chính giọng nói của mình vọng ra chào đáp lại.
- Mô-típ tham khảo: Mô-típ "hàng xóm bí ẩn" phổ biến trong loạt "Apartment/New Home Horror Stories" của Mr. Nightmare.

**U03. Ba Lần Gõ Cửa Sau Lưng**
- Bối cảnh: Căn hộ studio nhỏ tầng cao.
- Tiền đề: Một cô gái sống một mình bắt đầu nghe ba tiếng gõ cửa sau lưng mỗi khi đang quay lưng lại cửa chính.
- Cốt lõi nỗi sợ: Âm thanh luôn đến từ phía không thể nhìn thấy.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Tiếng gõ chuyển từ sau cửa sang từ bên trong tủ quần áo cô đang đứng dựa vào.
- Mô-típ tham khảo: Quy tắc "tiếng gõ ba nhịp" trong narration-style.md, kết hợp mô-típ "home alone horror" của Mr. Nightmare.

**U04. Sổ Ghi Nợ Của Người Thuê Trước**
- Bối cảnh: Dãy trọ cũ trong hẻm, phòng cho thuê giá rẻ.
- Tiền đề: Người thuê phòng mới tìm thấy một cuốn sổ ghi nợ cũ dưới sàn gỗ; mỗi khoản nợ đều đã "trả" bằng một ngày tháng trùng với ngày mất của ai đó trong toà nhà.
- Cốt lõi nỗi sợ: Món nợ không tính bằng tiền mà bằng thời gian sống còn lại.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật thấy tên mình được thêm vào sổ, cạnh một ô ngày tháng còn bỏ trống.
- Mô-típ tham khảo: Vật để lại của người thuê trước — đổi hẳn sang cuốn sổ (khác vật thể "gương" ở seed H001) để tránh trùng.

**U05. Đồng Hồ Sảnh Chung Cư Chạy Chậm Một Phút**
- Bối cảnh: Sảnh chung cư cũ, không tên toà nhà thật.
- Tiền đề: Đồng hồ treo ở sảnh chung cư luôn chậm đúng một phút so với mọi đồng hồ khác; cư dân dần nhận ra một phút đó trùng khoảnh khắc có người trong toà nhà qua đời.
- Cốt lõi nỗi sợ: Một phút lệch nhịp giữa "giờ chung cư" và giờ thật.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật đứng nhìn đồng hồ sảnh nhảy thêm một phút đúng lúc điện thoại cô đổ chuông báo tin dữ.
- Mô-típ tham khảo: "Thời gian lệch/đồng hồ báo điềm" — chuyển hoá kiểu "found footage bất thường" của Chilling Scares thành một chi tiết sai lệch nhỏ, đúng văn phong kênh.

**U06. Ban Công Tầng Trên Không Có Người Ở**
- Bối cảnh: Chung cư cũ, ban công đối diện nhau qua giếng trời.
- Tiền đề: Mỗi tối, đồ phơi trên ban công tầng trên rung nhẹ như có ai đang phơi đồ, dù căn hộ đó đã bỏ trống nhiều tháng.
- Cốt lõi nỗi sợ: Chuyển động đời thường (phơi đồ) diễn ra ở nơi không ai sống.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Một chiếc áo lạ xuất hiện trên dây phơi nhà nhân vật — đúng chiếc áo cô thấy "bay" trên ban công trống đêm hôm trước.
- Mô-típ tham khảo: "Chuyển động đời thường ở nơi vắng người" — biến thể nhẹ nhàng của "school lockdown" và "found footage", không có cảnh giật gân.

**U07. Chuông Báo Cháy Kêu Một Mình**
- Bối cảnh: Tầng hầm giữ xe chung cư.
- Tiền đề: Chuông báo cháy tầng hầm kêu vào đúng ba giờ mười lăm sáng mỗi ngày, dù kỹ thuật viên kiểm tra không tìm ra nguyên nhân.
- Cốt lõi nỗi sợ: Một hệ thống hiện đại (chuông báo cháy) trở thành phương tiện cho điềm báo cũ.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Chuông reo đúng giờ ngay khi nhân vật đang đứng một mình trong hầm; đèn khẩn cấp chỉ sáng đúng lối dẫn tới một góc tường bị bịt kín.
- Mô-típ tham khảo: Kết hợp mô-típ "báo động vô cớ" đô thị hiện đại với quy tắc kênh: chỉ gợi qua bóng tối/âm thanh, không hiện hình quái vật.

### Ca đêm / công việc khuya (7 ý tưởng)

**N01. Ca Trực Gác Cổng Nhà Máy Đêm** — *có yếu tố cần cân nhắc thêm*
- Bối cảnh: Nhà máy nhỏ ngoại ô hư cấu, cổng sắt, đèn cao áp.
- Tiền đề: Bảo vệ ca đêm ở một nhà máy hư cấu nhận bàn giao ca với lời dặn kỳ lạ: đừng bao giờ trả lời nếu có người gõ cổng sau sau nửa đêm.
- Cốt lõi nỗi sợ: Một quy tắc bàn giao ca không ai giải thích lý do.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Tiếng gõ cổng sau vang lên đúng nhịp mà người bảo vệ trước đã dặn, trong khi camera an ninh cho thấy cổng sau vẫn đóng kín.
- Mô-típ tham khảo: Gần với dòng "rules-based horror" quốc tế (kiểu Viidith22 được nhắc trong nghiên cứu creepypasta), viết lại hoàn toàn mới bằng lời kể, không trình bày như danh sách quy tắc để tránh giống hướng dẫn làm theo.
- ⚠️ Lưu ý khi viết: Không được viết dưới dạng liệt kê "quy tắc" tách khỏi mạch truyện — chỉ kể lại như một phần lời dặn trong câu chuyện, để không bị hiểu là rủ người xem làm theo.

**N02. Trực Tổng Đài Cuộc Gọi Không Số**
- Bối cảnh: Phòng trực tổng đài nhỏ, một chiếc điện thoại bàn cũ.
- Tiền đề: Nhân viên trực tổng đài đêm của một hãng taxi hư cấu nhận được cuộc gọi đặt xe từ một số không tồn tại, đến đúng một địa chỉ mỗi đêm.
- Cốt lõi nỗi sợ: Một cuộc gọi lặp lại, luôn cùng giờ, không ai bắt máy khi gọi lại.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật quyết định không bắt máy đêm đó; sáng hôm sau thấy chính số điện thoại của mình hiện trong danh sách cuộc gọi đến.
- Mô-típ tham khảo: Biến thể mô-típ "Disturbing Recordings/Phone Calls" của Lazy Masquerade, viết thành truyện gốc hoàn toàn mới.

**N03. Người Trực Đêm Ở Trạm Xăng Cuối Đường**
- Bối cảnh: Trạm xăng ven đường vắng, hư cấu.
- Tiền đề: Nhân viên mới vào ca đêm ở một trạm xăng ven quốc lộ hư cấu nhận ra một chiếc xe tải luôn dừng đổ xăng đúng hai giờ sáng, và bình xăng xe không bao giờ đầy dù đổ bao lâu.
- Cốt lõi nỗi sợ: Một hành động lặp lại (đổ xăng) không bao giờ hoàn tất.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật nhìn theo gương chiếu hậu của xe tải khi nó rời đi và thấy ghế lái trống không, vô lăng tự xoay.
- Mô-típ tham khảo: "Gas station horror" xuất hiện ở cả MrCreepyPasta (Tales from the Gas Station) và Mr. Nightmare; viết lại bối cảnh và nhân vật hoàn toàn mới.

**N04. Ca Trực Kho Lạnh Xuyên Đêm**
- Bối cảnh: Kho lạnh của một cơ sở chế biến thực phẩm hư cấu.
- Tiền đề: Nhân viên kho lạnh ca đêm phát hiện nhiệt kế kho luôn tụt thêm vài độ mỗi khi anh rời khỏi phòng giám sát, dù kho đã cài đặt cố định.
- Cốt lõi nỗi sợ: Một chỉ số kỹ thuật khách quan (nhiệt độ) trở thành dấu hiệu có ai đó đang ở trong kho.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Camera giám sát ghi lại hình một bóng người đứng giữa kho đúng lúc lạnh nhất, nhưng khi anh chạy vào kho trống không, chỉ có hơi thở đọng thành khói ngay trước mặt anh.
- Mô-típ tham khảo: Chuyển hoá "found footage bất thường" (Chilling Scares) thành chi tiết cảm giác lạnh — đúng yêu cầu văn phong kênh.

**N05. Người Gác Thang Máy Bệnh Viện Ca Ba**
- Bối cảnh: Khu nhà phụ cũ của một bệnh viện hư cấu.
- Tiền đề: Nhân viên vận hành thang máy chở hàng ca ba ở một bệnh viện hư cấu nhận ra thang máy đôi khi tự dừng ở tầng đã đóng cửa từ nhiều năm.
- Cốt lõi nỗi sợ: Một không gian từng có sự sống nay chỉ còn thang máy nhớ đường.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Cửa thang máy mở ở tầng đóng, hành lang tối om, và một giọng rất khẽ gọi đúng chức danh công việc của nhân vật — không gọi tên.
- Mô-típ tham khảo: "Hospital lockdown horror" (Dr. NoSleep) viết lại chậm rãi, không có cảnh nguy hiểm thể chất.

**N06. Ca Trực Quán Net Xuyên Đêm**
- Bối cảnh: Quán net nhỏ trong hẻm, ánh đèn neon xanh.
- Tiền đề: Nhân viên trông quán net ca đêm nhận thấy một máy tính ở góc khuất luôn tự bật dù đã tắt nguồn, màn hình chỉ hiện một cửa sổ chat trống.
- Cốt lõi nỗi sợ: Công nghệ hiện đại (máy tính, tin nhắn) làm phương tiện cho một điều cũ.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Cửa sổ chat gõ ra đúng một dòng chữ — tên thật của nhân vật, điều không khách nào từng biết.
- Mô-típ tham khảo: Hiện đại hoá công cụ giao tiếp thành điềm báo (gần "Online Dating Horror Stories" của Mr. Nightmare), chuyển hẳn sang bối cảnh Việt hoá.

**N07. Người Trông Xe Bãi Đêm Ký Túc Xá**
- Bối cảnh: Bãi xe khu ký túc xá, ánh đèn cao áp vàng.
- Tiền đề: Người trông giữ xe ca đêm của một khu ký túc xá hư cấu đếm số xe mỗi đêm, và một đêm con số dư ra đúng một chiếc không ai nhận.
- Cốt lõi nỗi sợ: Một con số không khớp giữa sổ ghi và thực tế.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Chiếc xe dư đó là chiếc xe của nhân vật, dù xe của anh vẫn đang đứng nguyên chỗ cũ.
- Mô-típ tham khảo: Mô-típ "đếm sai/nhân đôi" — chi tiết sai lệch nhỏ đúng chuẩn kênh, khác nhân vật/bối cảnh với seed H012.

### Bí mật gia đình (7 ý tưởng)

**F01. Chiếc Ghế Trống Đầu Mâm Cơm**
- Bối cảnh: Nhà cấp bốn trong xóm nhỏ.
- Tiền đề: Gia đình luôn dọn thêm một bát cơm và để trống một chiếc ghế đầu mâm mỗi bữa tối, nhưng không ai chịu giải thích vì sao.
- Cốt lõi nỗi sợ: Một nghi thức gia đình lặp đi lặp lại không rõ lý do.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Người con út phát hiện tên trên chiếc bát trống là tên của chính mình, viết bằng nét chữ của một người đã mất trước khi cô sinh ra.
- Mô-típ tham khảo: Đối lập có chủ đích với các tựa "giết vợ/giết chồng" đầy bạo lực của kênh domestic-crime-horror: giữ chủ đề tội lỗi gia đình nhưng bỏ hoàn toàn mô tả bạo lực.

**F02. Bức Ảnh Gia Đình Thiếu Một Người**
- Bối cảnh: Phòng khách nhà cũ, tường treo đầy ảnh qua các năm.
- Tiền đề: Mỗi năm gia đình chụp ảnh vào đúng một ngày cố định, và trong ảnh năm nay có một người đứng ở rìa khung hình mà không ai trong nhà nhận ra.
- Cốt lõi nỗi sợ: Sự xuất hiện âm thầm trong hình ảnh gia đình — chi tiết thị giác đúng chất kênh.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật lật lại ảnh những năm trước và thấy cùng một bóng người xuất hiện ở rìa mỗi tấm, ngày một gần hơn.
- Mô-típ tham khảo: "Ảnh gia đình có người lạ" (creepy photo backstory của Lazy Masquerade) viết lại hoàn toàn theo bối cảnh gia đình Việt.

**F03. Lá Thư Không Bao Giờ Gửi Của Bà**
- Bối cảnh: Căn nhà gỗ cũ của gia đình nhiều thế hệ.
- Tiền đề: Sau khi bà mất, cháu gái tìm thấy một chồng thư bà viết đều đặn mỗi tháng suốt hai mươi năm, gửi cho một người trong nhà chưa ai từng nghe tên.
- Cốt lõi nỗi sợ: Một bí mật giữ kín bằng thói quen viết thư đều đặn.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Lá thư cuối cùng, chưa kịp gửi, ghi đúng ngày cháu gái sinh ra — và tên người nhận chính là tên cháu.
- Mô-típ tham khảo: Phiên bản chậm rãi, đối lập các tựa gây sốc kiểu "con dâu độc ác": giữ oan khuất gia đình nhưng qua sự im lặng, không qua tội ác mô tả cụ thể.

**F04. Cỗ Giỗ Không Ai Nhớ Ngày**
- Bối cảnh: Nhà thờ họ nhỏ trong làng.
- Tiền đề: Mỗi năm nhà nội tổ chức một cỗ giỗ vào ngày không trùng với ngày mất của ai trong gia phả mà người lớn tuổi nhất còn nhớ được.
- Cốt lõi nỗi sợ: Một lễ giỗ dành cho người không ai xác nhận từng tồn tại.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Nhân vật lật gia phả cũ và thấy trang ghi tên người được giỗ đã bị xé, chỉ còn lại nét mực loang đúng hình dáng một bàn tay.
- Mô-típ tham khảo: Biến thể gia đình của mô-típ "con số định mệnh"; giữ tôn trọng tín ngưỡng thờ cúng theo đúng narration-style.md, bàn thờ/giỗ chạp chỉ là bối cảnh chứ không bị biến thành yếu tố đáng sợ trực tiếp.

**F05. Tủ Quần Áo Khóa Kín Của Người Anh Cả** — *có yếu tố cần cân nhắc thêm*
- Bối cảnh: Căn phòng nhỏ cuối nhà, ít người lai vãng.
- Tiền đề: Gia đình cấm ngặt không ai được mở tủ quần áo cũ của người anh cả đã đi xa nhiều năm không tin tức, dù đồ đạc trong nhà đã dọn hết.
- Cốt lõi nỗi sợ: Một món đồ bị cấm chạm vào mà không ai giải thích rõ vì sao.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật mở tủ trong đêm mưa và thấy quần áo bên trong vẫn còn ấm, như vừa có người cởi ra.
- Mô-típ tham khảo: "Căn phòng/tủ đồ cấm" phổ biến trong cả truyện trọ VN và "haunted house" quốc tế; giữ bí ẩn gia đình, không có chi tiết bạo lực.
- ⚠️ Lưu ý khi viết: Lý do người anh cả vắng mặt phải giữ mơ hồ; không gợi ý anh ta chết do tự hại hay bị sát hại — chỉ để là một bí mật chưa kể.

**F06. Cuốn Gia Phả Tự Thêm Tên**
- Bối cảnh: Tủ thờ nhà từ đường.
- Tiền đề: Cuốn gia phả gia đình lưu qua nhiều đời có những trang cuối luôn để trống, nhưng mỗi lần giở lại, một cái tên mới đã lặng lẽ xuất hiện.
- Cốt lõi nỗi sợ: Chữ viết xuất hiện mà không ai cầm bút.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật thấy tên của chính con mình đã có sẵn trong gia phả, dù đứa bé còn chưa chào đời.
- Mô-típ tham khảo: Biến thể gia đình của mô-típ "sổ sách tự viết/tự thêm tên" (song song ý tưởng I07), khai thác nỗi sợ về số phận đã định trước.

**F07. Chiếc Nôi Cũ Trên Gác Mái**
- Bối cảnh: Gác mái nhà cổ, nhiều đồ cũ phủ bụi.
- Tiền đề: Nhà có một chiếc nôi gỗ cũ cất trên gác mái từ trước khi nhân vật ra đời, không ai trong nhà từng dùng đến, cũng không ai nói rõ vì sao vẫn giữ nó.
- Cốt lõi nỗi sợ: Một vật dụng gắn với trẻ nhỏ nhưng cả nhà tránh nhắc tới.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Đêm nhân vật lên gác mái dọn dẹp, chiếc nôi đang đung đưa nhẹ dù không có gió, và có một vệt lõm ấm trên đệm nôi.
- Mô-típ tham khảo: "Vật thể trẻ em bị bỏ quên" — đổi hẳn vật thể so với búp bê ở seed H015 (nôi thay búp bê) và động cơ (giữ bí mật gia đình, không phải món quà).

### Đường xa / lữ hành (7 ý tưởng)

**R01. Chuyến Xe Đêm Không Trả Khách**
- Bối cảnh: Xe khách liên tỉnh hư cấu, quốc lộ đêm.
- Tiền đề: Một chuyến xe khách tuyến đêm luôn có đúng một ghế trống dù vé đã bán hết, và tài xế không bao giờ dừng đúng bến cuối ghi trên vé.
- Cốt lõi nỗi sợ: Một hành trình không bao giờ đến đích như đã hứa.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Nhân vật nhìn ra cửa sổ và thấy phong cảnh bên ngoài lặp lại y hệt đoạn đường đã qua cách đây một giờ.
- Mô-típ tham khảo: Mô-típ "xe khách ma", khác seed H014 ở chỗ khai thác vòng lặp không gian thay vì hành khách kỳ lạ; gần "Travel/Stranded Horror Stories" của Mr. Nightmare.

**R02. Trạm Dừng Chân Không Có Đèn**
- Bối cảnh: Trạm dừng ven quốc lộ, quán nước nhỏ.
- Tiền đề: Một trạm dừng chân ven quốc lộ hư cấu luôn tắt điện đúng lúc có xe ghé vào nghỉ, dù các trạm khác quanh đó vẫn sáng bình thường.
- Cốt lõi nỗi sợ: Bóng tối chọn lọc — chỉ tắt đúng nơi có người.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Nhân vật bật đèn pin và thấy tất cả ghế trong quán đã quay mặt về phía mình, dù lúc bước vào chúng còn xếp ngay ngắn.
- Mô-típ tham khảo: "Rest Area Horror Stories" (Mr. Nightmare) viết lại hoàn toàn bằng bối cảnh và nhân vật Việt hoá.

**R03. Người Quá Giang Xin Xuống Đúng Cây Số Cũ**
- Bối cảnh: Quốc lộ vắng giữa hai thị trấn hư cấu.
- Tiền đề: Một tài xế xe tải đường dài thường cho người lạ quá giang, và nhận ra người quá giang đêm nay xin dừng đúng chỗ tháng trước từng có một người khác cũng xin xuống y hệt.
- Cốt lõi nỗi sợ: Sự lặp lại của một yêu cầu tưởng như ngẫu nhiên.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Tài xế nhìn gương chiếu hậu sau khi người quá giang xuống xe và thấy ghế sau vẫn còn một vệt ướt hình người, dù trời không mưa.
- Mô-típ tham khảo: Mô-típ quốc tế "phantom hitchhiker" (người quá giang biến mất), viết lại theo văn hoá đường dài Việt Nam.

**R04. Biển Báo Đếm Ngược Sai Số Km**
- Bối cảnh: Quốc lộ hai làn xe giữa đồng không mông quạnh.
- Tiền đề: Một biển báo khoảng cách trên quốc lộ hư cấu ghi số km giảm dần mỗi lần nhân vật đi qua, dù quãng đường thực tế không hề thay đổi.
- Cốt lõi nỗi sợ: Một con số kỹ thuật trở nên phi lý — dấu hiệu không gian đang "giữ" người lại.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Biển báo cuối cùng ghi số không, và con đường phía trước đột nhiên là đoạn đường nhân vật đã khởi hành từ đầu tối.
- Mô-típ tham khảo: Biến thể mô-típ "vòng lặp đường đi" (song song ý tưởng I06) trong bối cảnh lữ hành xa nhà, gần "Foreign Country/Travel Horror Stories" của Mr. Nightmare.

**R05. Ga Tàu Nhỏ Không Có Trong Lịch Trình**
- Bối cảnh: Tuyến tàu hoả đường dài hư cấu, ga xép giữa rừng.
- Tiền đề: Một chuyến tàu đêm bất ngờ dừng ở một ga xép không có tên trong lịch trình, và chỉ một mình nhân vật nhìn thấy sân ga đó qua cửa sổ.
- Cốt lõi nỗi sợ: Một điểm dừng chỉ hiện ra với riêng một người.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật hỏi người soát vé về ga đó và được cho xem lịch trình cũ — ga xép ấy từng tồn tại, đã đóng cửa đúng vào năm nhân vật sinh ra.
- Mô-típ tham khảo: "Ga tàu ẩn/bến xe ma" — đổi phương tiện di chuyển (tàu hoả thay xe khách) để tránh trùng các seed xe cộ đã có.

**R06. Người Lái Taxi Đêm Không Bật Đồng Hồ Tính Tiền**
- Bối cảnh: Trong xe taxi, phố vắng ban đêm hư cấu.
- Tiền đề: Một tài xế taxi công nghệ nhận cuốc xe lúc nửa đêm; khách lên xe không nói địa chỉ nhưng đồng hồ tính tiền tự chạy, tự tính đúng số tiền của một cuốc trước đó tài xế từng chở.
- Cốt lõi nỗi sợ: Công nghệ (đồng hồ tính tiền, ứng dụng gọi xe) lặp lại một chuyến đi cũ.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Tài xế nhìn gương chiếu hậu và nhận ra khuôn mặt hành khách chính là khuôn mặt mình từng thấy trong gương một năm trước, đêm anh suýt gặp tai nạn.
- Mô-típ tham khảo: Hiện đại hoá mô-típ "phantom passenger" bằng công nghệ gọi xe, khác biệt rõ với seed H014 (xe khách truyền thống).

**R07. Cột Km Cuối Cùng Trước Khi Trời Sáng**
- Bối cảnh: Đường đèo vắng hư cấu, sương mù dày.
- Tiền đề: Một phượt thủ đi xe máy xuyên đêm nhận ra mỗi khi trời sắp sáng, quãng đường còn lại luôn đúng bằng khoảng cách anh đã đi được, như thể đêm không muốn kết thúc.
- Cốt lõi nỗi sợ: Thời gian và khoảng cách không khớp nhau — đêm tự kéo dài.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Mặt trời cuối cùng cũng lên, nhưng ánh sáng chỉ soi rõ một đoạn đường ngắn phía trước, còn lại vẫn chìm trong một lớp sương không tan.
- Mô-típ tham khảo: "Đêm không kết thúc" — kết hợp giữa dòng Travel Horror quốc tế và không khí chậm rãi kiểu slow_burn của kênh.

### Vật bị nguyền (7 ý tưởng)

**C01. Chiếc Radio Bắt Được Đài Cũ**
- Bối cảnh: Căn phòng trọ nhỏ, không gian đô thị hư cấu.
- Tiền đề: Một chiếc radio cũ mua ở tiệm đồ si đôi khi tự bắt được một đài phát thanh phát đi phát lại bản tin của nhiều năm trước, đọc đúng tên người sắp gặp chuyện chẳng lành.
- Cốt lõi nỗi sợ: Một thiết bị cũ "phát lại" thời gian đã qua.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Bản tin đọc đúng tên và địa chỉ của nhân vật, ở thì tương lai chưa xảy ra.
- Mô-típ tham khảo: Vật cũ mang điềm báo (đổi cơ chế so với "bàn tay khô ba điều ước" ở seed H006 — dùng âm thanh thay vì điều ước); gần "Disturbing Recordings" của Lazy Masquerade.

**C02. Bộ Cờ Tướng Thiếu Một Quân**
- Bối cảnh: Quán nước vỉa hè cũ, sân nhà hàng xóm.
- Tiền đề: Một bộ cờ tướng gia truyền luôn thiếu đúng một quân, và ai chơi ván cờ cuối cùng với bộ cờ đủ quân đều gặp chuyện không hay ngay sau đó.
- Cốt lõi nỗi sợ: Một trò chơi tưởng vô hại trở thành lời tiên tri.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật tìm thấy quân cờ còn thiếu giấu trong tường nhà, khắc tên người đã mất từ ván cờ trước.
- Mô-típ tham khảo: "Đồ vật cũ mang lời nguyền" viết mới hoàn toàn, không hướng dẫn cách chơi hay nghi thức nào.

**C03. Áo Mưa Không Bao Giờ Khô**
- Bối cảnh: Nhà kho sau vườn, xóm nhỏ.
- Tiền đề: Chiếc áo mưa cũ treo sau cửa nhà kho luôn ướt sũng dù trời nắng ráo cả tuần, và giọt nước nhỏ xuống đúng nhịp như bước chân ai đó đi bộ ngoài mưa.
- Cốt lõi nỗi sợ: Một vật dụng "giữ" lại thời tiết của một đêm mưa đã qua từ lâu.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Nhân vật mặc thử áo mưa và cảm nhận cái lạnh thấm dần như đang đứng giữa cơn mưa năm nào, dù trời đang nắng.
- Mô-típ tham khảo: "Vật giữ ký ức cảm giác" — khai thác chi tiết cảm giác vật lý (nhiệt độ, độ ẩm) đúng yêu cầu narration-style.md, không máu me, không tự hại.

**C04. Cây Đàn Nguyệt Đứt Dây Đúng Giờ Ngọ**
- Bối cảnh: Phòng thờ trong nhà cổ.
- Tiền đề: Cây đàn nguyệt cũ của ông nội luôn tự đứt một dây đúng giờ ngọ mỗi ngày giỗ, dù dây đàn đã thay mới nhiều lần.
- Cốt lõi nỗi sợ: Một nhạc cụ "nhắc" đúng giờ giấc mà không ai lên dây.
- Không khí: folk (Dân gian u uất)
- Gợi ý cao trào: Nhân vật chơi thử cây đàn vào đúng giờ ngọ và nghe được một đoạn nhạc lạ, không phải bài ông nội từng dạy, phát ra từ chính cây đàn.
- Mô-típ tham khảo: Biến thể mô-típ "nhạc cụ bị nguyền" (song song sáo xương ở seed H009) nhưng đổi nhạc cụ, bối cảnh gia đình và cơ chế thời gian thay vì không gian.

**C05. Khung Ảnh Rỗng Trong Phòng Khách**
- Bối cảnh: Phòng khách nhà phố cũ.
- Tiền đề: Nhà có một khung ảnh treo tường luôn để trống, gia đình giải thích qua loa là "khung dự phòng", nhưng không ai dám lau bụi mặt kính khung ảnh đó.
- Cốt lõi nỗi sợ: Một khung trống chờ được lấp đầy — nỗi sợ về việc "ai đó sẽ vào khung".
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Nhân vật vô tình chụp ảnh cả nhà; khi rửa ảnh ra, khung ảnh trống trên tường đã có hình — hình một người trong nhà, chụp từ góc không ai đứng được.
- Mô-típ tham khảo: Phái sinh có kiểm soát từ mô-típ gương ở seed H001: đổi cơ chế (khung ảnh thay gương) và thời điểm xuất hiện khác biệt rõ rệt.

**C06. Đôi Guốc Gỗ Không Vừa Chân Ai**
- Bối cảnh: Hiên nhà, tủ giày ngoài cửa.
- Tiền đề: Đôi guốc gỗ cũ trong tủ giày nhà luôn xuất hiện lại đúng vị trí cũ dù đã đem cho hoặc vứt đi nhiều lần, và không ai trong nhà nhớ rõ đã mua nó từ khi nào.
- Cốt lõi nỗi sợ: Một vật không chịu rời đi.
- Không khí: slow_burn (Rợn chậm)
- Gợi ý cao trào: Nhân vật mang guốc ra bãi rác lúc nửa đêm, quay về nhà thì thấy guốc đã nằm sẵn ngay trước cửa phòng ngủ, còn ướt sương như vừa có người mang về.
- Mô-típ tham khảo: Mô-típ quốc tế "cursed/returning object" (gần khung "disturbing object" của Lazy Masquerade), bản địa hoá bằng vật dụng Việt (guốc gỗ).

**C07. Chiếc Chuông Gió Không Cần Gió**
- Bối cảnh: Hiên nhà cấp bốn, sân nhỏ trồng cây.
- Tiền đề: Chiếc chuông gió treo hiên nhà kêu leng keng ngay cả những đêm lặng gió nhất, và tiếng chuông luôn dừng đúng lúc có người bước ra nhìn.
- Cốt lõi nỗi sợ: Âm thanh chỉ tồn tại khi không ai quan sát trực tiếp.
- Không khí: tense (Căng thẳng dồn dập)
- Gợi ý cao trào: Nhân vật đứng nấp sau cửa nhìn trộm và thấy chuông gió tự xoay tròn, như có bàn tay vô hình giữ lấy nó ngay khi ngừng kêu.
- Mô-típ tham khảo: "Âm thanh ngừng khi bị quan sát" — bám sát chỉ dẫn narration-style.md về chi tiết cảm giác âm thanh, tránh xa các "disturbing object" mô tả bạo lực.

### Tâm lý / ám ảnh nội tâm (7 ý tưởng)

**P01. Cuốn Nhật Ký Viết Trước Một Ngày**
- Bối cảnh: Căn phòng trọ nhỏ, bàn học kê sát cửa sổ.
- Tiền đề: Một người phụ nữ phát hiện cuốn nhật ký của mình luôn tự ghi lại chuyện của ngày mai trước khi nó xảy ra, bằng chính nét chữ của cô.
- Cốt lõi nỗi sợ: Ranh giới giữa ký ức và tiên tri bị xoá nhoà — nhân vật không chắc mình đang sống hay đang đọc lại.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Trang nhật ký "ngày mai" bỏ trống lần đầu tiên, và cô nhận ra đó là dấu hiệu cô sẽ không còn ở đó để viết tiếp.
- Mô-típ tham khảo: "Văn bản tự viết/tiên tri" ở góc độ cá nhân (song song ý tưởng F06), hướng hẳn sang nghi ngờ nhận thức bản thân theo đúng mood psychological.

**P02. Người Trong Gương Không Chớp Mắt Cùng Lúc**
- Bối cảnh: Căn hộ một mình, phòng tắm hẹp.
- Tiền đề: Một cô gái nhận ra hình mình trong gương phòng tắm luôn chớp mắt chậm hơn cô đúng nửa giây, một khoảng lệch chỉ cô nhận ra.
- Cốt lõi nỗi sợ: Sự lệch pha rất nhỏ giữa bản thân và hình phản chiếu.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Một đêm hình trong gương không chớp mắt theo cô nữa mà đứng yên nhìn thẳng, trong khi cô vẫn đang chớp mắt liên tục.
- Mô-típ tham khảo: Biến thể có kiểm soát của mô-típ gương (khác cơ chế "tiếng gõ" ở seed H001, dùng độ trễ chuyển động) — đúng chuẩn "chi tiết sai lệch nhỏ" của narration-style.md.

**P03. Danh Sách Việc Cần Làm Tự Gạch Bỏ**
- Bối cảnh: Căn hộ nhỏ, góc làm việc tại nhà.
- Tiền đề: Một nhân viên văn phòng có thói quen viết danh sách việc cần làm mỗi sáng, và gần đây một số việc anh chưa làm đã tự động bị gạch ngang trước khi anh kịp hoàn thành.
- Cốt lõi nỗi sợ: Một công cụ quản lý thời gian trở thành nơi mất kiểm soát.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Dòng cuối cùng trong danh sách hôm nay ghi đúng tên anh, đã bị gạch ngang từ trước khi anh thức dậy.
- Mô-típ tham khảo: Hiện đại hoá mô-típ "văn bản tự viết" (song song P01, F06) bằng công cụ đời thường (to-do list), giữ mood psychological với kết mở.

**P04. Ba Cuộc Hẹn Cà Phê Giống Hệt Nhau**
- Bối cảnh: Quán cà phê góc phố hư cấu.
- Tiền đề: Một người đàn ông nhận ra ba lần hẹn gặp bạn cũ tại cùng một quán cà phê đều diễn ra giống hệt nhau đến từng câu nói, như thể thời gian đang lặp một đoạn ngắn.
- Cốt lõi nỗi sợ: Cảm giác quen thuộc đến kỳ lạ kéo dài thành một vòng lặp có thật.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Lần thứ tư, người bạn cũ bước vào quán nhưng lại nói một câu hoàn toàn khác — câu duy nhất khác biệt là lời từ biệt.
- Mô-típ tham khảo: Mô-típ "vòng lặp thời gian" liên hệ tới thể loại chuyện lạ phổ biến ở kênh phương Tây, viết lại thuần Việt, không dùng thuật ngữ nước ngoài.

**P05. Tiếng Bước Chân Chỉ Nghe Khi Đang Ngủ** — *có yếu tố cần cân nhắc thêm*
- Bối cảnh: Căn phòng ngủ nhỏ trong nhà trọ.
- Tiền đề: Một người chỉ nghe thấy tiếng bước chân quanh giường mình đúng lúc anh chắc chắn mình đang mơ, và mỗi giấc mơ đó lại nhớ rõ hơn giấc trước.
- Cốt lõi nỗi sợ: Ranh giới giữa giấc mơ và thực tại bị bào mòn dần.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Anh tỉnh dậy giữa đêm, chắc chắn mình đã thức, nhưng tiếng bước chân vẫn tiếp tục vòng quanh giường.
- Mô-típ tham khảo: "Bóng đè/giấc mơ xâm lấn" — phái sinh có kiểm soát từ seed H012, đổi bối cảnh và cơ chế (nhớ giấc mơ tăng dần) để tránh trùng lặp.
- ⚠️ Lưu ý khi viết: Cần viết khác biệt rõ với seed H012 (bóng đè ký túc xá) về cơ chế và không khí, tránh cảm giác làm lại cùng một truyện.

**P06. Người Bạn Chỉ Xuất Hiện Trong Ảnh Chụp Chung**
- Bối cảnh: Văn phòng nhỏ, các buổi liên hoan công ty.
- Tiền đề: Một cô gái luôn thấy một người bạn thân trong mọi bức ảnh nhóm chụp gần đây, nhưng không đồng nghiệp nào cô hỏi nhớ ra người đó từng có mặt.
- Cốt lõi nỗi sợ: Sự tồn tại chỉ được xác nhận qua hình ảnh, không qua ký ức người khác.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Cô lục lại ảnh cũ nhất có người bạn đó và nhận ra khuôn mặt trong ảnh, dù mờ, lại chính là khuôn mặt cô hồi nhỏ.
- Mô-típ tham khảo: Biến thể mô-típ "ảnh có người lạ" (song song F02) đẩy sang câu hỏi về danh tính bản thân, đúng đặc trưng "cú lật đổi cách hiểu toàn bộ" của mood psychological.

**P07. Tin Nhắn Thoại Từ Số Của Mẹ Đã Đổi**
- Bối cảnh: Căn hộ một mình, buổi tối sau giờ làm.
- Tiền đề: Một người nhận được tin nhắn thoại từ số điện thoại cũ của mẹ mình, nội dung là một cuộc trò chuyện họ từng có, nhưng câu trả lời của người con trong tin nhắn lại khác với những gì cô nhớ mình đã nói.
- Cốt lõi nỗi sợ: Ký ức cá nhân bị một phiên bản khác của chính nó thách thức.
- Không khí: psychological (Ám ảnh tâm lý)
- Gợi ý cao trào: Cô gọi lại số đó và nghe chính giọng mình trả lời, đúng câu mà tin nhắn thoại kia đã "sửa lại".
- Mô-típ tham khảo: Hiện đại hoá mô-típ "cuộc gọi/tin nhắn từ người thân" (gần "Disturbing Recordings" của Lazy Masquerade) theo hướng nghi ngờ trí nhớ, giữ kết mở.

## 5. Ý tưởng cần lưu ý thêm khi triển khai (borderline)

4 ý tưởng dưới đây vẫn nằm trong giới hạn chính sách hiện tại (đã kiểm bằng `horror/policy.py` lint, không phát hiện vi phạm) nhưng chạm tới vùng nhạy cảm hơn, cần người viết kịch bản cân nhắc kỹ khi triển khai thành hạt giống thật:

- **I05 — Bà Đỡ Không Ai Mời**: Chủ đề sinh nở/trẻ sơ sinh cần giữ mơ hồ, không gợi ý tổn hại tới mẹ hoặc trẻ.
- **N01 — Ca Trực Gác Cổng Nhà Máy Đêm**: Không được viết dưới dạng liệt kê "quy tắc" tách khỏi mạch truyện — chỉ kể lại như một phần lời dặn trong câu chuyện, để không bị hiểu là rủ người xem làm theo.
- **F05 — Tủ Quần Áo Khóa Kín Của Người Anh Cả**: Lý do người anh cả vắng mặt phải giữ mơ hồ; không gợi ý anh ta chết do tự hại hay bị sát hại — chỉ để là một bí mật chưa kể.
- **P05 — Tiếng Bước Chân Chỉ Nghe Khi Đang Ngủ**: Cần viết khác biệt rõ với seed H012 (bóng đè ký túc xá) về cơ chế và không khí, tránh cảm giác làm lại cùng một truyện.

## 6. Cách dùng tiếp

- File máy đọc đầy đủ: `sys/reports/horror-topics-50-20260924.json` (50 mục, đủ trường title/premise/setting/hook/mood/climax/pattern/borderline).
- Dữ liệu thô 240 tiêu đề thật: `sys/reports/horror-topics-raw-20260924.json`.
- Đây là bước nghiên cứu + phác thảo, **không tự thêm vào `horror/seeds.json`** vì việc đó cần người dùng chọn ý tưởng cụ thể trước (mỗi hạt giống cần `basis.type` rõ ràng — `public_domain`/`folklore`/`original` — và ít nhất 3 `dread` + `twist`, những phần này nên được viết kỹ hơn con số một-dòng ở đây trước khi đưa vào kho).
- Khi đã chọn được ý tưởng ưng ý, thêm hạt giống vào `horror/seeds.json` theo đúng định dạng trong `docs/horror.md`, rồi chạy `python3 horror/bank.py start <job>` như quy trình bình thường.

