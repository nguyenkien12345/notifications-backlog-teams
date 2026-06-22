# Mapping of Backlog notification reason codes to human-readable action descriptions.
# Reference: https://backlog.com/developer/api/2/get-notification/
REASON_DESCRIPTIONS = {
    1: "assigned you an issue",
    2: "sent you a notification (mention)",
    3: "commented on an issue",
    4: "added an issue",
    5: "updated/related activity on an issue",
    6: "assigned you a pull request",
    7: "sent you a pull request notification (mention)",
    8: "commented on a pull request",
    9: "added a pull request",
    10: "updated a pull request",
    11: "related activity on a pull request",
}

# Emojis associated with notification reasons to make Teams alerts visually engaging.
ACTION_EMOJIS = {
    1: "📥",   # Assigned
    2: "🔔",   # Mention
    3: "💬",   # Comment
    4: "➕",   # Issue Added
    5: "🔄",   # Issue Updated
    6: "🧑‍💻", # PR Assigned
    7: "🔔",   # PR Mention
    8: "💬",   # PR Comment
    9: "🚀",   # PR Added
    10: "🔄",  # PR Updated
    11: "🔗",  # PR Related
}

# Hex color mapping for MS Teams card headers based on notification reason.
THEME_COLORS = {
    1: "E67E22",   # Orange (Assigned)
    2: "3498DB",   # Blue (Mention)
    3: "2ECC71",   # Green (Comment)
    4: "27AE60",   # Dark Green (Issue Added)
    5: "95A5A6",   # Gray (Issue Updated)
    6: "F1C40F",   # Yellow (PR Assigned)
    7: "3498DB",   # Blue (PR Mention)
    8: "2ECC71",   # Green (PR Comment)
    9: "9B59B6",   # Purple (PR Added)
    10: "8E44AD",  # Dark Purple (PR Updated)
    11: "BDC3C7",  # Light Gray (PR Related)
}

DEFAULT_THEME_COLOR = "7F8C8D"
DEFAULT_ACTION_EMOJI = "📢"
