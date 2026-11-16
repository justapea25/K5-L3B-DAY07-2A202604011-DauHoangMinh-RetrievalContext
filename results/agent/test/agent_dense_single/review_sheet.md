# Phiếu chấm — agent_dense_single (test)

Chấm trong `reviews.json`: `answer_grade` 0 = sai/thiếu evidence, 1 = đúng một phần, 2 = đúng và đủ (từ chối câu có đáp án = 0); `citation_support` = true nếu đoạn được trích thực sự hỗ trợ ý đã trả lời; câu thiếu evidence: `abstention_correct`.

## q16 · dieu_kien · status = `answered`

**Câu hỏi:** Người lao động nghỉ việc sau nhiều năm làm việc thì được trợ cấp thôi việc mỗi năm làm việc bao nhiêu?

**Đáp án chuẩn:** Mỗi năm làm việc được trợ cấp một nửa tháng tiền lương (nếu đã làm việc thường xuyên từ đủ 12 tháng trở lên).
- Evidence 1 (Điều 46, trang 11): “mỗi năm làm việc được trợ cấp một nửa tháng tiền lương”

**Agent trả lời:** Người lao động nghỉ việc sau nhiều năm làm việc sẽ được trợ cấp thôi việc mỗi năm làm việc là một nửa tháng tiền lương. Điều này áp dụng cho những người đã làm việc thường xuyên từ đủ 12 tháng trở lên và không thuộc các trường hợp đủ điều kiện hưởng lương hưu theo quy định của pháp luật về bảo hiểm xã hội hoặc các trường hợp khác theo quy định tại điểm e khoản 1 Điều 36 của Bộ luật này. Thời gian làm việc để tính trợ cấp thôi việc là tổng thời gian thực tế làm việc trừ đi thời gian tham gia bảo hiểm thất nghiệp và thời gian đã nhận trợ cấp thôi việc trước đó. Tiền lương để tính trợ cấp thôi việc là tiền lương bình quân của 06 tháng liền kề trước khi thôi việc.

**Tìm kiếm:** `trợ cấp thôi việc mỗi năm làm việc`
**Auto:** context chứa evidence 1/1 nhóm; 1 lượt tìm; 6.33 s; $0.000402

<details><summary>Citation 1: bllđ-2019:B:art046:0 (trang [11]) — chứa evidence chuẩn</summary>

```text
Điều 46. Trợ cấp thôi việc
1. Khi hợp đồng lao động chấm dứt theo quy định tại các khoản 1, 2, 3, 4, 6, 7, 9 và 10 Điều 34 của Bộ luật này thì người sử dụng lao động có trách nhiệm trả trợ cấp thôi việc cho người lao động đã làm việc thường xuyên cho mình từ đủ 12 tháng trở lên, mỗi năm làm việc được trợ cấp một nửa tháng tiền lương, trừ trường hợp đủ điều kiện hưởng lương hưu theo quy định của pháp luật về bảo hiểm xã hội và trường hợp quy định tại điểm e khoản 1 Điều 36 của Bộ luật này.
2. Thời gian làm việc để tính trợ cấp thôi việc là tổng thời gian người lao động đã làm việc thực tế cho người sử dụng lao động trừ đi thời gian người lao động đã tham gia bảo hiểm thất nghiệp theo quy định của pháp luật về bảo hiểm thất nghiệp và thời gian làm việc đã được người sử dụng lao động chi trả trợ cấp thôi việc, trợ cấp mất việc làm.
3. Tiền lương để tính trợ cấp thôi việc là tiền lương bình quân của 06 tháng liền kề theo hợp đồng lao động trước khi người lao động thôi việc.
4. Chính phủ quy định chi tiết Điều này.
```
</details>

---

## q17 · dieu_kien · status = `answered`

**Câu hỏi:** Công ty được tạm đình chỉ công việc của người lao động tối đa bao lâu, và trong thời gian đó người lao động được tạm ứng bao nhiêu lương?

**Đáp án chuẩn:** Không quá 15 ngày, trường hợp đặc biệt không quá 90 ngày; được tạm ứng 50% tiền lương.
- Evidence 1 (Điều 128, trang 27): “Thời hạn tạm đình chỉ công việc không được quá 15 ngày, trường hợp đặc biệt không được quá 90 ngày”

