@echo off
REM Setup script for Language Learning Content Generator (Windows)

echo Creating directories...
mkdir data\dialogues data\audio data\videos models 2>nul

echo Installing Python dependencies...
pip install -r requirements.txt

echo Downloading NLTK data...
python download_nltk_data.py

REM Check if FFmpeg is installed
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo FFmpeg is not installed. Please install it manually:
    echo   - Download from: https://ffmpeg.org/download.html
    echo   - Or install with Chocolatey: choco install ffmpeg
) else (
    echo FFmpeg is already installed.
)

echo Do you want to download the Vosk speech recognition model? (y/n)
set /p download_vosk=

if /i "%download_vosk%"=="y" (
    echo Downloading Vosk model (small English model, ~40MB)...
    
    REM Check if PowerShell is available
    where powershell >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        powershell -Command "& {Invoke-WebRequest -Uri 'https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip' -OutFile '.\models\vosk-model-small-en-us-0.15.zip'}"
        
        echo Extracting model...
        powershell -Command "& {Expand-Archive -Path '.\models\vosk-model-small-en-us-0.15.zip' -DestinationPath '.\models' -Force}"
        
        REM Remove the zip file
        del .\models\vosk-model-small-en-us-0.15.zip
        
        echo Vosk model downloaded and extracted.
    ) else (
        echo PowerShell is not available. Please download the model manually from:
        echo https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
        echo and extract it to the 'models' directory.
    )
) else (
    echo Skipping Vosk model download. You can download it later from:
    echo https://alphacephei.com/vosk/models
)

echo Setup complete! You can now use the Language Learning Content Generator.
echo Don't forget to set up your API keys in config.py.
pause 