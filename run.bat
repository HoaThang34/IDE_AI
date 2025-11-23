@echo off
title Auto Run Python Server
echo ==========================================
echo     KIEM TRA VA CAI DAT THU VIEN...
echo ==========================================

:: Cài đặt thư viện từ file requirements.txt
pip install -r requirements.txt

echo.
echo ==========================================
echo        DANG KHOI DONG SERVER...
echo ==========================================
echo.

:: Chạy file main.py
python main.py

:: Giữ màn hình không bị tắt ngay nếu có lỗi
pause