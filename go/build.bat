@echo off
setlocal
REM Game Launcher (Go + WebView2) build.
REM   build.bat [version]
REM -s -w: no symbols, -trimpath: no local paths, -H windowsgui: no console.
REM CGO is required by webview_go (MinGW-w64 gcc on PATH).
set VERSION=%~1
if "%VERSION%"=="" set VERSION=dev
set CGO_ENABLED=1
set GOOS=windows
set GOARCH=amd64
pushd "%~dp0"
REM exe icon + version info (needs windres from MinGW-w64; the committed .syso is used otherwise)
where windres >nul 2>nul && go run .\tools\mkrc %VERSION%
go build -trimpath -ldflags="-H windowsgui -s -w -X main.version=%VERSION%" -o build\GameLauncher.exe .\cmd\gamelauncher
if errorlevel 1 (
  popd
  echo Build FAILED.
  exit /b 1
)
popd
echo OK -^> %~dp0build\GameLauncher.exe
endlocal