**Agent trả lời:** Công ty được tạm đình chỉ công việc của người lao động tối đa 15 ngày, trong trường hợp đặc biệt không quá 90 ngày. Trong thời gian tạm đình chỉ, người lao động được tạm ứng 50% tiền lương trước khi bị đình chỉ công việc. Hết thời hạn tạm đình chỉ, người sử dụng lao động phải nhận người lao động trở lại làm việc.

**Tìm kiếm:** `tạm đình chỉ công việc của người lao động tối đa bao lâu`
**Auto:** context chứa evidence 1/1 nhóm; 1 lượt tìm; 2.95 s; $0.000304

<details><summary>Citation 1: bllđ-2019:B:art128:0 (trang [27]) — chứa evidence chuẩn</summary>

```text
Điều 128. Tạm đình chỉ công việc
1. Người sử dụng lao động có quyền tạm đình chỉ công việc của người lao động khi vụ việc vi phạm có những tình tiết phức tạp nếu xét thấy để người lao động tiếp tục làm việc sẽ gây khó khăn cho việc xác minh. Việc tạm đình chỉ công việc của người lao động chỉ được thực hiện sau khi tham khảo ý kiến của tổ chức đại diện người lao động tại cơ sở mà người lao động đang bị xem xét tạm đình chỉ công việc là thành viên.
2. Thời hạn tạm đình chỉ công việc không được quá 15 ngày, trường hợp đặc biệt không được quá 90 ngày. Trong thời gian bị tạm đình chỉ công việc, người lao động được tạm ứng 50% tiền lương trước khi bị đình chỉ công việc. Hết thời hạn tạm đình chỉ công việc, người sử dụng lao động phải nhận người lao động trở lại làm việc.
3. Trường hợp người lao động bị xử lý kỷ luật lao động, người lao động cũng không phải trả lại số tiền lương đã tạm ứng.
4. Trường hợp người lao động không bị xử lý kỷ luật lao động thì được người sử dụng lao động trả đủ tiền lương cho thời gian bị tạm đình chỉ công việc.
```
</details>

---

## q18 · dien_dat_lai · status = `answered`

**Câu hỏi:** Một người mẹ sinh đôi thì được nghỉ thai sản tổng cộng bao lâu?

**Đáp án chuẩn:** 07 tháng (06 tháng + 01 tháng cho con thứ hai).
- Evidence 1 (Điều 139, trang 29): “Trường hợp lao động nữ sinh đôi trở lên thì tính từ con thứ 02 trở đi, cứ mỗi con, người mẹ được nghỉ thêm 01 tháng”

**Agent trả lời:** Một người mẹ sinh đôi sẽ được nghỉ thai sản tổng cộng là 06 tháng cho con đầu tiên và thêm 01 tháng cho mỗi con từ con thứ hai trở đi. Do đó, nếu sinh đôi, tổng thời gian nghỉ thai sản sẽ là 06 tháng + 01 tháng = 07 tháng.

**Tìm kiếm:** `nghỉ thai sản sinh đôi`
**Auto:** context chứa evidence 1/1 nhóm; 1 lượt tìm; 2.54 s; $0.000342

<details><summary>Citation 1: bllđ-2019:B:art139:0 (trang [29]) — chứa evidence chuẩn</summary>

```text
Điều 139. Nghỉ thai sản
1. Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng; thời gian nghỉ trước khi sinh không quá 02 tháng. Trường hợp lao động nữ sinh đôi trở lên thì tính từ con thứ 02 trở đi, cứ mỗi con, người mẹ được nghỉ thêm 01 tháng.
2. Trong thời gian nghỉ thai sản, lao động nữ được hưởng chế độ thai sản theo quy định của pháp luật về bảo hiểm xã hội.
3. Hết thời gian nghỉ thai sản theo quy định tại khoản 1 Điều này, nếu có nhu cầu, lao động nữ có thể nghỉ thêm một thời gian không hưởng lương sau khi thỏa thuận với người sử dụng lao động.
4. Trước khi hết thời gian nghỉ thai sản theo quy định tại khoản 1 Điều này, lao động nữ có thể trở lại làm việc khi đã nghỉ ít nhất được 04 tháng nhưng người lao động phải báo trước, được người sử dụng lao động đồng ý và có xác nhận của cơ sở khám bệnh, chữa bệnh có thẩm quyền về việc đi làm sớm không có hại cho sức khỏe của người lao động. Trong trường hợp này, ngoài tiền lương của những ngày làm việc do người sử dụng lao động trả, lao động nữ vẫn tiếp tục được hưởng trợ cấp thai sản theo quy định của pháp luật về bảo hiểm xã hội.
5. Lao động nam khi vợ sinh con, người lao động nhận nuôi con nuôi dưới 06 tháng tuổi, lao động nữ mang thai hộ và người lao động là người mẹ nhờ mang thai hộ được nghỉ việc hưởng chế độ thai sản theo quy định của pháp luật về bảo hiểm xã hội.
```
</details>

