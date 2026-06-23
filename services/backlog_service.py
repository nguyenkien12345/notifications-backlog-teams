import logging

import httpx

from core.config import settings
from models.backlog import BacklogNotification

logger = logging.getLogger("backlog_service")

# Các options khác có thể truyền vào trong httpx.AsyncClient:

# + 1 là headers:
# headers = {
#     "Authorization": "Bearer my-secret-token", # Gửi token bảo mật dạng Bearer
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0", # Giả lập làm trình duyệt Chrome
#     "Accept": "application/json" Thông báo cho server rằng client ưu tiên nhận dữ liệu JSON
# }
# => response = await client.get(url, headers=headers)

# + 2 là auth (Tự động xử lý xác thực tài khoản): Nếu API của bạn bắt buộc phải đăng nhập bằng tài khoản và mật khẩu thông thường (gọi là chế độ Basic Auth):
# => response = await client.get(url, auth=("my_username", "my_password"))

# + 3 là cookie (cookies (Gửi kèm cookie để giữ phiên đăng nhập)): Nếu bạn đang làm Bot để cào dữ liệu từ một trang web yêu cầu đăng nhập, và trang web đó lưu trạng thái qua Cookie, bạn có thể dùng option này để "gửi" các cặp Cookie đi kèm, giúp máy chủ nhận diện bạn đã đăng nhập rồi
# my_cookies = {"session_id": "abc123xyz", "logged_in": "true"}
# => response = await client.get(url, cookies=my_cookies)

# + 4 là follow_redirects (Tự động đuổi theo đường link bị chuyển hướng): Mặc định trong HTTPX, option này bằng False. Có nghĩa là nếu bạn gửi lệnh GET đến link http://facebook.com, máy chủ sẽ phản hồi mã 301 (Đường link này đã chuyển sang bản bảo mật https://facebook.com rồi). Nếu để mặc định, HTTPX sẽ dừng lại và trả về mã 301
# => response = await client.get(url, follow_redirects=True)

# + 5 là verify (Bật/Tắt kiểm tra chứng chỉ bảo mật SSL): Khi kết nối đến các link có chữ https://, Python sẽ kiểm tra xem trang web đó có chứng chỉ bảo mật (SSL) hợp pháp không. Nếu bạn làm việc trong mạng nội bộ công ty (Local Network) hoặc các Server thử nghiệm sử dụng chứng chỉ tự ký (Self-signed certificate), Python sẽ báo lỗi bảo mật và chặn không cho kết nối
# Để ép Bot bỏ qua kiểm tra an toàn và tiếp tục lấy dữ liệu, bạn truyền verify=False
# Lưu ý: Chỉ dùng cho môi trường dev/test. Không nên dùng trên production vì làm mất cơ chế xác thực SSL/TLS.
# => response = await client.get(url, verify=False)


class BacklogService:
    def __init__(self):
        # Build base URL dynamically based on space ID and domain configuration
        space_id = settings.BACKLOG_SPACE_ID
        domain = settings.BACKLOG_DOMAIN

        # Khởi tạo các thuộc tính dùng chung cho toàn bộ instance BacklogService
        # Các thuộc tính này sẽ được tái sử dụng ở các method khác mà không cần đọc lại config (Ở đây chính là base_url và api_key)
        if "." in space_id:
            self.base_url = f"https://{space_id}/api/v2"
        else:
            self.base_url = f"https://{space_id}.{domain}/api/v2"

        self.api_key = settings.BACKLOG_API_KEY.get_secret_value()

    async def fetch_notifications(
        self,
        min_id: int
        | None = None,  # Chỉ lấy những thông báo có ID lớn hơn số min_id này (nhằm tránh lấy lại thông báo cũ)
        count: int = 50,  # Số lượng thông báo muốn lấy trong 1 lần quét. Mặc định là 50 tin
    ) -> list[BacklogNotification]:
        url = f"{self.base_url}/notifications"
        params = {"apiKey": self.api_key, "count": count}

        if min_id is not None and min_id > 0:
            # Nếu người dùng có truyền vào một số min_id cụ thể và số đó lớn hơn 0, hệ thống sẽ nhét thêm một tham số tên là "minId" vào gói hàng params
            params["minId"] = min_id

        logger.debug(
            f"Fetching notifications from Backlog: {url} with params count={count}, minId={min_id}"
        )

        # + with: Đảm bảo kết nối được đóng và tài nguyên được giải phóng sau khi sử dụng
        # + timeout=10.0: Nếu request mất quá nhiều thời gian (mặc định tối đa 10 giây) httpx sẽ phát sinh TimeoutException
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)

                # Check for HTTP errors
                if response.status_code == 401:
                    logger.error("Unauthorized: Please check your Backlog API Key.")
                    response.raise_for_status()
                elif response.status_code == 404:
                    logger.error(
                        f"Space not found: Please verify your space ID ({settings.BACKLOG_SPACE_ID}) and domain ({settings.BACKLOG_DOMAIN})."
                    )
                    response.raise_for_status()
                else:
                    response.raise_for_status()

                raw_notifications = response.json()

                # - Duyệt qua từng thông báo thô n trong danh sách raw_notifications
                # - BacklogNotification(n) nghĩa là: "Hãy lấy tất cả các thông tin trong cục thô n này, đổ vào cái khuôn BacklogNotification để ép kiểu dữ liệu chuẩn chỉnh"
                # - BacklogNotification(n) còn: validate dữ liệu, convert kiểu dữ liệu, tạo object
                # - Ý nghĩa của 2 dấu ** (Dictionary Unpacking):
                #   * Hãy tưởng tượng cục dữ liệu thô n nhận về từ Backlog là một chiếc hộp đóng gói kín, bên trong chứa các cặp thông tin dạng Dictionary như thế này:
                #   * VD: n = {"id": 123, "content": "Ai đó vừa tag bạn", "sender": "Nam"}
                #   * Còn cái khuôn BacklogNotification của bạn thì lại chừa sẵn các ô trống riêng biệt để nhận dữ liệu vào: def BacklogNotification(id, content, sender): ...
                #   * Khi bạn gõ BacklogNotification(n), dấu ** đóng vai trò như một phép thuật "khui cái hộp n ra" và tự động đem các giá trị nhét vào đúng các ô trống có tên tương ứng của cái khuôn:
                #   * - Nó lấy giá trị của "id" nhét vào ô id
                #   * - Nó lấy giá trị của "content" nhét vào ô content

                notifications = [BacklogNotification(**n) for n in raw_notifications]

                # Tiến hành sắp xếp (sort) lại danh sách thông báo theo thứ tự tăng dần của trường id (thông báo nào có ID nhỏ hơn tức là xảy ra trước sẽ được xếp lên đầu)
                # Bonus thêm: Nếu muốn sắp xếp gỉam dần thì thêm option reverse=True vào. VD: notifications.sort(key=lambda x: x.id, reverse=True)
                notifications.sort(key=lambda x: x.id)
                return notifications

            except httpx.HTTPStatusError as hse:
                logger.error(
                    f"HTTP error occurred while contacting Backlog API: {hse.response.status_code} - {hse.response.text}"
                )
                raise hse
            except Exception as e:
                logger.error(f"Unexpected error occurred while fetching Backlog notifications: {e}")
                raise e
