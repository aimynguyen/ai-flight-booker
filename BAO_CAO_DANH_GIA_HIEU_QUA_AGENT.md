# Báo cáo đánh giá hiệu quả của Agent theo ba mẫu thiết kế

**Phạm vi:** ứng dụng đặt vé máy bay
**Sinh viên:** Nguyễn Ái My  
**MSSV:** 24521092  
**Ba mẫu được so sánh:** ReAct, Plan-then-Execute và Hybrid

## 1. Tóm tắt

Ba agent cùng giải quyết một quy trình: tìm chuyến bay SGN–DAD ngày 07/10/2026, chọn chuyến thỏa điều kiện khởi hành trước 12:00 và giá không quá 2.000.000 VND, đặt chỗ, thanh toán và xác minh hoàn tất.

- **ReAct** để mô hình ngôn ngữ quyết định chuỗi gọi công cụ. Cách này linh hoạt nhất về điều phối, nhưng phụ thuộc vào đầu ra của LLM và các rào chắn/counter dùng chung.
- **Plan-then-Execute** yêu cầu LLM sinh kế hoạch, nhưng phần thực thi lại là quy trình cố định trong code. Nó dễ dự đoán, song không thực sự thực thi nội dung kế hoạch và dừng ngay khi không đặt được chuyến đã chọn.
- **Hybrid** cũng sinh kế hoạch rồi thực hiện bằng code có cấu trúc; điểm khác biệt quan trọng là nó thử chuyến hợp lệ tiếp theo khi đặt chỗ thất bại. Trong ba fixture hiện có, đây là mẫu cân bằng tốt nhất giữa kiểm soát và khả năng phục hồi.

**Kết luận cần đọc cùng giới hạn:** các con số dưới đây là kết quả kỳ vọng suy ra từ logic và dữ liệu mock trong code, không phải kết quả benchmark đã chạy. Bộ đánh giá dùng Gemini thật cho cả ba agent, chỉ có ba kịch bản, và cách tính số bước không đồng nhất. Vì vậy chưa đủ cơ sở để kết luận về thời gian đáp ứng, chi phí token hay tỷ lệ thành công thống kê.

## 2. Cơ sở đánh giá và tiêu chí

Các kịch bản, fixture, cách reset trạng thái và hàm tổng hợp kết quả nằm trong [evaluation.py](./evaluation.py), dữ liệu chuyến bay và đặt chỗ giả lập nằm trong [tools.py](./tools.py), còn ràng buộc, quyền, giới hạn bước và phát hiện vòng lặp nằm trong [harness.py](./harness.py).

| Tiêu chí                  | Ý nghĩa trong báo cáo                                                                                        |
| ------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Hoàn thành nhiệm vụ       | Đặt được chuyến hợp lệ, thanh toán thành công và vượt qua bước xác minh.                                     |
| Khả năng thích ứng        | Tiếp tục với chuyến khác sau khi một lựa chọn không đặt được.                                                |
| Kiểm soát và tính dự đoán | Mức độ quy trình và điều kiện quyết định được thực thi rõ ràng trong code thay vì phụ thuộc vào LLM.         |
| Hiệu quả bước             | Chỉ dùng số bước được harness hiện tại báo cáo; không coi đây là số lần gọi LLM, độ trễ hay chi phí thực tế. |
| Khả năng kiểm chứng       | Mức độ có thể xác nhận kết quả bằng trạng thái booking và các điều kiện nghiệp vụ.                           |

## 3. Ba mẫu thiết kế

### 3.1 ReAct

Trong [react_agent.py](./agents/react_agent.py), `create_agent` kết hợp Gemini với các công cụ tìm chuyến, đặt ghế, thanh toán và tra cứu booking. Mô hình tự quyết định lúc nào gọi công cụ tiếp theo dựa trên kết quả nhận được. Các công cụ tích hợp một số kiểm tra quyền, giới hạn bước và phát hiện gọi lặp.

**Điểm mạnh**

- Linh hoạt khi yêu cầu người dùng thay đổi hoặc cần chuỗi hành động khác với quy trình chuẩn.
- Có thể quan sát kết quả công cụ rồi quyết định hành động tiếp theo, nên về thiết kế phù hợp với tác vụ tương tác.
- Có các rào chắn bước và quyền gọi công cụ.

**Điểm yếu và rủi ro**

- Kết quả và số lần gọi công cụ phụ thuộc vào LLM; không thể suy ra chắc chắn từ code là agent sẽ chọn đúng chuyến hoặc luôn hoàn tất.
- `LoopDetector` chặn lần gọi liên tiếp cùng một hành động từ lần thứ hai. Điều này có thể cản trở việc thử đặt chuyến khác sau một lần đặt thất bại.
- `budget_tracker` và `loop_detector` được tạo ở phạm vi module. Endpoint web trong [app.py](./app.py) không khởi tạo lại chúng cho từng yêu cầu, trong khi harness có reset chúng cho từng case. Kết quả chạy qua web có thể vì thế phụ thuộc các yêu cầu trước.
- Phần `get_booking_tool` sử dụng tên `result` đã import từ `unittest` như một dict (`result["completed"] = ...`). Đây là lỗi tiềm tàng trên đường xác minh booking, làm giảm độ tin cậy của luồng ReAct.

**Đánh giá:** tiềm năng thích ứng cao nhất về mặt kiến trúc, nhưng độ ổn định hiện tại bị giới hạn bởi trạng thái dùng chung, luật chặn lặp và lỗi trong công cụ xác minh.

### 3.2 Plan-then-Execute

