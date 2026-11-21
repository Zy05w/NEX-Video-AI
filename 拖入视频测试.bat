@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" (
  echo 请把视频文件拖到本文件图标上运行。
  pause
  exit /b 1
)
echo 请选择处理方式：
echo   1 = 动漫：超分 2x + 补帧 2x
echo   2 = 真人：超分 2x + 补帧 2x
echo   3 = 只超分 2x（动漫模型）
echo   4 = 只补帧 2x
choice /c 1234 /n /m "输入 1-4："
if errorlevel 4 (
  ".venv\Scripts\python.exe" -m nex.cli "%~1" --fi rife-v4.6 --fi-mult 2
) else if errorlevel 3 (
  ".venv\Scripts\python.exe" -m nex.cli "%~1" --sr realesr-animevideov3 --sr-scale 2
) else if errorlevel 2 (
  ".venv\Scripts\python.exe" -m nex.cli "%~1" --sr realesrgan-x4plus --sr-scale 2 --fi rife-v4.6 --fi-mult 2
) else (
  ".venv\Scripts\python.exe" -m nex.cli "%~1" --sr realesr-animevideov3 --sr-scale 2 --fi rife-v4.6 --fi-mult 2
)
echo.
pause
