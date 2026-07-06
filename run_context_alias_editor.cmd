@echo off
setlocal
set "PYTHON_EXE=C:\Users\Namba\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if exist "%PYTHON_EXE%" (
  "%PYTHON_EXE%" context-alias-editor\server.py --host 127.0.0.1 --port 8788
) else (
  python context-alias-editor\server.py --host 127.0.0.1 --port 8788
)
