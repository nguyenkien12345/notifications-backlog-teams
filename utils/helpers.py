def truncate_text(text: str | None, max_length: int = 500, suffix: str = "...") -> str:
    if not text:
        return ""

    if len(text) > max_length:
        return text[:max_length] + suffix
    return text


def build_backlog_url(
    space_id: str,
    domain: str,
    project_key: str | None = None,
    issue_key: str | None = None,
    comment_id: int | None = None,
    is_pull_request: bool = False,
) -> str:
    base_url = f"https://{space_id}" if "." in space_id else f"https://{space_id}.{domain}"

    if issue_key:
        url = f"{base_url}/view/{issue_key}"
        if comment_id:
            url += f"#comment-{comment_id}"
        return url
    elif is_pull_request and project_key:
        return f"{base_url}/projects/{project_key}/git"
    elif project_key:
        return f"{base_url}/projects/{project_key}"

    return base_url
