from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime

class SyncState(BaseModel):
    # ID của thông báo cuối cùng đã xử lý: Lưu lại ID (mã số định danh) của thông báo cuối cùng trên Backlog mà Bot đã đọc và gửi sang Teams
    last_processed_notification_id: int = Field(default=0, description="The ID of the last processed/forwarded notification.")

    # Mốc thời gian lần đồng bộ cuối cùng
    # Giá trị mặc định là None (Rỗng). Khi Bot mới tinh chưa chạy lần nào, nó sẽ không có mốc thời gian lần chạy cuối, nên để None là hợp lý nhất. Sau khi chạy xong, nó sẽ được cập nhật thành một chuỗi chữ dạng thời gian
    last_sync_time: Optional[str] = Field(default=None, description="ISO timestamp of the last executed sync job.")

    # Số lần đồng bộ thành công
    successful_syncs_count: int = Field(default=0, description="Number of successful sync iterations.")

    # Số lần đồng bộ thất bại
    failed_syncs_count: int = Field(default=0, description="Number of failed sync iterations.")
