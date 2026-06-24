import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from core.config import settings
from services.sync_service import SyncService

logger = logging.getLogger("scheduler")

# Create a single global instance of the scheduler
scheduler = AsyncIOScheduler()


async def sync_job():
    """Job function wrapper that runs the sync process."""
    logger.info("Executing scheduled sync job...")
    try:
        sync_service = SyncService()
        await sync_service.sync_now()
    except Exception as e:
        logger.error(f"Scheduled sync job failed: {e}")


def start_scheduler():
    """Initializes and starts the background scheduler."""
    if not scheduler.running:
        interval = settings.SYNC_INTERVAL_MINUTES
        logger.info(f"Starting background scheduler. Sync interval: {interval} minutes.")

        # Add interval job
        scheduler.add_job(
            sync_job,  # Do something (Chú ý: truyền tên hàm, không có dấu ngoặc tròn ())
            "interval",  # Chế độ lặp đi lặp lại định kỳ (cứ sau mỗi khoảng thời gian cố định)
            minutes=interval,  # Khoảng thời gian lặp lại
            id="backlog_sync_job",  # Đặt id cho job này để phân biệt nếu sau này dự án của bạn có thêm các công việc (job) chạy ngầm khác (như job dọn dẹp log, job báo cáo tuần...)
            replace_existing=True,  # Nếu trong bộ nhớ lỡ có một cấu hình cũ trùng tên ID này, hãy xóa nó đi và đè cái mới này lên để tránh xung đột
        )

        scheduler.start()
    else:
        logger.warning("Scheduler is already running.")


def stop_scheduler():
    """Shuts down the background scheduler."""
    if scheduler.running:
        logger.info("Stopping background scheduler.")
        scheduler.shutdown()
        logger.info("Background scheduler stopped successfully.")
