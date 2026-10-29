@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================
echo  부동산신탁사 재무 대시보드 - 데이터 갱신
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [!] 파이썬이 설치되어 있지 않습니다.
  echo     https://www.python.org/downloads 에서 설치한 뒤 다시 실행하세요.
  echo     설치 첫 화면에서 "Add python.exe to PATH" 를 반드시 체크하세요.
  pause
  exit /b 1
)

if exist fisis_key.txt goto havekey
set /p FISIS_API_KEY=FISIS 인증키를 붙여넣고 Enter: 
echo %FISIS_API_KEY%> fisis_key.txt
echo (인증키를 fisis_key.txt 에 저장했습니다. 다음부터는 묻지 않습니다.)
goto run
:havekey
set /p FISIS_API_KEY=<fisis_key.txt

:run
echo.
echo FISIS에서 데이터를 받는 중입니다 (1~2분)...
python scripts\fetch_fisis.py
if errorlevel 1 (
  echo.
  echo [!] 수집에 실패했습니다. 위 메시지를 캡처해서 Claude에게 보여주세요.
  pause
  exit /b 1
)

echo.
echo Cloudflare 업로드용 압축 파일을 만드는 중...
powershell -NoProfile -Command "Compress-Archive -Path index.html,manifest.webmanifest,sw.js,icons,data -DestinationPath cloudflare-upload.zip -Force"
echo.
echo 완료! 열린 폴더의 cloudflare-upload.zip 을 Cloudflare에 올리세요.
explorer /select,"%~dp0cloudflare-upload.zip"
pause
