@echo off
chcp 65001 >nul
title AstroPulse India - Server (Port 9001)
cd /d "%~dp0"

rem ---- Python: पहले venv, नहीं मिले तो सिस्टम Python ----
if exist "venv\Scripts\python.exe" (
    set "PY=venv\Scripts\python.exe"
) else (
    set "PY=python"
)

rem ---- AI चैटबॉट के लिए Gemini key (सिर्फ अपने कंप्यूटर पर, इस फाइल को GitHub पर push न करें) ----
rem set GEMINI_API_KEY=यहां_अपनी_key_लिखें

rem ---- 4 सेकंड बाद browser खुलेगा (सर्वर के चालू होने का समय) ----
start "" /b cmd /c "timeout /t 4 /nobreak >nul & start "" http://localhost:9001"

echo AstroPulse India चालू है: http://localhost:9001
echo बंद करने के लिए इस विंडो में Ctrl+C दबाएँ या विंडो बंद कर दें।
echo.

rem ---- सर्वर इसी विंडो में चालू (यहीं सारे logs दिखेंगे) ----
"%PY%" -m uvicorn main:app --host 0.0.0.0 --port 9001
pause