[plan_then_execute.py](./agents/plan_then_execute.py) dùng LLM để sinh danh sách kế hoạch, sau đó code tự tìm chuyến hợp lệ rẻ nhất, đặt, trả tiền và xác minh theo thứ tự cố định.

**Điểm mạnh**

- Luồng thực thi đơn giản, dễ theo dõi và có đường đi thành công rõ ràng.
- Chọn chuyến và kiểm tra ràng buộc được thực hiện bằng logic Python, không giao quyết định chọn chuyến cho LLM.
- Phù hợp khi quy trình ổn định và ưu tiên tính dự đoán.

**Điểm yếu**

- Nội dung `plan` chỉ được in ra; không được phân tích hay dùng để điều khiển thực thi. Do đó, đây chưa phải thực thi kế hoạch do LLM lập, mà là một workflow cố định có bước tạo kế hoạch.
- Khi chuyến rẻ nhất hợp lệ không đặt được, agent trả thất bại ngay thay vì thử chuyến kế tiếp.
- Hành trình, ngày bay và ràng buộc được đọc từ `harness.CONSTRAINTS` hoặc truyền hằng số SGN, DAD, ngày 07/10/2026. Chúng không được trích xuất từ `user_request`.

**Đánh giá:** tính dự đoán và khả năng kiểm thử tốt, nhưng khả năng phục hồi thấp. Có thể phù hợp cho quy trình có dữ liệu ổn định nếu bổ sung retry và truyền yêu cầu có cấu trúc.

### 3.3 Hybrid

[hybrid_agent.py](./agents/hybrid_agent.py) dùng LLM để tạo kế hoạch, còn tìm chuyến, lọc ràng buộc, chọn chuyến, đặt, thanh toán và xác minh do code điều khiển. Nếu đặt một chuyến thất bại, vòng lặp loại chuyến đó khỏi danh sách đã thử rồi chọn ứng viên hợp lệ rẻ tiếp theo.

**Điểm mạnh**

- Việc chọn chuyến và kiểm tra các điều kiện quan trọng được thực hiện rõ ràng trong code.
- Có khả năng thử chuyến kế tiếp sau lỗi đặt chỗ; đây là cải thiện trực tiếp so với Plan-then-Execute.
- Ít phụ thuộc hơn ReAct vào việc LLM quyết định đúng thứ tự công cụ trong giao dịch đặt vé.

**Điểm yếu**

- Kế hoạch LLM cũng chỉ được in ra và không ảnh hưởng đến luồng thực thi.
- Hybrid chỉ retry lỗi đặt chỗ. Lỗi thanh toán hoặc xác minh sẽ kết thúc tác vụ.

**Đánh giá:** lựa chọn phù hợp nhất trong ba mẫu cho fixture đặt vé hiện tại vì kết hợp kiểm soát xác định với retry có giới hạn. Tuy nhiên, cần xử lý đầu vào động và chuẩn hóa đo lường trước khi dùng kết luận này cho môi trường thực tế.

## 4. Kết quả kỳ vọng theo dữ liệu mock

Trong [tools.py](./tools.py), các fixture có ý nghĩa như sau:

- `success`: có chuyến VJ604 giá 1.480.000 VND, khởi hành 08:10, thỏa điều kiện và rẻ nhất trong các chuyến hợp lệ.
- `fail`: không có chuyến nào đồng thời thỏa giờ khởi hành và giới hạn giá.
- `booking_failure`: VJ604 là chuyến hợp lệ rẻ nhất nhưng được cấu hình để đặt thất bại; VN122 là lựa chọn hợp lệ tiếp theo.

| Kịch bản          | ReAct                                                                                   | Plan-then-Execute                                                | Hybrid                                                                  |
| ----------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `success`         | Không thể xác định tĩnh; tùy quyết định LLM và đường gọi công cụ.                       | **Kỳ vọng thành công**: chọn VJ604, thanh toán và xác minh.      | **Kỳ vọng thành công**: chọn VJ604, thanh toán và xác minh.             |
| `fail`            | Không thể xác định tĩnh; cần xác nhận hành vi từ đầu ra chạy thực tế.                   | **Kỳ vọng thất bại đúng**: không tìm thấy chuyến thỏa ràng buộc. | **Kỳ vọng thất bại đúng**: không còn chuyến hợp lệ để thử.              |
| `booking_failure` | Có khả năng không phục hồi do detector chặn gọi `book_seat` lặp; kết quả phụ thuộc LLM. | **Kỳ vọng thất bại**: dừng sau khi đặt VJ604 không thành công.   | **Kỳ vọng thành công**: bỏ VJ604, thử VN122 rồi thanh toán và xác minh. |

Theo logic dự kiến ở trên, tỷ lệ hoàn thành của Plan-then-Execute là **1/3** và Hybrid là **2/3** trên ba fixture. Đây là **ước lượng từ code**, không phải số liệu chạy thực nghiệm. Với ReAct, không báo tỷ lệ thành công giả định vì phụ thuộc vào phản hồi LLM và có lỗi tiềm tàng ở bước tra cứu booking.

## 5. Kết luận và khuyến nghị

| Mục tiêu                                        | Mẫu phù hợp nhất theo code hiện tại                      |
| ----------------------------------------------- | -------------------------------------------------------- |
| Linh hoạt khi luồng hành động biến đổi          | ReAct, sau khi sửa lỗi xác minh và phạm vi state/counter |
| Luồng đơn giản, có thể dự đoán                  | Plan-then-Execute                                        |
| Đặt vé có kiểm soát và chịu được lỗi đặt chuyến | Hybrid                                                   |
