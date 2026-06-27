import os
import sys

# Nếu chạy dưới dạng file đóng gói (PyInstaller), tự động chuyển thư mục làm việc (CWD) về thư mục chứa file chạy
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.webhook import router as webhook_router
from core.config import settings
from core.scheduler import start_scheduler, stop_scheduler

# Configure logging dynamically from settings
logging.basicConfig(
    # Đi vào (Module) thư viện logging để lấy ra cái cấu hình mức độ logging.INFO tương ứng. Nếu trong file .env bạn nhập bậy bạ một chữ không tồn tại, nó sẽ lấy mức độ mặc định là logging.INFO
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
# Tạo một người ghi nhật ký riêng cho file này với cái tên là "main". Bạn sẽ biết lỗi hay thông tin này xuất phát từ file này
logger = logging.getLogger("main")


# Quản lý vòng đời của Bot (Lifespan)
@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: Start APScheduler
    logger.info("Starting up Smart Reminder Bot...")
    try:
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to initialize scheduler on startup: {e}", exc_info=True)

    # Chữ yield giống như một cái dấu ngắt. Khi hệ thống chạy đến chữ này, nó sẽ dừng lại và giữ nguyên trạng thái đó.
    # Lúc này, Bot chính thức hoạt động, sẵn sàng chờ bạn gọi API hoặc chờ bộ hẹn giờ kích hoạt SyncService
    yield

    # Shutdown: Clean up scheduler resources
    logger.info("Shutting down Smart Reminder Bot...")
    try:
        stop_scheduler()
    except Exception as e:
        logger.error(f"Failed to shutdown scheduler cleanly: {e}", exc_info=True)


# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Smart Reminder Bot",
    description="Syncs Backlog notifications to Microsoft Teams in the background",
    version="1.0.0",
    # lifespan=lifespan: Nó thay thế cho @app.on_event("startup") và @app.on_event("shutdown").
    # Quản lý tài nguyên cực tốt: Nhờ có chữ yield, bạn có thể tạo ra một kết nối ở trên, cho app mượn dùng suốt cả ngày, rồi khi app tắt, đoạn code bên dưới yield sẽ tự động dọn dẹp kết nối đó một cách an toàn và sạch sẽ.
    lifespan=lifespan,
    # Nếu code của bạn bị lỗi sập nguồn ở đâu đó, FastAPI sẽ in hẳn một trang web chứa toàn bộ chi tiết lỗi (Traceback) ra màn hình trình duyệt cho bạn xem để sửa
    debug=True,
    # Khai báo các địa chỉ Server (môi trường) chạy con Bot này trên trang tài liệu /docs. Người xem có thể bấm menu thả xuống để chọn test trực tiếp trên máy Local, Server Test (Staging) hoặc Server Chạy thật (Production)
    # servers=[
    #     {"url": "http://localhost:8000", "description": "Máy cá nhân (Local)"},
    #     {"url": "https://api.botcuatoi.com", "description": "Server chạy thật (Production)"}
    # ],
    # contact: Thông tin tác giả
    contact={
        "name": "Nguyen Trung Kien",
        "url": "https://www.facebook.com/spring.reus/",
        "email": "nguyenkien11202000@gmail.com",
        "phone": "0981284476",
    },
    # license_info: Thông tin bản quyền
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    # terms_of_service: Điều khoản sử dụng. Link dẫn đến trang điều khoản quy định người khác được làm gì và không được làm gì với con Bot này, cũng sẽ hiển thị ở trang đầu /docs
    terms_of_service="https://www.facebook.com/spring.reus/",
    # responses: Phạm vi toàn cục. Định nghĩa lỗi chung cho mọi API
    responses={
        404: {"description": "Không tìm thấy đường link này trên Bot"},
        500: {"description": "Lỗi hệ thống bên trong server"},
    },
    # redirect_slashes: Tự động sửa dấu gạch chéo / ở cuối URL. Nếu bạn viết code API là /sync, nhưng người dùng gõ nhầm trên trình duyệt là /sync/ (có dấu / ở cuối), FastAPI sẽ tự động chuyển hướng (Redirect) họ về đúng link /sync mà không báo lỗi 404.
    # Nếu bạn tắt đi (False), gõ thừa dấu / sẽ bị lỗi ngay lập tức
    redirect_slashes=True,
    # Nhóm cấu hình và tuỳ biến giao diện tài liệu (Docs URL)
    # + docs_url: Thay đổi đường link dẫn đến trang tài liệu Swagger UI (mặc định là /docs)
    # docs_url="/chuc-nang-he-thong", # Đổi từ /docs sang /chuc-nang-he-thong
    # + redoc_url: Thay đổi đường link dẫn đến trang tài liệu ReDoc (mặc định là /redoc).
    # redoc_url=None, # Truyền None để tắt hẳn trang ReDoc nếu không xài tới
    # Nhóm cấu hình OpenAPI (Tùy biến tài liệu nâng cao)
    # + openapi_url: FastAPI hoạt động dựa trên một file JSON mô tả toàn bộ cấu trúc API (gọi là OpenAPI schema). Mặc định link này là /openapi.json. Bạn có thể ẩn nó đi để tránh hacker quét cấu trúc hệ thống
    # openapi_url=None,
    # + openapi_tags: Dùng để thêm mô tả chi tiết, hình ảnh hoặc tài liệu cho từng cái tags (danh mục) mà bạn chia ở các file API
    # openapi_tags=TAGS_METADATA,
    # + default_response_class: Mặc định FastAPI trả dữ liệu về dạng JSON chuẩn (JSONResponse). Tuy nhiên, nếu bạn muốn API của mình trả dữ liệu siêu nhanh (Serialize JSON nhanh hơn và CPU usage thấp hơn), bạn có thể đổi sang dùng ORJSONResponse hoặc UJSONResponse từ các thư viện chuyên tối ưu tốc độ.
    # default_response_class=JSONResponse,
    # Nhóm quản lý máy chủ proxy và đường dẫn gốc
    # Khi bạn deploy (triển khai) con Bot này lên môi trường mạng thực tế, đôi khi nó sẽ chạy phía sau một cổng trung gian (Reverse Proxy như Nginx, Traefik) hoặc nằm trong một cụm thư mục con của một hệ thống lớn
    # root_path: Cấu hình đường dẫn gốc cho ứng dụng. Ví dụ app của bạn được nhúng bên trong một trang web lớn tại đường dẫn https://congty.com/my-bot/. Nếu không cấu hình root_path="/my-bot", các đường link API bên trong sẽ bị lỗi đường dẫn hết.
    # root_path="/my-bot
)

