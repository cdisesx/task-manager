@echo off
setlocal
set PYTHONUTF8=1
set SCRIPT_DIR=%~dp0

if not exist "%SCRIPT_DIR%config\config.json" (
  echo [ERR] config\config.json not found.
  pause
  exit /b 1
)

echo [1/3] Installing Python dependencies...
python -m pip install -r "%SCRIPT_DIR%requirements.txt"
if errorlevel 1 goto :err_pip

echo [2/3] Checking Node.js dependencies...
pushd "%SCRIPT_DIR%dashboard" || goto :err_cd
if not exist "node_modules" (
  echo      Installing...
  call npm install
  if errorlevel 1 goto :err_npm
)
popd

echo [3/3] Starting dashboard...
node "%SCRIPT_DIR%dashboard\server.js"
pause
exit /b 0

:err_cd
  echo [ERR] Failed to enter dashboard directory
  pause
  exit /b 1

:err_pip
  echo [ERR] pip install failed
  pause
  exit /b 1

:err_npm
  echo [ERR] npm install failed
  popd
  pause
  exit /b 1
