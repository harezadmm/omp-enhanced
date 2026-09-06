@echo off
echo ========================================
echo OMP-Enhanced Quick Installer
echo ========================================
echo.

:: Cek winget ada atau ngga
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Winget not found. Install from Microsoft Store.
    pause
    exit /b 1
)

echo [1/3] Installing Java JDK 21...
winget install --id Oracle.JDK.21 --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% neq 0 echo [WARNING] Java install failed or already installed

echo.
echo [2/3] Installing Gradle...
winget install --id Gradle.Gradle --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% neq 0 echo [WARNING] Gradle install failed or already installed

echo.
echo [3/3] Installing Android SDK...
winget install --id Google.AndroidStudio --silent --accept-package-agreements --accept-source-agreements
if %errorLevel% neq 0 echo [WARNING] Android Studio install failed or already installed

echo.
echo ========================================
echo DONE! Restart terminal then run:
echo   java -version
echo   gradle -v
echo ========================================
pause
