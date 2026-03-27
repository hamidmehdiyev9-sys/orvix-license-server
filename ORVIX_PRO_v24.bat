@echo off
REM "Select an app" olmasin: yalniz tam yol ile .exe (PATH sart deyil)
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "SCRIPT=%~dp0ORVIX_PRO_v24.py"

set "PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe"
if exist "%PY%" (
  start "" "%PY%" -3 "%SCRIPT%"
  exit /b 0
)

for %%V in (312 311 310 313 39) do (
  set "PW=%LOCALAPPDATA%\Programs\Python\Python%%V\pythonw.exe"
  if exist "!PW!" (
    start "" "!PW!" "%SCRIPT%"
    exit /b 0
  )
)

for %%V in (312 311 310) do (
  if exist "C:\Python%%V\pythonw.exe" (
    start "" "C:\Python%%V\pythonw.exe" "%SCRIPT%"
    exit /b 0
  )
)

for %%V in (312 311 310) do (
  if exist "C:\Python%%V\python.exe" (
    start "" "C:\Python%%V\python.exe" "%SCRIPT%"
    exit /b 0
  )
)

if exist "%ProgramFiles%\Python312\pythonw.exe" (
  start "" "%ProgramFiles%\Python312\pythonw.exe" "%SCRIPT%"
  exit /b 0
)

REM Son çarə: VBS (özü də tam yolu tapir)
if exist "%~dp0ORVIX_PRO_v24_launch.vbs" (
  wscript //nologo "%~dp0ORVIX_PRO_v24_launch.vbs"
  exit /b %errorlevel%
)

echo Python tapilmadi: C:\Python312\ ve ya python.org
pause
exit /b 1
