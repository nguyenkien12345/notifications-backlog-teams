# File Makefile dùng để làm gì ?
# - Về bản chất Makefile là: Một công cụ build automation
# - Để chạy một lệnh kiểm tra lỗi code bằng ruff, bạn phải gõ cả một đoạn dài ngoằn trên Terminal: venv/bin/ruff check . --fix. 
# Hoặc để cài đặt thư viện, bạn phải gõ: venv/bin/pip install -r requirements.txt -r requirements-dev.txt. Gõ đi gõ lại đống này vừa mệt, vừa dễ sai chính tả
# - Makefile sinh ra để giải quyết vấn đề này. Nó gom tất cả các câu lệnh dài dòng, phức tạp vào trong các "từ khóa" (gọi là Target). 
# Chỉ cần gõ đúng 4-5 chữ cái là hệ thống tự chạy một sớ lệnh phức tạp phía sau

# .PHONY: Phần định nghĩa phím tắt chung. Đây là một từ khóa đặc biệt của Makefile. 
# Nó dùng để thông báo rằng: "Những chữ nằm phía sau (help, install, lint, format, check) chỉ là tên của các phím tắt lệnh, chứ không phải là tên của một file hay thư mục nào trong máy tính đâu nhé
.PHONY: help install lint format check run build

# Variables
PYTHON = venv/bin/python
PIP = venv/bin/pip
RUFF = venv/bin/ruff
PYINSTALLER = venv/bin/pyinstaller

# make help (Hướng dẫn sử dụng)
# Khi bạn gõ lệnh: make help (hoặc chỉ gõ chuỗi chữ make), hệ thống sẽ in (@echo) 
# ra màn hình một cái bảng menu hướng dẫn cực kỳ đẹp mắt để ai đọc vào cũng biết dự án này có những phím tắt nào. Dấu @ ở đầu để ra lệnh cho máy tính: "chỉ in kết quả ra thôi, đừng in lại cái lệnh tao vừa gõ".
help:
	@echo "Available commands:"
	@echo "  make install      - Install both production and development dependencies"
	@echo "  make lint         - Check logic, syntax, and style issues using Ruff (auto-fixable rules are fixed)"
	@echo "  make format       - Auto-format code layout using Ruff formatter"
	@echo "  make check        - Verify code formatting and lint rules (CI mode)"
	@echo "  make run          - Start the FastAPI development server with hot-reload"
	@echo "  make build        - Package the application into a single executable using PyInstaller"

# make install (Cài đặt toàn bộ các thư viện)
# Makefile sẽ tự động kích hoạt lệnh cài đặt song song cả 2 file requirements.txt và requirements-dev.txt
install:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

# make lint (Bắt lỗi và sửa lỗi tự động)
# Thư viện ruff sẽ quét toàn bộ dự án (.). Tham số --fix có nghĩa là: "Nếu thấy lỗi nào nhỏ nhặt (như thừa import, thừa biến), hãy tự động sửa luôn cho tao, đừng bắt tao sửa tay!"
lint:
	$(RUFF) check . --fix

# make format (Làm đẹp code)
# Thư viện ruff sẽ tự động đi qua từng file code trong dự án, căn lề, thụt dòng, sửa dấu nháy... biến toàn bộ dự án thành một chuẩn
format:
	$(RUFF) format .

# make check (Kiểm tra nghiêm ngặt - Chế độ CI)
# Lệnh này chạy 2 bước: kiểm tra lỗi logic (check .) và kiểm tra xem code đã được làm đẹp chuẩn chỉnh chưa (format --check .). Lệnh này không tự động sửa code, nó chỉ "soi" xem lập trình viên làm bài có kỹ không. 
# Nếu phát hiện code bị lệch dòng hay sai chuẩn, nó sẽ báo đỏ để chặn không cho đẩy code lên Server (thường dùng trong hệ thống tự động kiểm tra CI/CD)
check:
	$(RUFF) check .
	$(RUFF) format --check .

# make run (Chạy nhanh FastAPI development server)
# Chỉ cần gõ `make run`. Nó sẽ tự chạy uvicorn từ venv mà không cần bạn activate thủ công.
run:
	venv/bin/uvicorn main:app --reload

# make build (Đóng gói ứng dụng thành file thực thi duy nhất bằng PyInstaller)
# 1 số option hữu ích:
# --onefile: Đóng gói toàn bộ code và thư viện vào một file duy nhất (nằm trong thư mục dist/ sau khi build xong)
# --collect-all uvicorn và --collect-all fastapi: Thu thập toàn bộ package resources đi kèm của Uvicorn và FastAPI để đảm bảo server web chạy bình thường
# --icon app.ico: Sử dụng icon chỉ định cho ứng dụng (file app.ico nằm cùng thư mục với main.py) (Nếu không gọi option này thì nó sẽ hiển thị icon mặc định của hệ điều hành)
# --name MyApplication: Đặt tên cho file thực thi (Nếu không gọi option này thì file thực thi sẽ có tên là main.exe)
# --clean: Xóa cache build cũ
# --noconsole hoặc --windowed: Ẩn cửa sổ đen của terminal. Option này chỉ nên dùng nếu đây là: GUI, Desktop app, Tray app
# --add-data source;destination: Thêm file hoặc thư mục vào file thực thi (source là đường dẫn file/thư mục, destination là đường dẫn đích trong file thực thi). Dấu . là thư mục hiện tại. VD: --add-data "config.json;."
# --hidden-import: Ép PyInstaller tìm kiếm thêm module (VD: --hidden-import "custom_module")
# --upx-dir path/to/upx: Sử dụng UPX đã cài sẵn để giảm kích thước exe
# --strip: Xóa bỏ các symbol không cần thiết khỏi file thực thi để giảm kích thước
# --debug all: Bật debug mode

# Cách câu lệnh này hoạt động: 
# PyInstaller sẽ:
# 1) Đọc file script chính (main.py). Nó sẽ tạo ra một file cấu hình tạm thời gọi là SyncNotification.spec (nếu chưa có). File này chứa toàn bộ các tham số build mà ta đã truyền từ câu lệnh
# 2) Quét cây thư mục Dependency (Graph Generation). Nó đi xuyên qua code, tìm tất cả các lệnh import và from ... import .... Nó sẽ gom toàn bộ các file .py của dự án và các thư viện trong venv (bao gồm toàn bộ file của fastapi và uvicorn do có lệnh --collect-all) để tạo thành một sơ đồ phụ thuộc
# 3) Tạo thư mục build/ và biên dịch sang C-level. Nó tạo thư mục build/. Tại đây, nó sẽ gom tất cả các file Python đã quét được, biên dịch chúng thành file bytecode .pyc. Đồng thời, nó thu thập các file thư viện động liên kết hệ thống (như các file .dll trên Windows hoặc .so trên Linux)
# 4) Đóng gói và nén (Assembly & Compression). PyInstaller sẽ lấy toàn bộ các file bytecode .pyc, các file .dll, và các asset phụ trợ, nén tất cả lại thành một khối dữ liệu nhị phân duy nhất bằng zlib
# 5) Tạo file Executable hoàn chỉnh trong dist/. Nó tạo một file chạy "mồi" (bootloader) có tên là SyncNotification.exe nằm trong thư mục dist/. Khối dữ liệu nén ở Bước 4 sẽ được nhúng trực tiếp vào đuôi của file exe mồi này

build:
	$(PYINSTALLER) --onefile --collect-all uvicorn --collect-all fastapi --clean --strip --icon nttts.ico --name SyncNotification main.py
