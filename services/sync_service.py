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
                # 0 ở đây có nghĩa là không có tin nào được đồng bộ
                return 0

            # 2. Filter notifications
            to_process = []
            for n in notifications:
                if n.id <= last_id:
                    # Bỏ qua
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
                # Trường hợp có tin mới (ví dụ có 5 tin), nhưng cả 5 tin này đều đã bị người dùng đọc mất rồi, khiến danh sách to_process trống rỗng.
                # Lúc này Bot sẽ tìm đến thông báo cuối cùng nằm ở cuối danh sách thô (notifications[-1]), lấy cái ID cao nhất của nó (highest_id) để cập nhật đè vào sổ. Mục đích là để lượt chạy sau Bot không phải quét lại 5 tin đã đọc này nữa.
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
                    # Nếu bạn có 10 tin, gửi được 5 tin thành công, đến tin số 6 mạng đột ngột bị đứt sập nguồn. Nhờ có ghi log, hệ thống đã kịp lưu lại mốc tin số 5. Lượt sau mạng có lại, Bot sẽ chạy tiếp từ tin số 6, hoàn toàn không bị gửi lặp lại 5 tin đầu tiên lên Teams!
                    self.state_service.update_state(last_processed_id=last_id)
                    synced_count += 1
                else:
                    # On failure, stop processing this batch to ensure we retry this notification next time
                    # Nếu tin nhắn hiện tại gửi sang Teams bị lỗi (thất bại), Bot sẽ lập tức dừng vòng lặp for (bằng lệnh return) ngay lập tức, không gửi tiếp các tin phía sau nữa vì
                    # khả năng cao các tin sau cũng sẽ lỗi. Bot dừng lại, ghi nhận ca làm việc này bị lỗi (increment_failure=True) để chờ 5 phút sau chạy lại, gửi lại đúng cái tin lỗi đó
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
