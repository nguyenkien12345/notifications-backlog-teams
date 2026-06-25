from pydantic import BaseModel, Field


class SyncState(BaseModel):
    last_processed_notification_id: int = Field(
        default=0, description="The ID of the last processed/forwarded notification."
    )

    last_sync_time: str | None = Field(
        default=None, description="ISO timestamp of the last executed sync job."
    )

    successful_syncs_count: int = Field(
        default=0, description="Number of successful sync iterations."
    )

    failed_syncs_count: int = Field(default=0, description="Number of failed sync iterations.")
