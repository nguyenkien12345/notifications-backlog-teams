import logging
from typing import Any

import httpx

from constants import DEFAULT_THEME_COLOR, THEME_COLORS
from core.config import settings
from models.backlog import BacklogNotification
from utils import build_backlog_url, truncate_text

logger = logging.getLogger("teams_service")


class TeamsService:
    def __init__(self):
        self.webhook_url = settings.TEAMS_WEBHOOK_URL.get_secret_value()

    def get_backlog_url(self, notification: BacklogNotification) -> str:
        return build_backlog_url(
            space_id=settings.BACKLOG_SPACE_ID,
            domain=settings.BACKLOG_DOMAIN,
            project_key=notification.project.projectKey if notification.project else None,
            issue_key=notification.issue.issueKey if notification.issue else None,
            comment_id=notification.comment.id if notification.comment else None,
            is_pull_request=bool(notification.pullRequest),
        )

    def get_theme_color(self, reason: int) -> str:
        # - Nếu tìm thấy, nó lấy màu đó ra. Nếu không tìm thấy, nó sẽ tự động lấy màu mặc định (DEFAULT_THEME_COLOR)
        return THEME_COLORS.get(reason, DEFAULT_THEME_COLOR)

    def build_message_card(self, notification: BacklogNotification) -> dict[str, Any]:
        emoji = notification.get_action_emoji()
        reason_desc = notification.get_reason_description()
        sender_name = notification.sender.name if notification.sender else "Someone"

        # - Build notification title from action emoji, sender name and action description
        title = f"{emoji} {sender_name} {reason_desc}"

        # - Lấy mã màu chủ đề của card và lấy đường link chi tiết dẫn đến Backlog
        theme_color = self.get_theme_color(notification.reason)
        backlog_url = self.get_backlog_url(notification)

        # - Một thông báo trên Backlog có thể xuất phát từ một Công việc (Issue) hoặc một Yêu cầu duyệt code (Pull Request)
        # - Khởi tạo 3 biến: facts, text_content, và subtitle
        facts = []  # Danh sách thông số phụ (facts)
        text_content = ""  # Nội dung tin nhắn (text_content)
        subtitle = ""  # Tiêu đề phụ (subtitle)

        if notification.project:
            facts.append(
                {"name": "Project", "value": f"[{notification.project.name}] ({backlog_url})"}
            )
            subtitle = notification.project.name

        # + TRƯỜNG HỢP 1: NẾU LÀ CÔNG VIỆC (ISSUE)
        if notification.issue:
            facts.append({"name": "Issue Key", "value": notification.issue.issueKey})
            facts.append({"name": "Summary", "value": notification.issue.summary})
            subtitle = f"{notification.project.projectKey if notification.project else ''} - {notification.issue.issueKey}"

            # Chọn nội dung hiển thị: Ưu tiên nội dung bình luận, nếu không có thì lấy mô tả công việc
            if notification.comment and notification.comment.content:
                text_content = notification.comment.content
            elif notification.issue.description:
                text_content = notification.issue.description

        # + TRƯỜNG HỢP 2: NẾU LÀ YÊU CẦU DUYỆT CODE (PULL REQUEST)
        elif notification.pullRequest:
            facts.append({"name": "PR Number", "value": f"#{notification.pullRequest.number}"})
            facts.append({"name": "PR Title", "value": notification.pullRequest.title})
            subtitle = f"PR #{notification.pullRequest.number} - {notification.pullRequest.title}"

            if notification.comment and notification.comment.content:
                text_content = notification.comment.content
            elif notification.pullRequest.description:
                text_content = notification.pullRequest.description

        # Truncate content if it's too long
        text_content = truncate_text(text_content, max_length=500)

        # - Tạo một phân đoạn (section) chứa toàn bộ tiêu đề, tiêu đề phụ, bảng thông số facts và nội dung chữ text_content vừa tính toán được ở trên
        section: dict[str, Any] = {
            "activityTitle": title,
            "activitySubtitle": subtitle,
            "markdown": True,
            "facts": facts,
        }

        if text_content:
            section["text"] = f"**Content:**\n\n{text_content}"

        # - Gom toàn bộ thông tin vào một cục Dictionary lớn đặt tên là card
        # - potentialAction: Ra lệnh cho Teams vẽ ra một cái Nút bấm (Action Button) tên là "View in Backlog". Khi người dùng trên Teams click vào nút này, trình duyệt sẽ tự động mở ra đường link backlog_url dẫn thẳng tới trang công việc đó
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": f"Backlog Notification from {sender_name}",
            "sections": [section],
            "potentialAction": [
                {
                    "@type": "OpenUri",
                    "name": "View in Backlog",
                    "targets": [{"os": "default", "uri": backlog_url}],
                }
            ],
        }

        return card

    async def send_notification(self, notification: BacklogNotification) -> bool:
        card_payload = self.build_message_card(notification)

        logger.debug(f"Sending card to Teams for notification ID {notification.id}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.webhook_url, json=card_payload)

                # Check for Teams webhook return code (usually returns '1' as text on success)
                if response.status_code == 200:
                    logger.info(f"Successfully posted notification {notification.id} to Teams.")
                    return True
                else:
                    logger.error(
                        f"Failed to post to Teams Webhook: HTTP {response.status_code} - {response.text}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error occurred while posting to Teams Webhook: {e}")
                return False
