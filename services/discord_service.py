import logging
import re
from typing import Any

import httpx

from constants import DEFAULT_THEME_COLOR, THEME_COLORS
from core.config import settings
from models.backlog import BacklogNotification
from utils import build_backlog_url, truncate_text

logger = logging.getLogger("discord_service")


class DiscordService:
    def __init__(self):
        self.webhook_url = (
            settings.DISCORD_WEBHOOK_URL.get_secret_value()
            if settings.DISCORD_WEBHOOK_URL
            else None
        )

    def get_backlog_url(self, notification: BacklogNotification) -> str:
        return build_backlog_url(
            space_id=settings.BACKLOG_SPACE_ID,
            domain=settings.BACKLOG_DOMAIN,
            project_key=notification.project.projectKey if notification.project else None,
            issue_key=notification.issue.issueKey if notification.issue else None,
            comment_id=notification.comment.id if notification.comment else None,
            is_pull_request=bool(notification.pullRequest),
        )

    def get_theme_color(self, reason: int) -> int:
        hex_color = THEME_COLORS.get(reason, DEFAULT_THEME_COLOR)
        try:
            return int(hex_color, 16)
        except ValueError:
            return int(DEFAULT_THEME_COLOR, 16)

    def parse_description_sections(self, description: str) -> dict[str, str]:
        if not description:
            return {}

        description = description.replace("\r\n", "\n").replace("\r", "\n")

        headers = {
            "前提条件": ["前提条件", "再現の前提条件"],
            "手順": ["手順", "再現手順"],
            "結果": ["結果", "実際の結果", "再現結果"],
            "期待する動作": ["期待する動作", "期待した結果", "期待した動作"],
        }

        flat_headers = []
        header_to_key = {}
        for key, aliases in headers.items():
            for alias in aliases:
                flat_headers.append(alias)
                header_to_key[alias] = key

        header_pattern = re.compile(
            r"^(?P<prefix>[#*]*)\s*(?P<name>"
            + "|".join(re.escape(h) for h in flat_headers)
            + r")\s*$",
            re.MULTILINE,
        )

        matches = list(header_pattern.finditer(description))
        result = {}

        for idx, match in enumerate(matches):
            alias_name = match.group("name")
            key = header_to_key[alias_name]
            start_pos = match.end()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(description)
            content = description[start_pos:end_pos].strip()

            if key not in result or (not result[key] and content):
                result[key] = content

        return result

    def build_embed_payload(
        self, notification: BacklogNotification, comment_count: int | None = None
    ) -> dict[str, Any]:
        emoji = notification.get_action_emoji()
        reason_desc = notification.get_reason_description()
        sender_name = notification.sender.name if notification.sender else "Someone"

        title = f"{emoji} {sender_name} {reason_desc}"
        backlog_url = self.get_backlog_url(notification)
        color = self.get_theme_color(notification.reason)

        fields = []
        text_content = ""

        if notification.project:
            fields.append(
                {
                    "name": "Project",
                    "value": f"[{notification.project.name}]({backlog_url})",
                    "inline": True,
                }
            )

        if notification.issue:
            fields.append(
                {"name": "Issue Key", "value": notification.issue.issueKey, "inline": True}
            )
            fields.append(
                {
                    "name": "Summary",
                    "value": truncate_text(notification.issue.summary, max_length=250),
                    "inline": False,
                }
            )

            if notification.issue.createdUser:
                fields.append(
                    {
                        "name": "Created By",
                        "value": notification.issue.createdUser.name,
                        "inline": True,
                    }
                )
            if notification.issue.assignee:
                fields.append(
                    {"name": "Assignee", "value": notification.issue.assignee.name, "inline": True}
                )
            if notification.issue.status:
                fields.append(
                    {"name": "Status", "value": notification.issue.status.name, "inline": True}
                )
            if notification.issue.priority:
                fields.append(
                    {"name": "Priority", "value": notification.issue.priority.name, "inline": True}
                )
            if comment_count is not None:
                fields.append(
                    {"name": "Total Comments", "value": str(comment_count), "inline": True}
                )

            if notification.comment and notification.comment.content:
                text_content = truncate_text(notification.comment.content, max_length=1000)
            elif notification.issue.description:
                parsed_sections = self.parse_description_sections(notification.issue.description)
                if parsed_sections:
                    formatted_parts = []
                    for section_title, content in parsed_sections.items():
                        if content:
                            truncated_content = truncate_text(content, max_length=500)
                            formatted_parts.append(f"**{section_title}:**\n{truncated_content}")
                    text_content = "\n\n".join(formatted_parts)
                else:
                    text_content = truncate_text(notification.issue.description, max_length=1000)

        elif notification.pullRequest:
            fields.append(
                {
                    "name": "PR Number",
                    "value": f"#{notification.pullRequest.number}",
                    "inline": True,
                }
            )
            fields.append(
                {
                    "name": "PR Title",
                    "value": truncate_text(notification.pullRequest.title, max_length=250),
                    "inline": False,
                }
            )

            if notification.comment and notification.comment.content:
                text_content = truncate_text(notification.comment.content, max_length=1000)
            elif notification.pullRequest.description:
                text_content = truncate_text(notification.pullRequest.description, max_length=1000)

        embed = {
            "title": title,
            "url": backlog_url,
            "color": color,
            "fields": fields,
            "footer": {"text": "Backlog Notification Bot"},
        }

        if text_content:
            embed["description"] = f"**Content:**\n\n{text_content}"

        payload = {"username": "Smart Reminder Bot", "embeds": [embed]}
        return payload

    async def send_notification(self, notification: BacklogNotification) -> bool:
        if not self.webhook_url:
            logger.debug("Discord webhook URL is not configured. Skipping Discord notification.")
            return True

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

        payload = self.build_embed_payload(notification, comment_count=comment_count)

        logger.debug(f"Sending embed to Discord for notification ID {notification.id}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(self.webhook_url, json=payload)
                if 200 <= response.status_code < 300:
                    logger.info(f"Successfully posted notification {notification.id} to Discord.")
                    return True
                else:
                    logger.error(
                        f"Failed to post to Discord Webhook: HTTP {response.status_code} - {response.text}"
                    )
                    return False
            except Exception as e:
                logger.error(f"Error occurred while posting to Discord Webhook: {e}")
                return False
