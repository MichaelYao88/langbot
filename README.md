# Language Learning Content Generator

A system for generating language learning content for TikTok/Reels and YouTube. This project automates the creation of engaging language learning videos that incorporate vocabulary words in natural dialogues.

## Features

- Generate vocabulary lists for target languages
- Create natural dialogues that incorporate vocabulary words
- Convert dialogue text to speech using ElevenLabs API
- Generate videos with text, images, and audio
- Track used vocabulary words to avoid repetition

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
   mkdir -p data/dialogues data/audio data/videos
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

### 3. Generate Audio

```bash
python generate_audio.py --dialogue_file data/dialogues/example_12345678.json
```

Options:
- `--dialogue_file`: JSON file containing dialogue data
- `--output_dir`: Directory to save audio files
- `--generate_translations`: Generate audio for translations as well

### 4. Generate Video

```bash
python generate_video.py --dialogue_file data/dialogues/example_12345678.json --audio_dir data/audio/example_12345678 --image_paths images/character1.jpg images/character2.jpg
```

Options:
- `--dialogue_file`: JSON file containing dialogue data
- `--audio_dir`: Directory containing audio files and metadata
- `--image_paths`: Paths to image files to use in the video
- `--output_path`: Path to save the output video

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
   python generate_audio.py --dialogue_file data/dialogues/word_12345678.json
   ```

4. Generate a video using the audio and images:
   ```
   python generate_video.py --dialogue_file data/dialogues/word_12345678.json --audio_dir data/audio/word_12345678 --image_paths images/char1.jpg images/char2.jpg
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
- Images for video generation (e.g., from Midjourney)

## License

This project is licensed under the MIT License - see the LICENSE file for details. 