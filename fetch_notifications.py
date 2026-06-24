import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta

# Tự động tìm và lấy ra đường dẫn tuyệt đối dẫn đến thư mục chứa file script hiện tại, bất kể bạn đang đứng ở đâu để bấm nút chạy file
workspace_dir = os.path.dirname(os.path.abspath(__file__))
# Khi chúng ta thực thi một script độc lập nằm sâu trong thư mục con, Python đôi khi không hiểu các thư mục như core hay services nằm ở đâu để import. Dòng này lấy đường dẫn tuyệt đối của thư mục chứa file hiện tại và ép Python phải nhìn vào đó, giúp lệnh from core.config import settings chạy mượt mà mà không bị lỗi ModuleNotFoundError
sys.path.append(workspace_dir)

import httpx

from core.config import settings


async def fetch_recent_notifications(days=7):
    # Determine base URL
    space_id = settings.BACKLOG_SPACE_ID
    domain = settings.BACKLOG_DOMAIN
    if "." in space_id:
        base_url = f"https://{space_id}/api/v2"
    else:
        base_url = f"https://{space_id}.{domain}/api/v2"

    api_key = settings.BACKLOG_API_KEY.get_secret_value()
    url = f"{base_url}/notifications"

    params = {"apiKey": api_key, "count": 20}

    # Calculate threshold (7 days ago in UTC)
    time_threshold = datetime.now(UTC) - timedelta(days=days)
    print(f"Fetching notifications from: {url}")
    print(f"Filtering notifications since: {time_threshold.isoformat()}")

    all_recent_notifications = []

    # Tăng thời gian chờ lên hẳn 60 giây để đảm bảo dù mạng lag hay dữ liệu quá khứ nặng, script vẫn kiên trì đợi bằng được
    async with httpx.AsyncClient(timeout=60.0) as client:
        max_id = None
        while True:
            if max_id:
                # - Lần chạy đầu tiên, max_id bằng None, Bot lấy 20 tin mới nhất (ví dụ từ ID 200 về ID 181)
                # - Lần chạy thứ hai, Bot nạp tham số maxId = 181. Máy chủ Backlog đọc được sẽ hiểu là: "À, hãy đưa cho tôi 20 tin tiếp theo cũ hơn cái ID 181 này" (lấy từ ID 180 về ID 161)
                params["maxId"] = max_id

            response = await client.get(url, params=params)

            # Ý nghĩa của dòng: response.raise_for_status() 
            # - Trong trường hợp status code từ 200 đến 299, chương trình sẽ tiếp tục chạy bình thường
            # - Trong trường hợp status code từ 400 trở lên, chương trình sẽ dừng ngay lập tức và báo lỗi
            response.raise_for_status()
            
            notifications = response.json()

            if not notifications:
                break

            reached_end = False
            for n in notifications:
                created_str = n.get("created")
                if not created_str:
                    continue

                if created_str.endswith("Z"):
                    # Chuẩn hóa chuỗi thời gian từ Backlog (Thay chữ 'Z' thành múi giờ +00:00)
                    created_str = created_str[:-1] + "+00:00"

                try:
                    created_dt = datetime.fromisoformat(created_str)
                except ValueError:
                    created_dt = datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=UTC
                    )

                if created_dt >= time_threshold:
                    # Nếu tin này mới hơn mốc 7 ngày trước, giữ lại
                    all_recent_notifications.append(n)
                else:
                    # Nếu phát hiện 1 tin cũ hơn mốc 7 ngày trước -> Đã chạm đến vạch đích quá khứ
                    reached_end = True

            # + Thoát/Dừng vòng lặp ngay khi:
            # - reached_end = True (Đã gặp phải element cũ hơn) (Đã chạm tới vạch đích quá khứ)
            # - Số lượng tin Backlog trả về ít hơn 20 (chứng tỏ trên hệ thống đã cạn sạch thông báo, không còn gì để quét nữa)
            if reached_end or len(notifications) < params["count"]:
                break

            # Trước khi lặp lại vòng mới, Bot tìm ra cái ID nhỏ nhất (tin cũ nhất) trong nhóm 20 tin vừa quét để làm bàn đạp nạp vào maxId cho lượt quét tiếp theo
            max_id = min(n["id"] for n in notifications)

    return all_recent_notifications


