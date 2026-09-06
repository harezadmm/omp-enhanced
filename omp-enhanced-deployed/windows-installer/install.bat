@echo off
setlocal enabledelayedexpansion

echo ===============================================
echo OMP-Enhanced Windows Installer
echo ===============================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARNING] Not running as Administrator
    echo Some features may require admin privileges
    echo.
)

:: Set installation directories
set "INSTALL_DIR=%USERPROFILE%\.omp-enhanced"
set "JAVA_DIR=%INSTALL_DIR%\jdk-21"
set "ANDROID_SDK=%INSTALL_DIR%\android-sdk"
set "GRADLE_DIR=%INSTALL_DIR%\gradle-9.7.1"

echo [1/6] Checking Java JDK 21...
java -version 2>&1 | findstr /i "21" >nul
if %errorLevel% equ 0 (
    echo [OK] Java JDK 21 already installed
    goto :android_sdk
)

echo [INSTALL] Downloading Java JDK 21...
mkdir "%JAVA_DIR%" 2>nul

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://download.oracle.com/java/21/latest/jdk-21_windows-x64_bin.zip' -OutFile '%TEMP%\jdk21.zip'}"

if exist "%TEMP%\jdk21.zip" (
    echo [INSTALL] Extracting Java JDK 21...
    powershell -Command "Expand-Archive -Path '%TEMP%\jdk21.zip' -DestinationPath '%INSTALL_DIR%' -Force"
    del "%TEMP%\jdk21.zip"
    
    :: Find actual JDK folder
    for /d %%i in ("%INSTALL_DIR%\jdk-21*") do set "JAVA_DIR=%%i"
    
    echo [OK] Java JDK 21 installed to: !JAVA_DIR!
) else (
    echo [ERROR] Failed to download Java JDK 21
    echo Please download manually from: https://www.oracle.com/java/technologies/downloads/#java21
    pause
    exit /b 1
)

:android_sdk
echo.
echo [2/6] Checking Android SDK...
if exist "%ANDROID_SDK%\cmdline-tools" (
    echo [OK] Android SDK already installed
    goto :gradle
)

echo [INSTALL] Downloading Android SDK command-line tools...
mkdir "%ANDROID_SDK%\cmdline-tools" 2>nul

powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip' -OutFile '%TEMP%\cmdline-tools.zip'}"

if exist "%TEMP%\cmdline-tools.zip" (
    echo [INSTALL] Extracting Android SDK tools...
    powershell -Command "Expand-Archive -Path '%TEMP%\cmdline-tools.zip' -DestinationPath '%TEMP%\cmdline-tools-temp' -Force"
    
    mkdir "%ANDROID_SDK%\cmdline-tools\latest" 2>nul
    xcopy /E /I /Y "%TEMP%\cmdline-tools-temp\cmdline-tools\*" "%ANDROID_SDK%\cmdline-tools\latest\"
    
    del "%TEMP%\cmdline-tools.zip"
    rmdir /S /Q "%TEMP%\cmdline-tools-temp"
    
    echo [OK] Android SDK installed to: %ANDROID_SDK%
) else (
    echo [ERROR] Failed to download Android SDK
    pause
    exit /b 1
)

:gradle
echo.
echo [3/6] Checking Gradle...
if exist "%GRADLE_DIR%" (
    echo [OK] Gradle already installed
    goto :env_vars
)

echo [INSTALL] Downloading Gradle 9.7.1...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://services.gradle.org/distributions/gradle-9.7.1-bin.zip' -OutFile '%TEMP%\gradle.zip'}"

if exist "%TEMP%\gradle.zip" (
    echo [INSTALL] Extracting Gradle...
    powershell -Command "Expand-Archive -Path '%TEMP%\gradle.zip' -DestinationPath '%INSTALL_DIR%' -Force"
    del "%TEMP%\gradle.zip"
    echo [OK] Gradle installed to: %GRADLE_DIR%
) else (
    echo [ERROR] Failed to download Gradle
    pause
    exit /b 1
)

:env_vars
echo.
echo [4/6] Setting up environment variables...

:: Set JAVA_HOME
setx JAVA_HOME "%JAVA_DIR%" >nul 2>&1
echo [OK] JAVA_HOME = %JAVA_DIR%

:: Set ANDROID_HOME
setx ANDROID_HOME "%ANDROID_SDK%" >nul 2>&1
echo [OK] ANDROID_HOME = %ANDROID_SDK%

:: Update PATH
set "NEW_PATH=%JAVA_DIR%\bin;%ANDROID_SDK%\cmdline-tools\latest\bin;%ANDROID_SDK%\platform-tools;%GRADLE_DIR%\bin"

for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do set "CURRENT_PATH=%%b"

echo !CURRENT_PATH! | findstr /C:"%JAVA_DIR%" >nul
if %errorLevel% neq 0 (
    setx PATH "!CURRENT_PATH!;%NEW_PATH%" >nul 2>&1
    echo [OK] PATH updated with new tools
) else (
    echo [OK] PATH already configured
)

:hermes
echo.
echo [5/6] Checking Hermes Agent...
where hermes >nul 2>&1
if %errorLevel% equ 0 (
    echo [OK] Hermes Agent already installed
    goto :verify
)

echo [INFO] Hermes Agent not found
echo Please install Hermes Agent manually from:
echo https://hermes-agent.nousresearch.com/docs/installation
echo.

:verify
echo.
echo [6/6] Verification...
echo.
echo ===============================================
echo Installation Summary
echo ===============================================
echo.

if exist "%JAVA_DIR%" (
    echo [OK] Java JDK 21: %JAVA_DIR%
) else (
    echo [FAIL] Java JDK 21: Not found
)

if exist "%ANDROID_SDK%" (
    echo [OK] Android SDK: %ANDROID_SDK%
) else (
    echo [FAIL] Android SDK: Not found
)

if exist "%GRADLE_DIR%" (
    echo [OK] Gradle 9.7.1: %GRADLE_DIR%
) else (
    echo [FAIL] Gradle: Not found
)

echo.
echo ===============================================
echo IMPORTANT: Restart your terminal/CMD
echo ===============================================
echo Environment variables will be active after restart.
echo.
echo Then verify installation:
echo   java -version
echo   gradle -v
echo   hermes --version
echo.
echo ===============================================

pause
