import logging

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# (pydantic) SecretStr: Secure string type that hides sensitive values in logs and debug output.
# (pydantic) Field: Defines validation rules, defaults, and metadata for a model field.

# Giải thích ý nghĩa của dòng: BACKLOG_SPACE_ID: str = Field(..., alias="BACKLOG_SPACE_ID")
# - BACKLOG_SPACE_ID: str => Khai báo biến BACKLOG_SPACE_ID phải là kiểu chuỗi chữ (str - string).
# - Field(...): Dấu ba chấm ... có nghĩa là bắt buộc phải có (tương đương với required). Nếu trong file .env thiếu biến này, chương trình sẽ báo lỗi ngay lập tức và dừng lại.
# - alias="BACKLOG_SPACE_ID": Tên bí danh. Khi nó đi tìm trong file .env, nó sẽ tìm chữ viết hoa BACKLOG_SPACE_ID.

# Giải thích ý nghĩa của dòng: BACKLOG_DOMAIN: str = Field("backlog.com", alias="BACKLOG_DOMAIN")
# - Field("backlog.com", ...): Khác với dấu ba chấm, ở đây điền sẵn chữ "backlog.com". Đây chính là giá trị mặc định. Nếu trong file .env bạn không khai báo BACKLOG_DOMAIN, chương trình sẽ tự động lấy giá trị này.

# Giải thích ý nghĩa của dòng: ONLY_UNREAD: bool = Field(True, alias="ONLY_UNREAD")
# - Kiểu dữ liệu Đúng/Sai (bool - boolean). Ở đây mặc định là True (Đúng) – có nghĩa là hệ thống mặc định chỉ quét các thông báo chưa đọc.

# Giải thích ý nghĩa của đoạn cấu hình dưới đây:
# - env_file=".env": Chỉ định cho Pydantic biết: "Hãy tìm và đọc các giá trị từ file có tên là .env nằm ở thư mục gốc".
# - env_file_encoding="utf-8": Đọc file với font chữ chuẩn quốc tế UTF-8 (để nếu bạn có gõ tiếng Việt hay ký tự đặc biệt trong file .env cũng không bị lỗi).
# - extra="ignore": Nếu trong file .env bạn có lỡ tay viết thêm một vài biến lạ hoắc không có định nghĩa ở trên, chương trình sẽ bỏ qua (ignore) chứ không bắt lỗi.
# - populate_by_name=True: Cho phép bạn tạo cấu hình bằng cả hai cách: dùng tên biến trong code (BACKLOG_SPACE_ID) hoặc dùng tên bí danh (BACKLOG_SPACE_ID).
# model_config = SettingsConfigDict(
#     env_file=".env",
#     env_file_encoding="utf-8",
#     extra="ignore",
#     populate_by_name=True
# )

# Python sẽ thử tạo ra một đối tượng cụ thể tên là settings từ cái khuôn Settings ở trên. Quá trình này sẽ kích hoạt việc đọc file .env và kiểm tra xem có thiếu biến bắt buộc nào không, hoặc có biến nào sai kiểu dữ liệu không
# settings = Settings()


class Settings(BaseSettings):
    # Backlog Settings
    BACKLOG_SPACE_ID: str = Field(..., alias="BACKLOG_SPACE_ID")
    BACKLOG_API_KEY: SecretStr = Field(..., alias="BACKLOG_API_KEY")
    BACKLOG_DOMAIN: str = Field("backlog.com", alias="BACKLOG_DOMAIN")
    ONLY_UNREAD: bool = Field(True, alias="ONLY_UNREAD")

    # Teams Settings
    TEAMS_WEBHOOK_URL: SecretStr = Field(..., alias="TEAMS_WEBHOOK_URL")

    # Discord Settings
    DISCORD_WEBHOOK_URL: SecretStr | None = Field(None, alias="DISCORD_WEBHOOK_URL")

    # Bot Settings
    SYNC_INTERVAL_MINUTES: int = Field(5, alias="SYNC_INTERVAL_MINUTES")
    STATE_FILE_PATH: str = Field("storage/state.json", alias="STATE_FILE_PATH")
    LOG_LEVEL: str = Field("INFO", alias="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )


# Load settings instance
try:
    settings = Settings()
except Exception as e:
    # Set up temporary basic logging to show config loading errors
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("config")
    logger.warning(
        f"Configuration validation failed: {e}. "
        "Please ensure .env file is set up correctly with required variables."
    )
    # We allow the settings import to succeed but with partial defaults
    # by using dummy values, or we raise. Standard is to raise to fail-fast.
    raise e

# Perform validation of placeholders
logger = logging.getLogger("config")
if (
    settings.BACKLOG_SPACE_ID == "your-space-id"
    or settings.BACKLOG_API_KEY.get_secret_value() == "your-api-key"
):
    logger.warning(
        "Configuration loaded but placeholder values (e.g. 'your-space-id', 'your-api-key') were detected. Please update your .env file."
    )
