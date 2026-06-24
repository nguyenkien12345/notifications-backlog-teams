## 1. Tổng quan Luồng công việc (Flow Overview)
1. **Trigger**: Tiếp nhận dữ liệu từ Teams Webhook.
2. **Khởi tạo**: Định nghĩa và thiết lập các biến lưu trữ nội dung (`Body`) và tệp đính kèm (`Attachments`).
3. **Điều kiện**: Kiểm tra xem trường tệp đính kèm có trống (`null`) hay không.
4. **Hành động (nhánh True (Happy Case))**: Nếu không có tệp đính kèm, gửi một Adaptive Card vào Group chat "48:notes".

---

## 2. Chi tiết từng Bước (Step-by-Step Breakdown)

### Bước 1: Trigger - When a Teams webhook request is received
* **Chức năng**: Đây là điểm bắt đầu của luồng (Trigger). Nó đóng vai trò như một HTTP Endpoint lắng nghe các dữ liệu dạng JSON được gửi từ một ứng dụng bên ngoài hoặc chính hệ thống Teams thông qua cơ chế Webhook.
* **Đầu vào (Input)**:
  * HTTP Request (Payload dạng JSON) được gửi tới URL của Webhook. Cấu trúc thường bao gồm thông tin người gửi, nội dung thông điệp, danh sách tệp đính kèm...
* **Đầu ra (Output)**:
  * Một đối tượng JSON chứa toàn bộ dữ liệu của Request (`Trigger Body`). Các bước phía sau có thể truy xuất các thuộc tính nằm trong JSON này.

### Bước 2: Action - Do Not Remove FlowIL
* **Chức năng**: Khởi tạo hoặc thực hiện một tác vụ cố định liên quan đến biến hoặc định danh cấu trúc (có thể là một biến chuỗi hoặc một bước đánh dấu nội bộ để giữ luồng không bị lỗi hệ thống/ID).
* **Đầu vào (Input)**: Giá trị mặc định hoặc chuỗi định danh tĩnh.
* **Đầu ra (Output)**: Giá trị hoặc trạng thái của biến `FlowIL` đã được thiết lập thành công.

### Bước 3: Action - Initialize variable (Body)
* **Chức năng**: Khởi tạo một biến (thường là kiểu chuỗi `String` hoặc `Object`) để lưu trữ phần thân nội dung chính của thông điệp nhận được từ Webhook nhằm dễ dàng tái sử dụng ở các bước sau.
* **Đầu vào (Input)**:
  * Name: `Body`
  * Type: `String` hoặc `Object`
  * Value: Trích xuất từ thuộc tính nội dung của Bước 1 (ví dụ: `triggerBody()?['body']`).
* **Đầu ra (Output)**: Biến `Body` được lưu trữ trong bộ nhớ tạm của lượt chạy flow hiện tại.

### Bước 4: Action - Initialize variable (Attachments)
* **Chức năng**: Khởi tạo một biến kiểu danh sách (`Array`) hoặc đối tượng (`Object`/`String`) chuyên biệt để quản lý dữ liệu liên quan đến các tệp đính kèm đi kèm với yêu cầu webhook.
* **Đầu vào (Input)**:
  * Name: `Attachments`
  * Type: `Array` hoặc `String` (tùy thuộc vào cấu trúc webhook thiết lập)
  * Value: Trích xuất từ mảng dữ liệu đính kèm của Bước 1 (ví dụ: `triggerBody()?['attachments']`).
* **Đầu ra (Output)**: Biến `Attachments` chứa danh sách các tệp dữ liệu được truyền vào luồng.

### Bước 5: Condition - Attachments is null
* **Chức năng**: Sử dụng cấu trúc rẽ nhánh điều kiện logic (`If/Else`) để kiểm tra xem biến `Attachments` có giá trị hay không.
* **Đầu vào (Input)**: Giá trị hiện tại của biến `Attachments`.
* **Logic kiểm tra**: Biến `Attachments` `is equal to` `null` (hoặc rỗng).
* **Đầu ra (Output)**: Kết quả Boolean (`True` hoặc `False`). Luồng sẽ đi vào một trong hai nhánh tương ứng:

#### Nhánh TRUE (Khi biến Attachments rỗng/null):
Nếu điều kiện thỏa mãn (không có tệp đính kèm nào được gửi kèm theo webhook), luồng sẽ thực hiện hành động:
* **Action: Post card in a chat or channel 1**
  * **Tham số thiết lập (Parameters)**:
    * `Post as`: `Flow bot` (Gửi tin nhắn dưới danh nghĩa là Bot của hệ thống tự động).
    * `Post in`: `Group chat` (Đăng trực tiếp vào một cuộc trò chuyện nhóm).
    * `Group chat`: `48:notes` (Mục tiêu chính xác của nhóm chat nhận tin).
    * `Adaptive Card`: `string(...)` (Một biểu thức xử lý chuỗi JSON của thẻ Thích ứng, chứa cấu trúc hiển thị thông tin đẹp mắt, nút bấm hoặc biểu đồ tĩnh).
  * **Đầu vào (Input)**: Cấu trúc JSON của Adaptive Card và ID của cuộc trò chuyện nhóm `48:notes`.
  * **Đầu ra (Output)**: Thẻ tin nhắn hiển thị thành công trong Microsoft Teams chat nhóm; trả về ID của tin nhắn đã đăng và mã trạng thái thành công (`Status Code: 200`).

#### Nhánh FALSE (Khi biến Attachments KHÔNG rỗng - có chứa tệp đính kèm):
* Hiện tại nhánh này hiển thị **1 Action**, dùng để xử lý các logic nghiệp vụ khi có file đính kèm (ví dụ: tải file lên OneDrive/SharePoint, hoặc gửi một loại thẻ thông báo khác có kèm link download file).

---

## 3. Cơ chế hoạt động đồng bộ của hệ thống (How It Works)

```
[Webhook Request] 
       │
       ▼
[Nhận Payload JSON] ──► [Khởi tạo & Gán giá trị vào biến Body & Attachments]
                                                     │
                                                     ▼
                                       ┌───────────────────────────┐
                                       │ Kiểm tra: Attachments=null?│
                                       └─────────────┬─────────────┘
                                                     │
                                           ┌─────────┴─────────┐
                                           ▼ True              ▼ False
                             [Gửi Adaptive Card vào]     [Thực hiện 1 tác vụ]
                             [Group Chat '48:notes']     [Xử lý tệp đính kèm]
```

1. **Kích hoạt luồng**: Khi một hệ thống bên thứ ba gửi dữ liệu đến URL Webhook được cấu hình, Power Automate bắt đầu một phiên chạy (run instance).
2. **Xử lý biến**: Hệ thống tuần tự đi qua bước kiểm tra an toàn `Do Not Remove FlowIL` và trích xuất thông tin thô từ webhook để map gọn gàng vào hai biến cục bộ là `Body` và `Attachments`. Việc này giúp tối ưu hóa hiệu năng và tránh việc phân tách lại chuỗi JSON phức tạp ở các bước sau.
3. **Rẽ nhánh thông minh**: Bộ kiểm tra điều kiện hoạt động độc lập để phân loại luồng dữ liệu. Đối với kịch bản được cấu hình chi tiết ở hình 2, khi không phát hiện tệp đính kèm (Nhánh True), Flow Bot sẽ ngay lập tức được triệu hồi để render một thẻ nội dung (`Adaptive Card`) thông qua chuỗi biểu thức `string(...)` và đẩy trực tiếp vào phòng chat nội bộ có ID tương ứng với nhóm `48:notes`.

---
