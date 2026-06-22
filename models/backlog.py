from typing import Optional, Any
from pydantic import BaseModel, Field
from constants import REASON_DESCRIPTIONS, ACTION_EMOJIS, DEFAULT_ACTION_EMOJI

class Project(BaseModel):
    id: int
    projectKey: str
    name: str

class Issue(BaseModel):
    id: int
    issueKey: str
    summary: str
    description: Optional[str] = None

class Comment(BaseModel):
    id: int
    content: Optional[str] = None
    created: Optional[str] = None

class PullRequest(BaseModel):
    id: int
    number: int
    title: str
    description: Optional[str] = None

class User(BaseModel):
    id: int
    userId: Optional[str] = None
    name: str
    mailAddress: Optional[str] = None

class BacklogNotification(BaseModel):
    id: int
    alreadyRead: bool
    reason: int
    created: str
    project: Optional[Project] = None
    issue: Optional[Issue] = None
    comment: Optional[Comment] = None
    pullRequest: Optional[PullRequest] = None
    sender: Optional[User] = None
    user: Optional[User] = None

    def get_reason_description(self) -> str:
        """
        Map Backlog notification reason code to human-readable string.
        Reference: https://backlog.com/developer/api/2/get-notification/
        """
        return REASON_DESCRIPTIONS.get(self.reason, f"triggered an action (reason code: {self.reason})")

    def get_action_emoji(self) -> str:
        """Return an emoji based on the reason code to make notifications visually engaging."""
        return ACTION_EMOJIS.get(self.reason, DEFAULT_ACTION_EMOJI)

