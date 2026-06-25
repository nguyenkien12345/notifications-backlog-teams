import logging

import httpx

from core.config import settings
from models.backlog import BacklogNotification

logger = logging.getLogger("backlog_service")

class BacklogService:
    def __init__(self):
        space_id = settings.BACKLOG_SPACE_ID
        domain = settings.BACKLOG_DOMAIN

        if "." in space_id:
            self.base_url = f"https://{space_id}/api/v2"
        else:
            self.base_url = f"https://{space_id}.{domain}/api/v2"

        self.api_key = settings.BACKLOG_API_KEY.get_secret_value()

    async def fetch_notifications(
        self,
        min_id: int
        | None = None,
        count: int = 50,
    ) -> list[BacklogNotification]:
        url = f"{self.base_url}/notifications"
        params = {"apiKey": self.api_key, "count": count}

        if min_id is not None and min_id > 0:
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

                # Tiến hành sắp xếp (sort) lại danh sách thông báo theo thứ tự giảm dần của trường id (thông báo nào có ID lớn hơn tức là mới nhất sẽ được xếp lên đầu)
                # Bonus thêm: Nếu muốn sắp xếp gỉam dần thì thêm option reverse=True vào. VD: notifications.sort(key=lambda x: x.id, reverse=True)
                notifications.sort(key=lambda x: x.id, reverse=True)
                return notifications

            except httpx.HTTPStatusError as hse:
                logger.error(
                    f"HTTP error occurred while contacting Backlog API: {hse.response.status_code} - {hse.response.text}"
                )
                raise hse
            except Exception as e:
                logger.error(f"Unexpected error occurred while fetching Backlog notifications: {e}")
                raise e

    async def fetch_issue_comment_count(self, issue_id_or_key: str | int) -> int:
        """
        Fetch the total number of comments for a specific issue.
        """
        url = f"{self.base_url}/issues/{issue_id_or_key}/comments/count"
        params = {"apiKey": self.api_key}

        logger.debug(f"Fetching comment count for issue {issue_id_or_key}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                return data.get("count", 0)
            except Exception as e:
                logger.error(f"Failed to fetch comment count for issue {issue_id_or_key}: {e}")
                return 0
