$PythonExe = "C:\Users\Namba\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if (Test-Path -LiteralPath $PythonExe) {
    & $PythonExe context-alias-editor\server.py --host 127.0.0.1 --port 8788
} else {
    & python context-alias-editor\server.py --host 127.0.0.1 --port 8788
}
