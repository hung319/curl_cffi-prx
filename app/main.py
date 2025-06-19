# app/main.py

import os
import json
from datetime import datetime, timezone
# --- THAY ĐỔI: Import thêm BaseModel từ pydantic và Dict từ typing ---
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict
# -----------------------------------------
from fastapi.responses import PlainTextResponse
from curl_cffi.requests import AsyncSession, RequestsError


# Các phần code phía trên không thay đổi
# ...
start_time = datetime.now(timezone.utc)
SECRET_KEY = os.getenv("API_KEY")
IP_SOCKS = os.getenv("IPSOCKS")
USER_SOCKS = os.getenv("USERSOCKS")
PASS_SOCKS = os.getenv("PASSSOCKS")
final_proxy_url = None
if IP_SOCKS:
    proxy_scheme = "socks5h" 
    auth_part = ""
    if USER_SOCKS and PASS_SOCKS:
        auth_part = f"{USER_SOCKS}:{PASS_SOCKS}@"
    final_proxy_url = f"{proxy_scheme}://{auth_part}{IP_SOCKS}"
    print(f"Proxy đã được cấu hình để sử dụng: {proxy_scheme}://...@{IP_SOCKS}")
else:
    print("Không có cấu hình proxy nào được tìm thấy. API sẽ chạy ở chế độ trực tiếp.")
if not SECRET_KEY:
    raise ValueError("Biến môi trường API_KEY chưa được thiết lập.")

app = FastAPI(
    title="Fetcher API with Docs",
    description="API để fetch URL, hỗ trợ health check và có tài liệu tự động.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)
session = AsyncSession(impersonate="chrome120", timeout=45)

# --- THÊM MỚI: Định nghĩa model cho dữ liệu đầu vào của POST request ---
class PostRequest(BaseModel):
    url: str
    key: str
    data: Optional[str] = None  # Dữ liệu dạng chuỗi để gửi đi trong body
    custom_headers: Optional[Dict[str, str]] = None
    referer: Optional[str] = None
# -----------------------------------------


# Endpoint / và /api (GET) không thay đổi
@app.get("/", tags=["Health Check"])
async def get_root_health_check():
    uptime = datetime.now(timezone.utc) - start_time
    proxy_status = { "configured": bool(final_proxy_url), "details": f"Using proxy configured at {IP_SOCKS}" if final_proxy_url else "API is running in direct mode." }
    return { "status": "active", "server_time_utc": datetime.now(timezone.utc).isoformat(), "uptime_seconds": uptime.total_seconds(), "proxy": proxy_status }

@app.get("/api", tags=["GET Method"])
async def fetch_url_get_api(
    key: str = Query(..., description="API Key để xác thực."),
    url: str = Query(..., description="URL của trang web bạn muốn lấy nội dung."),
    referer: Optional[str] = Query(None, description="URL referer để gửi trong request header."),
    custom_headers: Optional[str] = Query(None, description="Một chuỗi JSON chứa các header tùy chỉnh.")
):
    if key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="API Key không hợp lệ hoặc bị thiếu.")
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL không hợp lệ.")
    headers = {}
    if custom_headers:
        try:
            parsed_headers = json.loads(custom_headers)
            if isinstance(parsed_headers, dict): headers.update(parsed_headers)
            else: raise HTTPException(status_code=400, detail="custom_headers phải là một đối tượng JSON.")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Giá trị của custom_headers không phải là một chuỗi JSON hợp lệ.")
    if referer: headers["Referer"] = referer
    request_kwargs = {"headers": headers}
    if final_proxy_url: request_kwargs["proxies"] = {"http": final_proxy_url, "https": final_proxy_url}
    try:
        response = await session.get(url, **request_kwargs)
        response.raise_for_status()
        return response.text
    except RequestsError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi khi yêu cầu đến URL mục tiêu: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {exc}")

# --- THÊM MỚI: Endpoint cho phương thức POST tại /api ---
@app.post("/api", tags=["POST Method"])
async def fetch_url_post_api(request: PostRequest):
    """
    Nhận yêu cầu POST, gửi dữ liệu đến URL mục tiêu và trả về kết quả.
    """
    if request.key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="API Key không hợp lệ hoặc bị thiếu.")
        
    headers = request.custom_headers or {}
    if request.referer:
        headers["Referer"] = request.referer
        
    request_kwargs = {
        "headers": headers,
        "data": request.data
    }
    
    if final_proxy_url:
        request_kwargs["proxies"] = {"http": final_proxy_url, "https": final_proxy_url}
        
    try:
        response = await session.post(request.url, **request_kwargs)
        response.raise_for_status()
        return response.text
    except RequestsError as exc:
        raise HTTPException(status_code=502, detail=f"Lỗi khi yêu cầu đến URL mục tiêu: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi máy chủ không xác định: {exc}")

@app.on_event("shutdown")
async def shutdown_event():
    await session.close()
