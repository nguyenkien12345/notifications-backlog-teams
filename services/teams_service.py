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

    def build_message_card(
        self, notification: BacklogNotification, comment_count: int | None = None
    ) -> dict[str, Any]:
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

            # Additional details for issue creator, comments, status, assignee, priority
            if notification.issue.createdUser:
                facts.append({"name": "Created By", "value": notification.issue.createdUser.name})
            if notification.issue.assignee:
                facts.append({"name": "Assignee", "value": notification.issue.assignee.name})
            if notification.issue.status:
                facts.append({"name": "Status", "value": notification.issue.status.name})
            if notification.issue.priority:
                facts.append({"name": "Priority", "value": notification.issue.priority.name})
            if comment_count is not None:
                facts.append({"name": "Total Comments", "value": str(comment_count)})

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

    def build_adaptive_card_payload(
        self, notification: BacklogNotification, comment_count: int | None = None
    ) -> dict[str, Any]:
        emoji = notification.get_action_emoji()
        reason_desc = notification.get_reason_description()
        sender_name = notification.sender.name if notification.sender else "Someone"

        # - Build notification title from action emoji, sender name and action description
        title = f"{emoji} {sender_name} {reason_desc}"

        # - Lấy đường link chi tiết dẫn đến Backlog
        backlog_url = self.get_backlog_url(notification)

        # - Một thông báo trên Backlog có thể xuất phát từ một Công việc (Issue) hoặc một Yêu cầu duyệt code (Pull Request)
        # - Khởi tạo 3 biến: facts, text_content, và subtitle
        facts = []  # Danh sách thông số phụ (facts)
        subtitle = ""  # Tiêu đề phụ (subtitle)
        text_content = ""  # Nội dung tin nhắn (text_content)

        if notification.project:
            facts.append({"title": "Project", "value": notification.project.name})
            subtitle = notification.project.name

        if notification.issue:
            facts.append({"title": "Issue Key", "value": notification.issue.issueKey})
            facts.append({"title": "Summary", "value": notification.issue.summary})

            # Additional details for issue creator, comments, status, assignee, priority
            if notification.issue.createdUser:
                facts.append({"title": "Created By", "value": notification.issue.createdUser.name})
            if notification.issue.assignee:
                facts.append({"title": "Assignee", "value": notification.issue.assignee.name})
            if notification.issue.status:
                facts.append({"title": "Status", "value": notification.issue.status.name})
            if notification.issue.priority:
                facts.append({"title": "Priority", "value": notification.issue.priority.name})
            if comment_count is not None:
                facts.append({"title": "Total Comments", "value": str(comment_count)})

            subtitle = f"{notification.project.projectKey if notification.project else ''} - {notification.issue.issueKey}"

            if notification.comment and notification.comment.content:
                text_content = notification.comment.content
            elif notification.issue.description:
                text_content = notification.issue.description

        elif notification.pullRequest:
            facts.append({"title": "PR Number", "value": f"#{notification.pullRequest.number}"})
            facts.append({"title": "PR Title", "value": notification.pullRequest.title})
            subtitle = f"PR #{notification.pullRequest.number} - {notification.pullRequest.title}"

            if notification.comment and notification.comment.content:
                text_content = notification.comment.content
            elif notification.pullRequest.description:
                text_content = notification.pullRequest.description

        text_content = truncate_text(text_content, max_length=500)

        # Khởi tạo một mảng chứa các khối. Khối đầu tiên là TextBlock (Khối văn bản)
        body_elements: list[dict[str, Any]] = [
            {
                "type": "TextBlock",
                "text": title,  # Tiêu đề chính
                "weight": "Bolder",  # Chữ in đậm
                "size": "Medium",  # Chữ cỡ trung
                "wrap": True,  # Tự động xuống dòng nếu tiêu đề quá dài (để tránh bị dấu ba chấm ...)
                "color": "Attention",  # Màu đỏ,
                "maxLines": 3,  # Số dòng tối đa hiển thị, nếu vượt quá sẽ bị ẩn đi và hiển thị dấu ba chấm ở cuối
                "horizontalAlignment": "Left",
            }
        ]

        if subtitle:
            body_elements.append(
                {
                    "type": "TextBlock",
                    "text": subtitle,  # Tiêu đề phụ
                    "isSubtle": True,  # Hiển thị mờ hơn (để phân biệt với tiêu đề chính)
                    "weight": "Lighter",  # Chữ mỏng hơn
                    "spacing": "None",  # Nằm sát sạt ngay dưới tiêu đề chính, không bị khoảng trống rộng
                    "wrap": True,  # Tự động xuống dòng nếu tiêu đề quá dài (để tránh bị dấu ba chấm ...)
                    "color": "Warning",  # Màu Vàng/Cam
                    "maxLines": 3,  # Số dòng tối đa hiển thị, nếu vượt quá sẽ bị ẩn đi và hiển thị dấu ba chấm ở cuối
                    "horizontalAlignment": "Left",
                }
            )

        # Bảng thông số
        if facts:
            # FactSet:
            # - Tạo ra một cái bảng thông tin (key-value)
            # - Nó sẽ tự động chia màn hình làm 2 cột: cột trái in đậm (Title) và cột phải in thường (Value) thẳng hàng tăm tắp
            # Ví dụ:
            #   Project: Backlog
            #   Issue Key: BACK-123
            #   Summary: Fix bug in login page
            body_elements.append(
                {
                    "type": "FactSet",
                    "facts": facts,
                    "spacing": "Medium",
                }
            )

        #  Nội dung tin nhắn
        if text_content:
            body_elements.append(
                {
                    "type": "TextBlock",
                    "text": f"**Content:**\n\n{text_content}",
                    "wrap": True,
                    "spacing": "Medium",  # Tạo một khoảng cách vừa phải với bảng Facts phía trên
                }
            )

        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",  # Khai báo với Teams đây là thẻ Adaptive
                    "content": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.4",  # Phiên bản tính năng thẻ của Teams
                        "body": body_elements,  # Toàn bộ nội dung phần trên: tiêu đề, bảng, nội dung
                        "actions": [
                            {
                                "type": "Action.OpenUrl",  # Ra lệnh cho Teams vẽ ra một cái Nút bấm (Action Button)
                                "title": "View in Backlog",
                                "url": backlog_url,
                            }
                        ],
                    },
                }
            ],
        }
        return payload

    async def send_notification(self, notification: BacklogNotification) -> bool:
        # Determine payload type based on webhook target URL
        is_power_automate = (
            "powerplatform.com" in self.webhook_url or "powerautomate" in self.webhook_url
        )

        comment_count = None
        if notification.issue:
            try:
                from services.backlog_service import BacklogService

                backlog_service = BacklogService()
                comment_count = await backlog_service.fetch_issue_comment_count(
                    notification.issue.id
                )
            except Exception as e:
                logger.error(f"Failed to fetch comment count in send_notification: {e}")

        if is_power_automate:
            card_payload = self.build_adaptive_card_payload(
                notification, comment_count=comment_count
            )
        else:
            card_payload = self.build_message_card(notification, comment_count=comment_count)

        logger.debug(
            f"Sending card to Teams for notification ID {notification.id} (Format: {'AdaptiveCard' if is_power_automate else 'MessageCard'})"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.webhook_url, json=card_payload)

                # Check for Teams/PowerAutomate webhook return code (accept all 2xx success codes, like 200 OK or 202 Accepted)
                if 200 <= response.status_code < 300:
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
