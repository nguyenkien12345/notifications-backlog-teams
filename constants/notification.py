# Mapping of Backlog notification reason codes to human-readable action descriptions.
# Reference: https://developer.nulab.com/docs/backlog/api/2/get-notification/
REASON_DESCRIPTIONS = {
    1: "assigned you an issue",
    2: "commented on an issue",
    3: "added an issue",
    4: "updated/related activity on an issue",
    5: "attached a file to an issue",
    6: "added you to the project",
    9: "sent you a notification",
    10: "assigned you a pull request",
    11: "commented on a pull request",
    12: "added a pull request",
    13: "updated a pull request",
}

# Emojis associated with notification reasons to make Teams alerts visually engaging.
ACTION_EMOJIS = {
    1: "📥",  # Assigned
    2: "💬",  # Comment
    3: "➕",  # Issue Created
    4: "🔄",  # Issue Updated
    5: "📎",  # File Attached
    6: "👋",  # User Added to Project
    9: "🔔",  # Other
    10: "🧑‍💻",  # PR Assigned
    11: "💬",  # PR Comment
    12: "🚀",  # PR Created
    13: "🔄",  # PR Updated
}

# Hex color mapping for MS Teams card headers based on notification reason.
THEME_COLORS = {
    1: "E67E22",  # Orange (Assigned)
    2: "2ECC71",  # Green (Comment)
    3: "27AE60",  # Dark Green (Issue Created)
    4: "95A5A6",  # Gray (Issue Updated)
    5: "BDC3C7",  # Light Gray (File Attached)
    6: "3498DB",  # Blue (User Added)
    9: "7F8C8D",  # Gray (Other)
    10: "F1C40F",  # Yellow (PR Assigned)
    11: "2ECC71",  # Green (PR Comment)
    12: "9B59B6",  # Purple (PR Created)
    13: "8E44AD",  # Dark Purple (PR Updated)
}

DEFAULT_THEME_COLOR = "7F8C8D"
DEFAULT_ACTION_EMOJI = "📢"
