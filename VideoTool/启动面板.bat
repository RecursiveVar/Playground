@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title videotool 网页面板

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py -3"
)
if not defined PY (
  echo 没有找到 Python，请先安装 Python 3.8 或更高版本。
  pause
  exit /b 1
)

echo 正在启动 videotool 网页面板……
echo 服务地址会打印在下一行；关闭此窗口即停止服务。
echo.
%PY% webui.py %*
echo.
pause
