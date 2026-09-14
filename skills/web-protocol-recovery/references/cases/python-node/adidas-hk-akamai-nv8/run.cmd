@echo off
rem 双击即可运行并查看离线数据（也可在终端执行 run.cmd --print-body）
setlocal
cd /d "%~dp0"
python entry.py %*
echo.
echo （按任意键关闭窗口）
pause >nul
