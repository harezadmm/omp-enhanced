@echo off
setlocal enabledelayedexpansion

echo ================================================
echo OMP Enhanced Windows Installer v2.0.1
echo ================================================
echo.

:: Check PowerShell
where powershell >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PowerShell not found. Please install PowerShell.
    pause
    exit /b 1
)

:: Check Java
echo [1/5] Checking Java...
where java >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Java not found. Downloading OpenJDK 17...
    powershell -ExecutionPolicy Bypass -File "%~dp0download-java.ps1"
    if !errorlevel! neq 0 (
        echo [ERROR] Java installation failed.
        pause
        exit /b 1
    )
) else (
    java -version 2>&1 | findstr "version" >nul
    echo [OK] Java installed
)

:: Download OMP server files
echo.
echo [2/5] Downloading OMP server...
powershell -ExecutionPolicy Bypass -Command "& { Invoke-WebRequest -Uri 'https://github.com/openmultiplayer/open.mp/releases/download/v1.3.1.2748/open.mp-win-x86.zip' -OutFile 'omp-server.zip' -UseBasicParsing }"
if %errorlevel% neq 0 (
    echo [ERROR] Download failed.
    pause
    exit /b 1
)
echo [OK] Download complete

:: Extract
echo.
echo [3/5] Extracting files...
powershell -ExecutionPolicy Bypass -Command "Expand-Archive -Path 'omp-server.zip' -DestinationPath '.' -Force"
if %errorlevel% neq 0 (
    echo [ERROR] Extraction failed.
    pause
    exit /b 1
)
del omp-server.zip
echo [OK] Extraction complete

:: Create config
echo.
echo [4/5] Creating config...
if not exist "config.json" (
    echo { > config.json
    echo   "announce": true, >> config.json
    echo   "bind": "0.0.0.0", >> config.json
    echo   "port": 7777, >> config.json
    echo   "max_players": 50, >> config.json
    echo   "hostname": "OMP Enhanced Server", >> config.json
    echo   "gamemode": "rivershell", >> config.json
    echo   "language": "English", >> config.json
    echo   "password": "", >> config.json
    echo   "rcon_password": "changeme123", >> config.json
    echo   "logging": { >> config.json
    echo     "log_queries": false, >> config.json
    echo     "log_chat": true >> config.json
    echo   } >> config.json
    echo } >> config.json
    echo [OK] Config created
) else (
    echo [OK] Config exists
)

:: Create start script
echo.
echo [5/5] Creating start script...
echo @echo off > start.bat
echo echo Starting OMP server... >> start.bat
echo omp-server.exe >> start.bat
echo pause >> start.bat
echo [OK] Start script created

echo.
echo ================================================
echo Installation Complete!
echo ================================================
echo.
echo To start server: start.bat
echo RCON password: changeme123
echo.
pause
