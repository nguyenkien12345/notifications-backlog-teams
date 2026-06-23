import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.scheduler import scheduler
from services.state_service import StateService
from services.sync_service import SyncService

# Tạo một người ghi nhật ký riêng cho file này với cái tên là "api_webhook". Bạn sẽ biết lỗi hay thông tin này xuất phát từ file này
logger = logging.getLogger("api_webhook")
# Tất cả các đường link API trong file này sẽ được gắn vào cái router này để sau này nạp vào file chạy chính (main.py)
router = APIRouter()

# Phân biệt 2 thằng SyncService và StateService
# ========== SyncService ==========
# + Đặc điểm: Dịch vụ đồng bộ
# + Nhiệm vụ chính: Hành động & Kết nối. Đi lấy dữ liệu từ nơi này chuyển sang nơi khác
# + Nơi nó tương tác: Đi ra ngoài Internet (gọi API của Backlog, gửi Webhook tới Teams)
# + Tốc độ xử lý: Chậm hơn (vì phải đợi mạng Internet phản hồi)
# + Từ khóa hành động: Quét thông báo, gửi tin nhắn, đồng bộ, kết nối...

# ========== StateService ==========
# + Đặc điểm: Dịch vụ trạng thái
# + Nhiệm vụ chính: Lưu trữ & Nhớ thông tin. Đọc và ghi dữ liệu cấu hình/lịch sử vào file (ví dụ state.json)
# + Nơi nó tương tác: Làm việc nội bộ ở ổ cứng máy tính (Đọc/Ghi file cục bộ)
# + Tốc độ xử lý: Rất nhanh (vì chỉ đọc ghi file trên máy)
# + Từ khóa hành động: Lưu lịch sử, đọc trạng thái cũ, cập nhật số lượng...

# Giải thích ý nghĩa của dòng: response_model=SyncResponse
# + FastAPI sẽ tự động lọc bỏ các dữ liệu thừa và trả về đúng cấu trúc của class SyncResponse (Chỉ trả về các trường status, message, synced_count)
# (VD trong trường hợp api trả dư trường secret_data, secret_key thì thằng response_model này sẽ không trả về 2 trường đó)
# + Trong trường hợp trả thiếu trường vd như trường synced_count không được trả về thì cũng sẽ báo lỗi response validation
# + Nó cũng hỗ trợ Convert kiểu dữ liệu. Vd trường synced_count có kiểu dữ liệu là int mà trong code đang trả về chuỗi "5" thì nó cũng sẽ tự động thực hiện convert "5" -> 5 để trả về cho người dùng

# Giải thích ý nghĩa của option deprecated=True (Đánh dấu API đã lỗi thời)
# Trong quá trình phát triển, nếu bạn viết một API mới ngon hơn và không muốn người khác dùng API cũ này nữa (nhưng chưa xóa hẳn vì sợ lỗi hệ thống cũ), bạn có thể đánh dấu nó là lỗi thời.

# Giải thích ý nghĩa của option include_in_schema=False (Giấu API khỏi trang tài liệu)
# Có những API bạn chỉ muốn dùng nội bộ, hoặc dùng để test ngầm và không muốn bất kỳ ai nhìn thấy nó trên trang tài liệu hướng dẫn công khai


class SyncResponse(BaseModel):
    status: str
    message: str
    synced_count: int


@router.post(
    "/sync",
    status_code=status.HTTP_200_OK,
    summary="Manually trigger synchronization",
    tags=["Bot Management"],
    response_model=SyncResponse,
)
async def trigger_sync():
    logger.info("Manual synchronization triggered via API.")
    try:
        sync_service = SyncService()
        synced_count = await sync_service.sync_now()

        return {
            "status": "success",
            "message": f"Successfully synchronized {synced_count} notifications.",
            "synced_count": synced_count,
        }
    except Exception as e:
        logger.error(f"Manual synchronization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synchronization failed: {e!s}",
        ) from e


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    summary="Get current sync bot status",
    tags=["System System"],
)
async def get_status():
    try:
        state_service = StateService()
        state = state_service.get_state()

        return {
            "status": "healthy",
            "scheduler_running": scheduler.running,
            "sync_details": state.model_dump(),
        }
    except Exception as e:
        logger.error(f"Failed to retrieve sync status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load status: {e!s}",
        ) from e