async def main():
    try:
        notifications = await fetch_recent_notifications()
        print(f"\nFound {len(notifications)} notifications in the last 7 days:")
        print("=" * 80)
        # enumerate(notifications, 1): Vòng lặp tự động đếm số thứ tự tăng dần từ 1, 2, 3... giúp bạn biết chính xác có tổng cộng bao nhiêu thông báo
        for i, n in enumerate(notifications, 1):
            created = n.get("created")
            sender = n.get("sender", {}).get("name", "Unknown Sender")
            reason = n.get("reason")

            # Extract content context
            title = ""
            if n.get("issue"):
                title = f"Issue: {n['issue']['issueKey']} - {n['issue']['summary']}"
            elif n.get("pullRequest"):
                title = f"PR #{n['pullRequest']['number']} - {n['pullRequest']['title']}"
            elif n.get("comment"):
                title = f"Comment ID: {n['comment']['id']}"
            else:
                title = "General notification"

            read_status = "Read" if n.get("alreadyRead") else "UNREAD"

            print(f"{i:2d}. [{created}] [{read_status}] Sender: {sender}")
            print(f"    Topic: {title}")
            print(f"    Reason code: {reason}")
            print("-" * 80)

    except httpx.ReadTimeout:
        print(
            "\n[Lỗi] Kết nối đến Backlog bị quá hạn (Read Timeout). Vui lòng kiểm tra lại mạng hoặc chạy lại script sau ít phút.",
            file=sys.stderr,
        )
    except httpx.HTTPStatusError as e:
        print(
            f"\n[Lỗi HTTP] Máy chủ Backlog trả về mã lỗi: {e.response.status_code}\nChi tiết: {e.response.text}",
            file=sys.stderr,
        )
    except httpx.RequestError as e:
        print(f"\n[Lỗi Kết Nối] Không thể kết nối tới Backlog: {e}", file=sys.stderr)
    except Exception:
        import traceback

        print("\n[Lỗi Chưa Xác Định] Có lỗi xảy ra khi thực thi:", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# __name__ là một biến đặc biệt (special variable) mà Python tự gán khi module được load. Giá trị của biến __name__ này sẽ thay đổi phụ thuộc vào cách bạn gọi file đó:
# - Trường hợp 1: Bạn chủ động mở Terminal và gõ chạy trực tiếp file này: python script_kiem_tra.py
# => Python hiểu đây là file gốc (file chính) được kích hoạt. Nó sẽ tự động gán giá trị cho biến __name__ thành chuỗi chữ "__main__".
# Lúc này điều kiện if "__main__" == "__main__" hợp lệ (Đúng) => Các dòng code thụt lề bên trong lệnh if sẽ được phép chạy.

# - Trường hợp 2: File này được một file khác gọi (Import) vào làm thư viện
# Giả sử ở file main.py, bạn gõ lệnh: from services import fetch_recent_notifications.
# Lúc này, Python hiểu file này chỉ là một người phụ tá (Module phụ) được gọi đến thôi. Nó sẽ gán giá trị cho biến __name__ thành chính tên của file đó (ví dụ: "script_kiem_tra").
# Lúc này điều kiện if "script_kiem_tra" == "__main__" bị sai (Fails) => Toàn bộ đoạn code bên trong lệnh if sẽ bị khóa lại và bỏ qua.
if __name__ == "__main__":
    # - Nếu bạn gõ main() khơi khơi, Python sẽ chỉ trả về một đối tượng trạng thái chờ chứ hoàn toàn không chạy một dòng code nào bên trong hàm đó cả.
    # - Để chạy được một hàm async, bạn cần một Event Loop đứng ra quản lý thời gian và luồng chạy ngầm cho nó.
    asyncio.run(main())
