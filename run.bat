@echo off
title SMARTAssist Hub
cd /d "%~dp0"

echo.
echo  ================================================
echo   SMARTAssist Hub - Memulakan Sistem...
echo  ================================================
echo.

:: Cari Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [RALAT] Python tidak ditemui dalam PATH.
    echo  Sila pasang Python 3.11+ dari https://python.org
    echo  dan pastikan "Add Python to PATH" dipilih semasa pemasangan.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER% ditemui

:: Pasang dependencies jika belum ada
echo  [..] Memeriksa dependencies...
python -c "import uvicorn, fastapi, openai, langgraph" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [..] Memasang dependencies, sila tunggu...
    python -m pip install -r requirements.txt --quiet
    if %errorlevel% neq 0 (
        echo  [RALAT] Gagal memasang dependencies.
        echo  Cuba jalankan manual: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo  [OK] Dependencies berjaya dipasang
) else (
    echo  [OK] Dependencies sedia
)

:: Semak fail .env
if not exist ".env" (
    echo.
    echo  [AMARAN] Fail .env tidak ditemui.
    echo  Sila salin .env.example kepada .env dan isi DEEPSEEK_API_KEY.
    echo.
    pause
    exit /b 1
)
echo  [OK] Fail .env ditemui

:: Semak sama ada server sudah berjalan di port 8112
netstat -ano | findstr ":8112 " >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo  [OK] Server sudah berjalan di port 8112!
    echo  ================================================
    echo   Buka pelayar anda dan pergi ke:
    echo   http://localhost:8112
    echo  ================================================
    echo.
    start http://localhost:8112
    pause
    exit /b 0
)

echo.
echo  [OK] Sistem bersedia!
echo  ================================================
echo   Buka pelayar anda dan pergi ke:
echo   http://localhost:8112
echo  ================================================
echo.
echo  PETUA: Biarkan tetingkap ini terbuka — jangan tutup.
echo  Kali seterusnya jalankan run.bat, sistem akan terus
echo  buka tanpa perlu tunggu semula.
echo.
echo  Tekan Ctrl+C untuk hentikan sistem.
echo.

start http://localhost:8112
python -m uvicorn app:app --host 0.0.0.0 --port 8112

echo.
echo  Sistem telah dihentikan.
pause
