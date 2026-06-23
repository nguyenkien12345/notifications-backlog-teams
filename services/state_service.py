import json
import logging
import os
from pathlib import Path

from core.config import settings
from models.state import SyncState

logger = logging.getLogger("state_service")


class StateService:
    def __init__(self, state_file_path: str | None = None):
        # - Nếu lúc gọi hàm bạn truyền vào một đường dẫn riêng, nó sẽ xài đường dẫn đó. Nếu không truyền (để trống), nó tự lấy đường dẫn mặc định trong .env là STATE_FILE_PATH
        # - Hàm Path(...) bọc ngoài để biến chuỗi này thành đối tượng Path thông minh
        self.state_file_path = Path(state_file_path or settings.STATE_FILE_PATH)
        # - Dấu gạch dưới _ ở đầu (Protected/Internal convention) báo đây là một biến "nội bộ" (Private), các file bên ngoài không nên tự ý đụng vào
        self._cached_state: SyncState | None = None

    def get_state(self) -> SyncState:
        # - Kiểm tra xem biến self._cached_state có dữ liệu chưa (is not None). Nếu có rồi (tức là đã từng đọc file này một lần trước đó rồi), nó lập tức trả về luôn dữ liệu đó
        # - Đọc dữ liệu từ RAM nhanh hơn đọc từ ổ cứng (Disk) hàng nghìn lần
        if self._cached_state is not None:
            return self._cached_state

        # - Trường hợp file chưa tồn tại, file state.json chưa được sinh ra (not exists()):
        if not self.state_file_path.exists():
            logger.info(
                f"State file not found at {self.state_file_path}. Initializing default state."
            )

            # - Tạo ra một đối tượng bộ nhớ từ class SyncState()
            self._cached_state = SyncState()

            # - Lưu ngay cái file này xuống ổ cứng cho các lần sau
            self._save_to_disk(self._cached_state)

            return self._cached_state

        try:
            # - r chính là read (đọc)
            with open(self.state_file_path, encoding="utf-8") as f:
                # - Đọc và chuyển nội dung file JSON thành một cục Dictionary
                data = json.load(f)
                # - **data: Bóc vỏ cục Dictionary data ra để đổ vào Class SyncState
                self._cached_state = SyncState(**data)
                # - Lưu vào biến Cache rồi trả kết quả về
                return self._cached_state

        # - Nếu file state.json vô tình bị ai đó vào sửa bậy bạ hoặc bị lỗi chữ khiến cấu trúc JSON bị sai, thư viện json sẽ bắn ra lỗi JSONDecodeError
        except json.JSONDecodeError as jde:
            # - Hệ thống sẽ ghi log cảnh báo file bị lỗi (corrupted), sau đó tự động xóa bài làm lại từ đầu bằng cách đè một khuôn SyncState mặc định mới tinh lên để cứu vãn tình hình, không bị sập nguồn
            logger.warning(
                f"State file at {self.state_file_path} is corrupted: {jde}. Re-initializing state."
            )

            self._cached_state = SyncState()

            self._save_to_disk(self._cached_state)

            return self._cached_state

        except Exception as e:
            logger.error(
                f"Failed to read state file at {self.state_file_path}: {e}. Using default memory state."
            )

            # Chúng ta đang khai báo hàm get_state là luôn luôn trả về 1 đối tượng kiểu SyncState. Do đó, việc trả về một cái khuôn mặc định này sẽ không làm các file gọi get_state bị gãy logic hoặc bị lỗi vì nhận về dữ liệu rỗng (None)
            return SyncState()

    # - Sau khi SyncService làm việc xong, nó sẽ gọi hàm này để cập nhật thông tin mới vào sổ nhật ký.
    def update_state(
        self,
        last_processed_id: int | None = None,  # ID thông báo mới nhất vừa xử lý xong
        last_sync_time: str | None = None,  # Mốc thời gian vừa chạy xong
        increment_success: bool = False,  # Nếu bằng True, tăng số lần thành công lên 1
        increment_failure: bool = False,  # Nếu bằng True, tăng số lần thất bại lên 1
    ) -> SyncState:
        # - Lấy ra dữ liệu trạng thái hiện tại (hoặc từ RAM hoặc từ file)
        state = self.get_state()

        # - Người dùng truyền cái gì vào thì ta ghi đè/cộng dồn (+= 1) vào trường đó của cái khuôn dữ liệu state
        if last_processed_id is not None:
            state.last_processed_notification_id = last_processed_id
        if last_sync_time is not None:
            state.last_sync_time = last_sync_time
        if increment_success:
            state.successful_syncs_count += 1
        if increment_failure:
            state.failed_syncs_count += 1

        # - Cập nhật xong, ta cất dữ liệu mới vào biến Cache self._cached_state, sau đó gọi hàm ghi xuống ổ cứng _save_to_disk(state) để lưu lại vĩnh viễn, rồi trả kết quả mới về
        self._cached_state = state
        self._save_to_disk(state)
        return state

    # - Đây là hàm nội bộ (_ ở đầu)
    def _save_to_disk(self, state: SyncState) -> None:
        try:
            # - parents: Lấy thư mục cha chứa file (thư mục storage)
            # - .mkdir(parents=True, exist_ok=True): "Nếu thư mục storage này chưa có thì hãy tự động tạo ra nó luôn nhé. Nếu có rồi thì thôi đừng báo lỗi"
            self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

            # - Nếu bạn đang ghi file mà máy tính đột ngột bị mất điện hoặc sập nguồn, file state.json sẽ bị dở dang và hỏng hoàn toàn (corrupted). Chúng ta sẽ sử dụng một chiêu thức gọi là Ghi file nguyên tử (Atomic Write)

            # - Ghi vào file tạm. Thay vì ghi trực tiếp vào file chính state.json, code tạo ra một file tạm tên là storage/state.tmp (with_suffix(".tmp"))
            temp_path = self.state_file_path.with_suffix(".tmp")

            # - json.dump(...): Chuyển dữ liệu từ khuôn Pydantic (state.model_dump()) thành chuỗi JSON và ghi vào file tạm này
            # - indent=4: Tự động xuống hàng và thụt lề 4 ô cho đẹp mắt dễ đọc
            # - ensure_ascii=False: Giữ nguyên font chữ chuẩn (tiếng Việt nếu có) không bị biến thành các mã \u2342 loằng ngoằng
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(state.model_dump(), f, indent=4, ensure_ascii=False)

            # - Đổi tên chớp nhoáng. Lệnh os.replace(file_tạm, file_chính) sẽ tiến hành hoán đổi tên file. Hệ điều hành thực hiện lệnh này ở mức phần cứng cực kỳ nhanh
            # Nếu có mất điện lúc đang ghi, nó chỉ làm hỏng file .tmp, file state.json cũ của bạn vẫn nguyên vẹn 100%. Nhờ vậy mà dữ liệu của Bot luôn luôn an toàn
            os.replace(temp_path, self.state_file_path)
        except Exception as e:
            logger.error(f"Failed to save state to {self.state_file_path}: {e}")
