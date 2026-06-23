from pydantic import BaseModel

from constants import ACTION_EMOJIS, DEFAULT_ACTION_EMOJI, REASON_DESCRIPTIONS


class Project(BaseModel):
    id: int
    projectKey: str
    name: str


class Issue(BaseModel):
    id: int
    issueKey: str
    summary: str
    description: str | None = None


class Comment(BaseModel):
    id: int
    content: str | None = None
    created: str | None = None


class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    description: str | None = None


class User(BaseModel):
    id: int
    userId: str | None = None
    name: str
    mailAddress: str | None = None


class BacklogNotification(BaseModel):
    id: int
    alreadyRead: bool
    reason: int
    created: str
    project: Project | None = None
    issue: Issue | None = None
    comment: Comment | None = None
    pullRequest: PullRequest | None = None
    sender: User | None = None
    user: User | None = None

    def get_reason_description(self) -> str:
        """
        Map Backlog notification reason code to human-readable string.
        Reference: https://backlog.com/developer/api/2/get-notification/
        """
        return REASON_DESCRIPTIONS.get(
            self.reason, f"triggered an action (reason code: {self.reason})"
        )

    def get_action_emoji(self) -> str:
        """Return an emoji based on the reason code to make notifications visually engaging."""
        return ACTION_EMOJIS.get(self.reason, DEFAULT_ACTION_EMOJI)
