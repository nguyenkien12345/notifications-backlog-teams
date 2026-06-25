# Hướng dẫn sử dụng HTTPX AsyncClient

---

## Các Tùy Chọn Cấu Hình Chi Tiết (Options)

### 1. `headers` (Gửi thông tin HTTP Headers)
Dùng để gửi các thông tin bổ sung lên server như token bảo mật, giả lập trình duyệt, hoặc định dạng dữ liệu ưu tiên nhận.
```python
headers = {
    # Gửi token bảo mật dạng Bearer
    "Authorization": "Bearer my-secret-token", 
    # Giả lập làm trình duyệt Chrome để tránh bị chặn bởi một số hệ thống chống bot
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0", 
    # Thông báo cho server rằng client ưu tiên nhận dữ liệu JSON
    "Accept": "application/json" 
}

response = await client.get(url, headers=headers)
```

---

### 2. `auth` (Xác thực tài khoản - Basic Auth)
Sử dụng khi API yêu cầu đăng nhập bằng tài khoản và mật khẩu thông thường. HTTPX sẽ tự động mã hóa Base64 và xử lý các thủ tục xác thực.
```python
response = await client.get(url, auth=("my_username", "my_password"))
```

---

### 3. `cookies` (Gửi kèm Cookie để giữ phiên đăng nhập)
Thích hợp khi làm Bot cào dữ liệu từ các trang web yêu cầu đăng nhập, và trang web đó lưu trạng thái qua Cookie. Option này giúp gửi các cặp Cookie đi kèm để máy chủ nhận diện bạn đã đăng nhập.
```python
my_cookies = {
    "session_id": "abc123xyz", 
    "logged_in": "true"
}

response = await client.get(url, cookies=my_cookies)
```

---

### 4. `follow_redirects` (Tự động đuổi theo link chuyển hướng)
Mặc định trong HTTPX, tùy chọn này bằng `False`. Có nghĩa là nếu bạn gửi lệnh GET đến link `http://facebook.com`, máy chủ phản hồi mã chuyển hướng `301` hoặc `302` sang `https://facebook.com`, HTTPX sẽ dừng lại ở đó. Bật `True` để tự động đi tiếp đến link cuối cùng.
```python
response = await client.get(url, follow_redirects=True)
```

---

### 5. `verify` (Bật/Tắt kiểm tra chứng chỉ bảo mật SSL)
Khi kết nối đến các link `https://`, Python sẽ kiểm tra xem trang web đó có chứng chỉ bảo mật (SSL) hợp pháp không. 

Nếu bạn làm việc trong mạng nội bộ công ty (Local Network) hoặc các Server thử nghiệm sử dụng chứng chỉ tự ký (Self-signed certificate), Python sẽ báo lỗi bảo mật và chặn kết nối. Truyền `verify=False` để bỏ qua bước kiểm tra an toàn này.
```python
response = await client.get(url, verify=False)
```

> [!WARNING]
> **Lưu ý bảo mật:** Chỉ sử dụng `verify=False` cho môi trường phát triển (development) hoặc thử nghiệm (test). Tuyệt đối không dùng trên môi trường production vì nó làm mất cơ chế xác thực SSL/TLS, dẫn đến nguy cơ bị tấn công giả mạo (Man-in-the-Middle).