---

## q19 · dien_dat_lai · status = `answered`

**Câu hỏi:** Nhân viên cưới vợ thì được nghỉ mấy ngày mà vẫn hưởng nguyên lương?

**Đáp án chuẩn:** 03 ngày.
- Evidence 1 (Điều 115, trang 24): “Kết hôn: nghỉ 03 ngày”

**Agent trả lời:** Nhân viên cưới vợ được nghỉ 03 ngày mà vẫn hưởng nguyên lương theo quy định tại Điều 115 của Bộ luật Lao động 2019.

**Tìm kiếm:** `nghỉ cưới vợ`
**Auto:** context chứa evidence 1/1 nhóm; 1 lượt tìm; 3.15 s; $0.000327

<details><summary>Citation 1: bllđ-2019:B:art115:0 (trang [24]) — chứa evidence chuẩn</summary>

```text
Điều 115. Nghỉ việc riêng, nghỉ không hưởng lương
1. Người lao động được nghỉ việc riêng mà vẫn hưởng nguyên lương và phải thông báo với người sử dụng lao động trong trường hợp sau đây:
a) Kết hôn: nghỉ 03 ngày;
b) Con đẻ, con nuôi kết hôn: nghỉ 01 ngày;
c) Cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi; cha đẻ, mẹ đẻ, cha nuôi, mẹ nuôi của vợ hoặc chồng; vợ hoặc chồng; con đẻ, con nuôi chết: nghỉ 03 ngày.
2. Người lao động được nghỉ không hưởng lương 01 ngày và phải thông báo với người sử dụng lao động khi ông nội, bà nội, ông ngoại, bà ngoại, anh, chị, em ruột chết; cha hoặc mẹ kết hôn; anh, chị, em ruột kết hôn.
3. Ngoài quy định tại khoản 1 và khoản 2 Điều này, người lao động có thể thỏa thuận với người sử dụng lao động để nghỉ không hưởng lương.
```
</details>

---

## q20 · metadata_filter · status = `answered`

**Câu hỏi:** Trong phần giải quyết tranh chấp lao động, thời hiệu để yêu cầu hòa giải viên lao động hòa giải tranh chấp cá nhân là bao lâu?

**Đáp án chuẩn:** 06 tháng kể từ ngày phát hiện ra hành vi vi phạm quyền và lợi ích hợp pháp.
- Evidence 1 (Điều 190, trang 39): “Thời hiệu yêu cầu hòa giải viên lao động thực hiện hòa giải tranh chấp lao động cá nhân là 06 tháng”

**Agent trả lời:** Thời hiệu yêu cầu hòa giải viên lao động thực hiện hòa giải tranh chấp lao động cá nhân là 06 tháng kể từ ngày phát hiện ra hành vi mà bên tranh chấp cho rằng quyền và lợi ích hợp pháp của mình bị vi phạm.

**Tìm kiếm:** `thời hiệu yêu cầu hòa giải viên lao động hòa giải tranh chấp cá nhân`
**Auto:** context chứa evidence 1/1 nhóm; 1 lượt tìm; 2.82 s; $0.000346

<details><summary>Citation 1: bllđ-2019:B:art190:0 (trang [39]) — chứa evidence chuẩn</summary>

