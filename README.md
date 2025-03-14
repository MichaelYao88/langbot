# Language Learning Content Generator

A system for generating language learning content for TikTok/Reels and YouTube. This project automates the creation of engaging language learning videos that incorporate vocabulary words in natural dialogues.

## Features

- Generate vocabulary lists for target languages
- Create natural dialogues that incorporate vocabulary words
- Convert dialogue text to speech using ElevenLabs API
- Generate videos with text, images, and audio
- Track used vocabulary words to avoid repetition
- Automatic speech recognition for accurate subtitle timing
- Timestamp adjustment for better subtitle synchronization

## Setup

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your API keys in `config.py`:
   - OpenAI API key
   - Anthropic API key (optional)
   - ElevenLabs API key

4. Create directories for data storage:
   ```
   mkdir -p data/dialogues data/audio data/videos models
   ```

5. Download a Vosk model for speech recognition:
   ```
   # Download a model from https://alphacephei.com/vosk/models
   # For example, the small English model:
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip -d models/
   ```

## Usage

The system is designed to be used in a pipeline, with each script handling a specific part of the content generation process.

### 1. Generate Vocabulary List

```bash
python generate_vocab.py --num_words 20 --difficulty intermediate --provider openai
```

Options:
- `--num_words`: Number of vocabulary words to generate (default: 20)
- `--difficulty`: Difficulty level (beginner, intermediate, advanced)
- `--provider`: LLM provider to use (openai, anthropic)
- `--output`: Custom output file path

### 2. Generate Dialogues

```bash
python generate_dialogue.py --num_dialogues 5 --provider openai
```

Options:
- `--word`: Specific vocabulary word to use
- `--translation`: Translation of the vocabulary word
- `--context`: Context or usage information for the word
- `--provider`: LLM provider to use (openai, anthropic)
- `--vocab_file`: JSON file containing vocabulary words
- `--num_dialogues`: Number of dialogues to generate
- `--topic_word`: Specific topic word to use in the dialogue

### 3. Generate Audio

```bash
python generate_audio.py --dialogue_file data/dialogues/example_12345678.json
```

Options:
- `--dialogue_file`: JSON file containing dialogue data
- `--output_dir`: Directory to save audio files
- `--generate_translations`: Generate audio for translations as well

### 4. Generate Dialogue Timestamps

```bash
python generate_dialogue_timestamps.py
```

This script analyzes the audio files and creates corresponding JSON files with dialogue timestamps for subtitle display.

### 5. Generate Accurate Timestamps with Speech Recognition

```bash
python auto_subtitle.py --audio data/audio/example_12345678.mp3
```

Options:
- `--audio`: Path to a specific audio file to process
- `--model`: Path to the Vosk model directory (default: models/vosk-model-small-en-us-0.15)

This script uses automatic speech recognition to generate more accurate timestamps for the dialogue.

### 6. Adjust Timestamps

```bash
python adjust_timestamps.py --dialogue-id 12345678
```

Options:
- `--dialogue-id`: Dialogue ID to process

This script adjusts the timings in the generated timestamp JSON files based on the auto-generated timestamps.

### 7. Generate Background Video

```bash
python generate_background.py --audio data/audio/example_12345678.mp3
```

Options:
- `--output`: Output path for the video
- `--test`: Generate a 10-second test clip
- `--audio`: Specific audio file to use

This script generates a background video with audio and subtitles.

## Example Workflow

1. Generate a vocabulary list:
   ```
   python generate_vocab.py --num_words 10 --difficulty beginner
   ```

2. Generate dialogues for the vocabulary words:
   ```
   python generate_dialogue.py --num_dialogues 3
   ```

3. Generate audio for a dialogue:
   ```
   python generate_audio.py
   ```

4. Generate dialogue timestamps:
   ```
   python generate_dialogue_timestamps.py
   ```

5. Generate accurate timestamps with speech recognition:
   ```
   python auto_subtitle.py
   ```

6. Adjust timestamps:
   ```
   python adjust_timestamps.py
   ```

7. Generate a background video:
   ```
   python generate_background.py
   ```

## Monetization Strategy

1. Post the generated videos on TikTok/Instagram Reels
2. Include translations in the comments section
3. Direct viewers to a YouTube channel with compilations of the videos
4. Monetize the YouTube channel through ads and sponsorships

## Customization

You can customize the system by modifying the `config.py` file:
- Change the target language
- Adjust the number of dialogue turns
- Modify character personalities
- Change voice settings

## Requirements

- Python 3.8+
- OpenAI API key
- ElevenLabs API key
- Anthropic API key (optional)
- FFmpeg for audio/video processing
- Vosk for speech recognition
- Images for video generation (e.g., from Midjourney)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 