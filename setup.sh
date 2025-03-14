#!/bin/bash
# Setup script for Language Learning Content Generator

# Create necessary directories
echo "Creating directories..."
mkdir -p data/dialogues data/audio data/videos models

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Download NLTK data
echo "Downloading NLTK data..."
python download_nltk_data.py

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is not installed. Please install it manually:"
    echo "  - Windows: https://ffmpeg.org/download.html or 'choco install ffmpeg' (with Chocolatey)"
    echo "  - macOS: 'brew install ffmpeg' (with Homebrew)"
    echo "  - Linux: 'sudo apt-get install ffmpeg' (Debian/Ubuntu) or 'sudo yum install ffmpeg' (CentOS/RHEL)"
else
    echo "FFmpeg is already installed."
fi

# Download Vosk model
echo "Do you want to download the Vosk speech recognition model? (y/n)"
read -r download_vosk

if [[ $download_vosk == "y" || $download_vosk == "Y" ]]; then
    echo "Downloading Vosk model (small English model, ~40MB)..."
    
    # Check if wget is available, otherwise use curl
    if command -v wget &> /dev/null; then
        wget -c https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -P ./models/
    elif command -v curl &> /dev/null; then
        curl -L https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip -o ./models/vosk-model-small-en-us-0.15.zip
    else
        echo "Neither wget nor curl is installed. Please download the model manually from:"
        echo "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
        echo "and extract it to the 'models' directory."
        exit 1
    fi
    
    # Extract the model
    echo "Extracting model..."
    if command -v unzip &> /dev/null; then
        unzip -o ./models/vosk-model-small-en-us-0.15.zip -d ./models/
        # Remove the zip file
        rm ./models/vosk-model-small-en-us-0.15.zip
    else
        echo "unzip is not installed. Please extract the model manually."
    fi
    
    echo "Vosk model downloaded and extracted."
else
    echo "Skipping Vosk model download. You can download it later from:"
    echo "https://alphacephei.com/vosk/models"
fi

echo "Setup complete! You can now use the Language Learning Content Generator."
echo "Don't forget to set up your API keys in config.py." 