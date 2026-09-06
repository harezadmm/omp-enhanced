@echo off
setlocal enabledelayedexpansion

echo ====================================
echo OMP Skills Installer for Windows
echo ====================================
echo.

set "HERMES_DIR=%USERPROFILE%\.hermes\profiles\umi2\skills"

if not exist "%HERMES_DIR%" (
    echo Creating Hermes skills directory...
    mkdir "%HERMES_DIR%" 2>nul
)

echo Installing to: %HERMES_DIR%
echo.

echo Extracting omp-skills-windows.tar.gz...
tar -xzf omp-skills-windows.tar.gz -C "%HERMES_DIR%"

if %errorlevel% equ 0 (
    echo.
    echo ✓ Installation complete!
    echo Skills installed to: %HERMES_DIR%
    echo.
    echo Run: hermes skills list
) else (
    echo.
    echo × Error: tar extraction failed
    echo Make sure omp-skills-windows.tar.gz is in the same folder as this .bat file
    echo.
)

pause
