import logging
from datetime import datetime

from core.config import settings
from services.backlog_service import BacklogService
from services.state_service import StateService
from services.teams_service import TeamsService

logger = logging.getLogger("sync_service")


class SyncService:
    def __init__(self):
        self.backlog_service = BacklogService()
        self.teams_service = TeamsService()
        self.state_service = StateService()

    async def sync_now(self) -> int:
        """
        Executes a single synchronization loop.

        Returns:
            int: The number of new notifications successfully synced.
        """
        current_time = datetime.now().isoformat()
        state = self.state_service.get_state()
        last_id = state.last_processed_notification_id

        logger.info(f"Starting synchronization check. Last processed notification ID: {last_id}")

        try:
            # 1. Fetch notifications starting from the last processed ID
            notifications = await self.backlog_service.fetch_notifications(min_id=last_id)

            if not notifications:
                logger.info("No new notifications found in Backlog.")
                self.state_service.update_state(last_sync_time=current_time, increment_success=True)
                return 0

            # 2. Filter notifications
            to_process = []
            for n in notifications:
                # Extra check to ensure ID is strictly greater (though Backlog API minId does this, it's good safety)
                if n.id <= last_id:
                    continue
                # If ONLY_UNREAD is enabled, skip notifications that are already read
                if settings.ONLY_UNREAD and n.alreadyRead:
                    logger.debug(f"Skipping notification {n.id} because it is already read.")
                    continue
                to_process.append(n)

            if not to_process:
                logger.info(
                    "New notifications exist but none matched the unread/processing criteria."
                )
                # We can update the state to the highest ID fetched, since they are all read/filtered out anyway.
                highest_id = notifications[-1].id
                self.state_service.update_state(
                    last_processed_id=highest_id,
                    last_sync_time=current_time,
                    increment_success=True,
                )
                return 0

            logger.info(f"Found {len(to_process)} new notifications to sync.")
            synced_count = 0

            # 3. Process and forward notifications sequentially
            for notification in to_process:
                # Attempt to push to MS Teams
                success = await self.teams_service.send_notification(notification)

                if success:
                    # Update state sequentially so if the next one fails, we don't lose progress
                    last_id = notification.id
                    self.state_service.update_state(last_processed_id=last_id)
                    synced_count += 1
                else:
                    # On failure, stop processing this batch to ensure we retry this notification next time
                    logger.error(
                        f"Failed to deliver notification {notification.id} to Teams webhook. "
                        f"Aborting rest of the batch to retry on next run. Successfully synced in this run: {synced_count}."
                    )
                    self.state_service.update_state(
                        last_sync_time=current_time, increment_failure=True
                    )
                    return synced_count

            # 4. Finalize state
            self.state_service.update_state(last_sync_time=current_time, increment_success=True)
            logger.info(
                f"Synchronization complete. Successfully forwarded {synced_count} notifications."
            )
            return synced_count

        except Exception as e:
            logger.error(f"Error occurred during synchronization check: {e}", exc_info=True)
            self.state_service.update_state(last_sync_time=current_time, increment_failure=True)
            raise e
