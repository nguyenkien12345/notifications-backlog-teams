import logging
import re
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
        return THEME_COLORS.get(reason, DEFAULT_THEME_COLOR)

    def parse_description_sections(self, description: str) -> dict[str, str]:
        if not description:
            return {}

        # Chuẩn hóa toàn bộ ký tự xuống dòng từ các hệ điều hành khác nhau về định dạng \n
        description = description.replace("\r\n", "\n").replace("\r", "\n")

        # - Định nghĩa danh sách các tiêu đề (section header) có thể xuất hiện trong phần mô tả.
        # - Key của dictionary là tên section chuẩn mà hệ thống sẽ sử dụng trong kết quả trả về.
        # - Value là danh sách các biến thể (alias) của cùng một section do người dùng có thể nhập
        # theo nhiều cách khác nhau trong ticket.
        #
        # Ví dụ:
        # - "手順" và "再現手順" đều mang ý nghĩa là các bước tái hiện lỗi (Steps to Reproduce),
        #   nên sẽ được quy về cùng một key chuẩn là "手順".
        # - "結果", "実際の結果" và "再現結果" đều mô tả kết quả thực tế khi thực hiện thao tác,
        #   nên sẽ được quy về key chuẩn là "結果".
        #
        # Việc chuẩn hóa này giúp parser có thể nhận diện và xử lý được nhiều định dạng ticket khác nhau
        # nhưng vẫn trả về cấu trúc dữ liệu thống nhất để các bước xử lý phía sau sử dụng.

        headers = {
            "前提条件": ["前提条件", "再現の前提条件"],
            "手順": ["手順", "再現手順"],
            "結果": ["結果", "実際の結果", "再現結果"],
            "期待する動作": ["期待する動作", "期待した結果", "期待した動作"],
        }

        flat_headers = []
        header_to_key = {}
        for key, aliases in headers.items():
            # key = "前提条件"
            # aliases = ["前提条件", "再現の前提条件"]
            for alias in aliases:
                flat_headers.append(alias)
                header_to_key[alias] = key

        # Output:
        # flat_headers = ["前提条件", "再現の前提条件", "手順", "再現手順", "結果", "実際の結果", "再現結果", "期待する動作", "期待した結果", "期待した動作"]

        # header_to_key = [
        #   "前提条件": "前提条件",
        #   "再現の前提条件": "前提条件",

        #   "手順": "手順",
        #   "再現手順": "手順",

        #   "結果": "結果",
        #   "実際の結果": "結果",
        #   "再現結果": "結果",

        #   "期待する動作": "期待する動作",
        #   "期待した結果": "期待する動作",
        #   "期待した動作": "期待する動作",
        # ]

        # re.compile: Tìm tất cả các tiêu đề section
        # compile dùng để: Regex string => Biên dịch thành Regex Object => Dùng đi dùng lại nhiều lần
        # + ^: Bắt đầu dòng
        # + (?P<prefix>#*): Đây là một Named Group được đặt tên là prefix. Lưu phần match được vào biến tên prefix. VD: ### 結果 thì match.group("prefix") sẽ trả ra chuỗi là "###"
        # + #*: 0 hoặc nhiều ký tự #. Sử dụng dấu # để parse được markdown. Nếu không có #* thì regex sẽ không nhận diện được các header markdown. VD: #, ##, ###, ####, thậm chí là rỗng
        # + \s*: 0 hoặc nhiều ký tự khoảng trắng. VD: "", " ", "   ", "\t"
        # + ?P<name>: Đây là một Named Group được đặt tên là name. Lưu phần match được vào biến tên name. VD: ### 結果 thì match.group("name") sẽ trả ra chuỗi là "結果"
        # + Bên trong group name: "|".join(re.escape(h) for h in flat_headers). VD: flat_headers = ["前提条件", "手順", "結果"] thì sinh ra "|".join => "前提条件|手順|結果"
        # + (?P<name>前提条件|手順|結果) => Match vào tên header => Match một trong các giá trị sau: 前提条件 hoặc 手順 hoặc 結果
        # + \s*$: Cho phép khoảng trắng cuối dòng rồi kết thúc dòng
        # + re.MULTILINE: Nếu không có re.MULTILINE thì chỉ áp dụng cho: đầu toàn bộ chuỗi và cuối toàn bộ chuỗi. Có re.MULTILINE thì áp dụng cho: đầu mỗi dòng và cuối mỗi dòng

        header_pattern = re.compile(
            r"^(?P<prefix>#*)\s*(?P<name>"
            + "|".join(re.escape(h) for h in flat_headers)
            + r")\s*$",
            re.MULTILINE,
        )

        # Ví dụ thực tế
        # Description:

        # # 前提条件
        # # Windows 11

        # ## 手順
        # Open Chrome

        # ### 結果
        # Error happens

        # ### 期待する動作
        # No error

        # Regex sẽ tìm được 4 match.

        # Match 1
        # # 前提条件
        # Groups:
        # prefix = "#"
        # name = "前提条件"

        # Match 2
        # ## 手順
        # Groups:
        # prefix = "##"
        # name = "手順"

        # Match 3
        # ### 結果
        # Groups:
        # prefix = "###"
        # name = "結果"

        # Match 4
        # ### 期待する動作
        # Groups:
        # prefix = "###"
        # name = "期待する動作"

        # Sau khi chạy matches = list(header_pattern.finditer(description)) ta sẽ có 4 match:
        # Match 0: # 前提条件
        # Match 1: ## 手順
        # Match 2: ### 結果
        # Match 3: ### 期待する動作
        # finditer() trả về Iterator[Match]
        matches = list(header_pattern.finditer(description))

        result = {}

        # Vòng lặp tự động đếm số thứ tự tăng dần từ 1, 2, 3... giúp bạn biết chính xác có tổng cộng bao nhiêu item
        for idx, match in enumerate(matches):
            # VD: match là ### 結果 thì alias_name sẽ là 結果, key sẽ là 結果
            alias_name = match.group("name")
            key = header_to_key[alias_name]

            # Ví dụ:
            # ### 結果
            # |
            # Con trỏ đứng ở đây.
            start_pos = (
                match.end()
            )  # Vị trí kết thúc của Header hiện tại (bắt đầu phần nội dung bên dưới nó)

            # start() nghĩa là: vị trí bắt đầu của header tiếp theo. Nếu là Header cuối cùng, lấy đến hết chuỗi.
            # Ví dụ:
            # ### 期待する動作
            # No error
            # ^
            # Con trỏ đứng tại đây.
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(description)

            content = description[
                start_pos:end_pos
            ].strip()  # Đây là slicing string. Cắt từ start_pos đến trước end_pos. Kết quả là No error. strip sẽ xoá space, tab, newline ở đầu cuối

            # Chỉ lưu section lần đầu tiên, hoặc thay thế nếu giá trị cũ đang rỗng còn giá trị mới có nội dung.
            if key not in result or (not result[key] and content):
                result[key] = content

        return result

    def build_message_card(
        self, notification: BacklogNotification, comment_count: int | None = None
    ) -> dict[str, Any]:
        emoji = notification.get_action_emoji()
        reason_desc = notification.get_reason_description()
        sender_name = notification.sender.name if notification.sender else "Someone"

        title = f"{emoji} {sender_name} {reason_desc}"

        theme_color = self.get_theme_color(notification.reason)
        backlog_url = self.get_backlog_url(notification)

        facts = []
        text_content = ""
        subtitle = ""

        if notification.project:
            facts.append(
                {"name": "Project", "value": f"[{notification.project.name}] ({backlog_url})"}
            )
            subtitle = notification.project.name

        if notification.issue:
            facts.append({"name": "Issue Key", "value": notification.issue.issueKey})
            facts.append({"name": "Summary", "value": notification.issue.summary})

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

            if notification.comment and notification.comment.content:
                text_content = truncate_text(notification.comment.content, max_length=500)
            elif notification.issue.description:
                parsed_sections = self.parse_description_sections(notification.issue.description)
                if parsed_sections:
                    formatted_parts = []
                    for title, content in parsed_sections.items():
                        if content:
                            truncated_content = truncate_text(content, max_length=500)
                            formatted_parts.append(f"**{title}:**\n{truncated_content}")
                    text_content = "\n\n".join(formatted_parts)
                else:
                    text_content = truncate_text(notification.issue.description, max_length=500)

        elif notification.pullRequest:
            facts.append({"name": "PR Number", "value": f"#{notification.pullRequest.number}"})
            facts.append({"name": "PR Title", "value": notification.pullRequest.title})
            subtitle = f"PR #{notification.pullRequest.number} - {notification.pullRequest.title}"

            if notification.comment and notification.comment.content:
                text_content = truncate_text(notification.comment.content, max_length=500)
            elif notification.pullRequest.description:
                text_content = truncate_text(notification.pullRequest.description, max_length=500)

        section: dict[str, Any] = {
            "activityTitle": title,
            "activitySubtitle": subtitle,
            "markdown": True,
            "facts": facts,
        }

        if text_content:
            section["text"] = f"**Content:**\n\n{text_content}"

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

        title = f"{emoji} {sender_name} {reason_desc}"

        backlog_url = self.get_backlog_url(notification)

        facts = []
        subtitle = ""
        text_content = ""

        if notification.project:
            facts.append({"title": "Project", "value": notification.project.name})
            subtitle = notification.project.name

        if notification.issue:
            facts.append({"title": "Issue Key", "value": notification.issue.issueKey})
            facts.append({"title": "Summary", "value": notification.issue.summary})

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
                text_content = truncate_text(notification.comment.content, max_length=500)
            elif notification.issue.description:
                parsed_sections = self.parse_description_sections(notification.issue.description)
                if parsed_sections:
                    formatted_parts = []
                    for title, content in parsed_sections.items():
                        if content:
                            truncated_content = truncate_text(content, max_length=500)
                            formatted_parts.append(f"**{title}:**\n{truncated_content}")
                    text_content = "\n\n".join(formatted_parts)
                else:
                    text_content = truncate_text(notification.issue.description, max_length=500)

        elif notification.pullRequest:
            facts.append({"title": "PR Number", "value": f"#{notification.pullRequest.number}"})
            facts.append({"title": "PR Title", "value": notification.pullRequest.title})
            subtitle = f"PR #{notification.pullRequest.number} - {notification.pullRequest.title}"

            if notification.comment and notification.comment.content:
                text_content = truncate_text(notification.comment.content, max_length=500)
            elif notification.pullRequest.description:
                text_content = truncate_text(notification.pullRequest.description, max_length=500)

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
