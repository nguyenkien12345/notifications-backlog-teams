# - Dấu chấm . đại diện cho "Thư mục hiện tại" được gọi là Relative Import (Import tương đối)
# => Hãy nhìn ngay vào thư mục hiện tại (thư mục chứa file __init__.py này). Ở đó có file nào tên là notification.py không ?
# Nếu có, hãy vào đó lấy các biến ra cho tôi.

# - Vì cả 3 file __init__ và docs và notification đều cùng nằm trong 1 thư mục là constants và cùng một cấp nên dùng dấu . là hợp lý

# - Nếu bạn bỏ dấu chấm đi và viết khơi khơi là from notification import ..., Python sẽ hiểu đây là Absolute Import (Import tuyệt đối).
# Lúc này, Python sẽ không tìm kiếm trong thư mục hiện tại nữa. Thay vào đó, nó sẽ chạy ra ngoài hệ thống toàn cục,
# quét qua danh sách các thư viện bạn cài bằng lệnh pip (giống như fastapi, pydantic...) để tìm xem có thư viện nào tên là notification hay không.
# Dễ dẫn đến 2 lỗi sau đây:
# - Lỗi sập nguồn (ModuleNotFoundError): Vì notification là file bạn tự viết chứ không phải thư viện quốc tế,
# Python tìm bên ngoài không thấy sẽ báo lỗi ngay lập tức.

# - Lỗi nhận nhầm (Xung đột tên): Giả sử sau này bạn cài một thư viện bên ngoài cũng tên là notification,
# Python sẽ bị bối rối và lấy nhầm code của thư viện đó thay vì file code do chính bạn viết.

from .docs import (
    TAGS_METADATA,
)
from .notification import (
    ACTION_EMOJIS,
    DEFAULT_ACTION_EMOJI,
    DEFAULT_THEME_COLOR,
    REASON_DESCRIPTIONS,
    THEME_COLORS,
)

__all__ = [
    "ACTION_EMOJIS",
    "DEFAULT_ACTION_EMOJI",
    "DEFAULT_THEME_COLOR",
    "REASON_DESCRIPTIONS",
    "TAGS_METADATA",
    "THEME_COLORS",
]
