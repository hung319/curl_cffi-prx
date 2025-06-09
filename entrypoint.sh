#!/bin/sh

# Dòng này đảm bảo script sẽ thoát ngay nếu có lỗi
set -e

# Thiết lập biến PORT: Lấy giá trị từ biến môi trường ${PORT}, 
# nếu không có thì dùng giá trị mặc định là 8000.
PORT=${PORT:-8000}

echo "Starting Uvicorn server on port $PORT..."

# Dùng 'exec' để khởi động Uvicorn.
# Điều này đảm bảo Uvicorn là tiến trình chính và có thể nhận các tín hiệu hệ thống
# một cách đúng đắn, giúp giải quyết cảnh báo của Docker.
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
