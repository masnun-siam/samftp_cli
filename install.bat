@echo off
rem This script installs the samftp-cli application and its dependencies.

setlocal

echo Checking for Rye...
where rye >nul 2>nul
if %errorlevel% neq 0 (
    echo Rye is not installed. Please install it from https://rye-up.com/ and try again.
    exit /b 1
)

echo Syncing project dependencies...
rye sync

echo Installing the samftp command...
rye install --force samftp-cli --path .

echo.
echo ">> Installation successful!"
echo "You can now run the 'samftp' command from anywhere in your terminal."
echo "Please ensure '%%USERPROFILE%%\.rye\shims' is in your system's PATH."

endlocal 