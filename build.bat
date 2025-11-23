@echo off

echo.
echo Building CodeForge executable...
pyinstaller --clean build.spec

echo.
echo Build complete! Executable is in the 'dist' folder.
pause