```text
Điều 190. Thời hiệu yêu cầu giải quyết tranh chấp lao động cá nhân
1. Thời hiệu yêu cầu hòa giải viên lao động thực hiện hòa giải tranh chấp lao động cá nhân là 06 tháng kể từ ngày phát hiện ra hành vi mà bên tranh chấp cho rằng quyền và lợi ích hợp pháp của mình bị vi phạm.
2. Thời hiệu yêu cầu Hội đồng trọng tài lao động giải quyết tranh chấp lao động cá nhân là 09 tháng kể từ ngày phát hiện ra hành vi mà bên tranh chấp cho rằng quyền và lợi ích hợp pháp của mình bị vi phạm.
3. Thời hiệu yêu cầu Tòa án giải quyết tranh chấp lao động cá nhân là 01 năm kể từ ngày phát hiện ra hành vi mà bên tranh chấp cho rằng quyền và lợi ích hợp pháp của mình bị vi phạm.
4. Trường hợp người yêu cầu chứng minh được vì sự kiện bất khả kháng, trở ngại khách quan hoặc lý do khác theo quy định của pháp luật mà không thể yêu cầu đúng thời hạn quy định tại Điều này thì thời gian có sự kiện bất khả kháng, trở ngại khách quan hoặc lý do đó không tính vào thời hiệu yêu cầu giải quyết tranh chấp lao động cá nhân.
```
</details>

---

## q26 · multi_hop · status = `abstain`

**Câu hỏi:** Lao động nữ sinh một con được nghỉ thai sản bao lâu, và khi quay lại làm việc mà việc làm cũ không còn thì công ty phải làm gì?

**Đáp án chuẩn:** Nghỉ 06 tháng (trước sinh không quá 02 tháng); nếu việc làm cũ không còn, công ty phải bố trí việc làm khác với mức lương không thấp hơn mức lương trước khi nghỉ thai sản.
- Evidence 1 (Điều 139, trang 29): “Lao động nữ được nghỉ thai sản trước và sau khi sinh con là 06 tháng”
- Evidence 2 (Điều 140, trang 29): “trường hợp việc làm cũ không còn thì người sử dụng lao động phải bố trí việc làm khác cho họ với mức lương không thấp hơn mức lương trước khi nghỉ thai sản”

**Agent trả lời:** Không đủ bằng chứng trong Bộ luật Lao động 2019 để trả lời.
*(lý do từ chối: Không có thông tin về nghĩa vụ của công ty khi lao động nữ quay lại làm việc mà việc làm cũ không còn.)*

**Tìm kiếm:** `Lao động nữ sinh con nghỉ thai sản`
**Auto:** context chứa evidence 1/2 nhóm; 1 lượt tìm; 2.27 s; $0.000319

---

## u03 · thieu_bang_chung · status = `abstain`

**Câu hỏi:** Doanh nghiệp không giao kết hợp đồng lao động bằng văn bản với người lao động thì bị phạt tiền bao nhiêu?

**Kỳ vọng:** từ chối. Lý do thiếu: Điều 217 chỉ nói vi phạm bị xử phạt vi phạm hành chính; mức phạt nằm ở nghị định xử phạt, không có trong Bộ luật. Kiểm tra: 'phạt tiền' không đi kèm số tiền nào.

**Agent trả lời:** Không đủ bằng chứng trong Bộ luật Lao động 2019 để trả lời.
*(lý do từ chối: Tài liệu không chứa thông tin về mức phạt tiền cụ thể đối với doanh nghiệp không giao kết hợp đồng lao động bằng văn bản.)*

**Tìm kiếm:** `phạt tiền doanh nghiệp không giao kết hợp đồng lao động bằng văn bản`

---

## u04 · thieu_bang_chung · status = `abstain`

**Câu hỏi:** Doanh nghiệp phải đóng kinh phí công đoàn bằng bao nhiêu phần trăm quỹ tiền lương?

**Kỳ vọng:** từ chối. Lý do thiếu: Mức đóng kinh phí công đoàn quy định trong Luật Công đoàn. Kiểm tra: 'kinh phí công đoàn' = 0 kết quả trong Bộ luật.

**Agent trả lời:** Không đủ bằng chứng trong Bộ luật Lao động 2019 để trả lời.
*(lý do từ chối: Không tìm thấy thông tin về tỷ lệ phần trăm kinh phí công đoàn trong quỹ tiền lương trong tài liệu.)*

**Tìm kiếm:** `kinh phí công đoàn phần trăm quỹ tiền lương`

---