# ++++++++++ 1 vài cách sử dụng include_router khác ++++++++++
# 1. Nhúng cụm công khai cho người dùng: ai vào cũng được, có tag riêng
# app.include_router(
#     user_router,
#     prefix="/api/v1/user",
#     tags=["User Features"]
# )

# 2. Nhúng cụm cho Admin: Bắt buộc phải check quyền, có phản hồi lỗi bảo mật riêng trên tài liệu, gom vào tag Admin
# Trong đó:
# - dependencies: Cài "bảo vệ" cho toàn bộ cụm API. Nếu bạn có một router chứa 10 API liên quan đến admin,
# và bạn muốn tất cả 10 API này đều phải kiểm tra mã token bảo mật trước khi chạy, bạn chỉ cần truyền vào đây một lần duy nhất

# - kiem_tra_token_admin là 1 cái function

# - default_response_class: Đổi định dạng trả về cho riêng cụm này. Nếu toàn bộ ứng dụng của bạn trả về dữ liệu dạng JSON thông thường, nhưng riêng các API trong cái webhook_router này bạn muốn trả về nội dung dạng văn bản thuần túy (Plain Text) hoặc dạng HTML,
# bạn có thể ép riêng cho nó

# - include_in_schema=False: Ẩn toàn bộ cụm API khỏi tài liệu. Nếu bạn đang phát triển một cụm API để thử nghiệm ngầm hoặc phục vụ riêng cho nội bộ hệ thống và tuyệt đối không muốn đối tác hoặc người ngoài nhìn thấy các đường link này trên trang tài liệu hướng dẫn /docs,
# hãy bật option này lên

# app.include_router(
#     admin_router,
#     prefix="/api/v1/admin",
#     tags=["Admin Only"],
#     default_response_class=PlainTextResponse # Riêng các API cụm này sẽ mặc định trả về chữ thô, không phải JSON
#     dependencies=[Depends(kiem_tra_token_admin)],
#     responses={403: {"description": "Lỗi cấm truy cập nếu không phải Admin"}}
# )


# Tích hợp (nhúng) các đường link API từ file khác vào file main.py này
app.include_router(
    webhook_router,
    prefix="/api/v1",
)


# Health Check Endpoint
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "message": "Bot is running"}


# Đóng gói ứng dụng thành extension
if __name__ == "__main__":
    import uvicorn

    # Khởi chạy FastAPI app trên cổng 8000
    uvicorn.run(app, host="127.0.0.1", port=8000)
