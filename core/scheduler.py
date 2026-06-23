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
            sync_job, "interval", minutes=interval, id="backlog_sync_job", replace_existing=True
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
