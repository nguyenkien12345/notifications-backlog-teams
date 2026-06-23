from .helpers import build_backlog_url, truncate_text

# __all__: là một biến đặc biệt dạng danh sách (list). Nó đóng vai trò là một "Tấm khiên bảo mật" hoặc "Sách hướng dẫn công khai" cho thư mục (package) utils
# __all__ định nghĩa các hàm được phép xuất (export) công khai ra bên ngoài bởi package. Khi ai đó dùng: from utils import *. Python sẽ chỉ import các tên được liệt kê trong __all__, tránh bị lộ các thư viện nội bộ
# Ngoài ra __all__ còn đóng vai trò tài liệu hóa public API của package, giúp người dùng biết những hàm nào được package hỗ trợ chính thức

__all__ = ["build_backlog_url", "truncate_text"]
