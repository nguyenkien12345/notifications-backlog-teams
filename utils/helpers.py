from typing import Optional

def truncate_text(text: Optional[str], max_length: int = 500, suffix: str = "...") -> str:
    if not text:
        return ""
    # Kiểm tra tổng số ký tự của đoạn văn (len(text)). Nếu nó dài hơn số lượng tối đa cho phép (max_length)
    if len(text) > max_length:
        # Nó sẽ lấy từ ký tự đầu tiên (vị trí số 0) cho đến ký tự thứ max_length (ví dụ: ký tự thứ 500) kết hợp với suffix
        return text[:max_length] + suffix
    return text


def build_backlog_url(
    # Mã định danh không gian Backlog
    space_id: str,
    # Tên miền mặc định của Backlog
    domain: str,
    # Mã dự án (ví dụ: PROJ) (Không bắt buộc)
    project_key: Optional[str] = None,
    # Mã công việc cụ thể (ví dụ: PROJ-123)
    issue_key: Optional[str] = None,
    # ID của bình luận cụ thể bên trong công việc
    comment_id: Optional[int] = None,
    # Đánh dấu xem đây có phải là link dẫn đến trang Git Pull Request (yêu cầu duyệt code) hay không
    is_pull_request: bool = False,
) -> str:
    # Nếu người dùng nhập đầy đủ có dấu chấm (ví dụ: my-space.backlog.com), hệ thống chỉ cần thêm https:// vào đầu thành: https://my-space.backlog.com
    if "." in space_id:
        base_url = f"https://{space_id}"
    # Nếu người dùng chỉ nhập chữ ngắn gọn (ví dụ: my-space), hệ thống sẽ tự ráp thêm tên miền vào thành: https://my-space.backlog.com
    else:
        base_url = f"https://{space_id}.{domain}"

    # Trường hợp 1 (Ưu tiên cao nhất): Nếu có truyền vào issue_key (tức là muốn link dẫn đến một công việc cụ thể).
    if issue_key:
        # Nó sẽ tạo ra đường link dạng: https://my-space.backlog.com/view/PROJ-123.
        url = f"{base_url}/view/{issue_key}"
        if comment_id:
            # Nếu có kèm theo cả ID bình luận, nó sẽ cộng dồn thêm (url += ...) cái đuôi định vị bình luận vào sau link. Kết quả trả về sẽ là: https://my-space.backlog.com/view/PROJ-123#comment-9999
            url += f"#comment-{comment_id}"
        return url
    # Nếu không có issue_key, nhưng biến is_pull_request bằng True VÀ có mã dự án project_key. Hàm hiểu là bạn muốn vào trang quản lý code Git của dự án đó. Link trả về sẽ là: https://my-space.backlog.com/projects/PROJ/git
    elif is_pull_request and project_key:
        return f"{base_url}/projects/{project_key}/git"
    # Nếu chỉ có mỗi mã dự án project_key thô thôi (không phải công việc, không phải pull request). Hàm sẽ dẫn người dùng về trang chủ của dự án đó: https://my-space.backlog.com/projects/PROJ.
    elif project_key:
        return f"{base_url}/projects/{project_key}"
        
    return base_url
