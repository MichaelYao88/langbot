#!/usr/bin/env python3
"""
Script to generate audio from dialogue files by:
1. Cutting each line of English dialogue into segments based on Vietnamese words
2. Generating audio for English segments using ElevenLabs with language_code="en"
3. Generating audio for Vietnamese segments using ElevenLabs with language_code="vi"
4. Stitching segments together with 40ms pauses
5. Creating a single audio file for the entire dialogue with 50ms pauses between speakers
"""

import os
import json
import re
import requests
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import logging
import time
import config
from utils import logger, ensure_directories_exist
import sys
import shutil
import glob

# Load environment variables
print("Loading environment variables...")
load_dotenv(override=True)

# Constants
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"
VOICE_MIRA = os.getenv("VOICE_MIRA")
VOICE_MICHAEL = os.getenv("VOICE_MICHAEL")
PAUSE_DURATION_MS = 1  # Duration of pause in milliseconds between language segments
SPEAKER_PAUSE_DURATION_MS = 50  # Duration of pause in milliseconds between speakers
ELEVENLABS_VOLUME_BOOST_DB = 6.0  # Increase ElevenLabs volume by this many dB
VIETNAMESE_SPEECH_RATE = 0.8  # Slow down Vietnamese speech (0.8 = 80% of normal speed)
ENGLISH_SPEECH_RATE = 0.8  # Slow down English speech (0.9 = 90% of normal speed)

# Flag to track if ElevenLabs quota is exceeded
elevenlabs_quota_exceeded = False

# Cache for Vietnamese word audio
vietnamese_audio_cache = {
    "male": {},  # Cache for male voice
    "female": {}  # Cache for female voice
}

# Check for required dependencies
try:
    from gtts import gTTS
except ImportError:
    logger.error("gTTS is required. Please install it with: pip install gTTS")
    sys.exit(1)

# Check for FFmpeg
def check_ffmpeg():
    """Check if FFmpeg is installed and accessible."""
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

# Try to import pydub for audio processing
has_pydub = False
has_ffmpeg = check_ffmpeg()

if has_ffmpeg:
    try:
        from pydub import AudioSegment
        has_pydub = True
        logger.info("Using pydub for audio processing")
    except ImportError:
        logger.warning("pydub is not installed. Will use direct file output instead.")
else:
    logger.warning("FFmpeg is not installed. Will use direct file output instead.")
    logger.warning("For better audio processing, install FFmpeg from: https://ffmpeg.org/download.html")
    logger.warning("For Windows users, you can also use: choco install ffmpeg (as administrator)")

def extract_vietnamese_vocab_from_dialogue(dialogue_data):
    """Extract Vietnamese vocabulary words from the dialogue data."""
    vocab_words = set()
    
    # Add the topic word
    if "topic_word" in dialogue_data and dialogue_data["topic_word"]:
        vocab_words.add(dialogue_data["topic_word"].lower())
    
    # Add common words
    if "common_words" in dialogue_data and dialogue_data["common_words"]:
        for word_data in dialogue_data["common_words"]:
            if "word" in word_data and word_data["word"]:
                vocab_words.add(word_data["word"].lower())
    
    return vocab_words

def identify_vietnamese_segments(text, vietnamese_vocab=None):
    """
    Identify Vietnamese segments in the text.
    Returns a list of tuples (text, is_vietnamese).
    
    Args:
        text: The text to analyze
        vietnamese_vocab: Set of Vietnamese vocabulary words to identify
    """
    if not vietnamese_vocab:
        vietnamese_vocab = set()
    
    # This regex pattern matches Vietnamese characters and diacritics
    vietnamese_pattern = r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]+'
    
    # First, check for multi-word Vietnamese phrases in the text
    # This helps catch phrases like "co vua" where individual words might not be recognized
    multi_word_phrases = [word for word in vietnamese_vocab if ' ' in word]
    
    # Create a list of (start_index, end_index, phrase) for each multi-word phrase found in the text
    phrase_positions = []
    for phrase in multi_word_phrases:
        # Use case-insensitive search
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        for match in pattern.finditer(text.lower()):
            phrase_positions.append((match.start(), match.end(), phrase))
    
    # Sort by start position
    phrase_positions.sort()
    
    # Now process the text word by word, but be aware of multi-word phrases
    words = text.split()
    segments = []
    current_segment = []
    current_is_vietnamese = False
    
    # Track the character position as we process words
    char_pos = 0
    
    for word in words:
        # Skip leading spaces
        char_pos = text.find(word, char_pos)
        word_end = char_pos + len(word)
        
        # Check if this word is part of a multi-word phrase
        is_in_phrase = False
        for start, end, phrase in phrase_positions:
            if (start <= char_pos < end) or (start < word_end <= end):
                is_in_phrase = True
                break
        
        # Check if the word contains Vietnamese characters
        is_vietnamese_by_diacritics = bool(re.search(vietnamese_pattern, word))
        
        # Check if the word is a single-word Vietnamese vocabulary item
        is_vietnamese_by_vocab = word.lower() in vietnamese_vocab
        
        is_vietnamese = is_vietnamese_by_diacritics or is_vietnamese_by_vocab or is_in_phrase
        
        # If we're switching between Vietnamese and non-Vietnamese, create a new segment
        if is_vietnamese != current_is_vietnamese and current_segment:
            segments.append((' '.join(current_segment), current_is_vietnamese))
            current_segment = []
        
        current_segment.append(word)
        current_is_vietnamese = is_vietnamese
        
        # Move to the next word
        char_pos = word_end
    
    # Add the last segment
    if current_segment:
        segments.append((' '.join(current_segment), current_is_vietnamese))
    
    # Log the segments for debugging
    for segment, is_vietnamese in segments:
        logger.debug(f"Segment: '{segment}' - Vietnamese: {is_vietnamese}")
    
    return segments

def generate_elevenlabs_audio(text, voice_id, output_file=None, language_code="en"):
    """Generate audio using ElevenLabs API with specified language code."""
    global elevenlabs_quota_exceeded
    
    # If quota is already exceeded, don't even try ElevenLabs
    if elevenlabs_quota_exceeded:
        logger.info(f"ElevenLabs quota exceeded, using Google TTS fallback for {language_code} text")
        return generate_gtts_audio(text, output_file=output_file, lang=language_code)
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # Set speech rate based on language
    speech_rate = VIETNAMESE_SPEECH_RATE if language_code == "vi" else ENGLISH_SPEECH_RATE
    
    data = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5,
            "style": 0.0,
            "use_speaker_boost": True,
            "speaking_rate": speech_rate  # Apply appropriate speech rate
        }
    }
    
    # Add language code for Vietnamese
    if language_code == "vi":
        data["language_code"] = "vi"
    
    logger.info(f"Generating ElevenLabs audio for: {text[:50]}... (Language: {language_code}, Rate: {speech_rate})")
    
    try:
        response = requests.post(
            f"{ELEVENLABS_API_URL}/{voice_id}",
            json=data,
            headers=headers
        )
        
        if response.status_code == 401 and "quota_exceeded" in response.text:
            logger.warning("ElevenLabs quota exceeded, switching to Google TTS for all segments")
            elevenlabs_quota_exceeded = True
            return generate_gtts_audio(text, output_file=output_file, lang=language_code)
        
        if response.status_code != 200:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            return generate_gtts_audio(text, output_file=output_file, lang=language_code)
        
        # If output_file is provided, save directly to that file
        if output_file:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            return output_file
        
        # Otherwise, create a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        
        # If pydub is available, return AudioSegment
        if has_pydub:
            audio_segment = AudioSegment.from_mp3(temp_path)
            # Increase the volume of ElevenLabs audio
            audio_segment = audio_segment + ELEVENLABS_VOLUME_BOOST_DB
            return audio_segment
        else:
            return temp_path
            
    except Exception as e:
        logger.error(f"Error generating ElevenLabs audio: {str(e)}")
        return generate_gtts_audio(text, output_file=output_file, lang=language_code)

def generate_gtts_audio(text, output_file=None, lang='vi', gender=None):
    """Generate audio using Google Text-to-Speech."""
    logger.info(f"Generating Google TTS audio for: {text} (Language: {lang})")
    
    # Google TTS doesn't directly support gender selection, but we can try to match
    # the voice by using different TLD options
    tld = "com"  # Default TLD
    
    # If output_file is provided, save directly to that file
    if output_file:
        tts = gTTS(text=text, lang=lang, tld=tld, slow=True if lang == 'vi' else False)
        tts.save(output_file)
        return output_file
    
    # Otherwise, create a temporary file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_path = temp_file.name
    
    tts = gTTS(text=text, lang=lang, tld=tld, slow=True if lang == 'vi' else False)
    tts.save(temp_path)
    
    # If pydub is available, return AudioSegment
    if has_pydub:
        return AudioSegment.from_mp3(temp_path)
    else:
        return temp_path

def get_vietnamese_audio(text, voice_id, gender):
    """Get Vietnamese audio from cache or generate it if not cached."""
    global vietnamese_audio_cache
    
    # Normalize text for cache key
    cache_key = text.lower().strip()
    gender_key = "male" if gender == "male" else "female"
    
    # Check if audio is already in cache
    if cache_key in vietnamese_audio_cache[gender_key]:
        logger.info(f"Using cached Vietnamese audio for: {text}")
        return vietnamese_audio_cache[gender_key][cache_key]
    
    # Generate audio if not in cache
    logger.info(f"Generating new Vietnamese audio for: {text} (Gender: {gender_key})")
    audio = generate_elevenlabs_audio(text, voice_id, language_code="vi")
    
    # Cache the audio
    vietnamese_audio_cache[gender_key][cache_key] = audio
    
    return audio

def process_dialogue_line(line, speaker, output_dir, vietnamese_vocab=None):
    """Process a single dialogue line and generate audio."""
    segments = identify_vietnamese_segments(line["text"], vietnamese_vocab)
    
    # Determine which voice to use based on speaker
    voice_id = VOICE_MIRA if speaker == "Mira" else VOICE_MICHAEL
    gender = "female" if speaker == "Mira" else "male"
    
    # If pydub is available, use it to stitch audio segments
    if has_pydub:
        combined_audio = AudioSegment.empty()
        
        for i, (text, is_vietnamese) in enumerate(segments):
            # Generate audio for the segment
            if is_vietnamese:
                # Use cached Vietnamese audio or generate new if not cached
                segment_audio = get_vietnamese_audio(text, voice_id, gender)
            else:
                # Use ElevenLabs for English with default language_code="en"
                segment_audio = generate_elevenlabs_audio(text, voice_id)
            
            # Add the segment to the combined audio
            if segment_audio:
                combined_audio += segment_audio
                
                # Add pause after each segment except the last one
                if i < len(segments) - 1:
                    pause = AudioSegment.silent(duration=PAUSE_DURATION_MS)
                    combined_audio += pause
        
        return combined_audio
    
    # If pydub is not available, just generate audio for the first segment
    # This is a simplified approach for the demo
    else:
        if segments:
            text, is_vietnamese = segments[0]
            
            # Generate audio for the first segment
            if is_vietnamese:
                output_file = os.path.join(output_dir, f"{speaker}_vietnamese_segment.mp3")
                return get_vietnamese_audio(text, voice_id, gender)
            else:
                output_file = os.path.join(output_dir, f"{speaker}_english_segment.mp3")
                return generate_elevenlabs_audio(text, voice_id, output_file=output_file)
    
    return None

def get_processed_dialogues():
    """Get a list of dialogue IDs that have already been processed."""
    processed_ids = set()
    audio_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*.mp3"))
    
    for file_path in audio_files:
        # Extract the dialogue ID from the filename
        filename = os.path.basename(file_path)
        if "_" in filename:
            dialogue_id = filename.split("_")[1].split(".")[0]
            processed_ids.add(dialogue_id)
    
    return processed_ids

def process_dialogue_file(file_path, output_dir):
    """Process a dialogue file and generate audio for the entire dialogue."""
    ensure_directories_exist()
    
    # Load the dialogue file
    with open(file_path, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    dialogue_id = dialogue_data["id"]
    
    # Check if this dialogue has already been processed
    processed_ids = get_processed_dialogues()
    if dialogue_id in processed_ids:
        logger.info(f"Dialogue {dialogue_id} has already been processed. Skipping.")
        return None
    
    # Process all lines in the dialogue
    if not dialogue_data["english_dialogue"]:
        logger.error(f"No English dialogue found in {file_path}")
        return None
    
    if not has_pydub:
        logger.error("Pydub is required for processing entire dialogues.")
        return None
    
    # Extract Vietnamese vocabulary words from the dialogue
    vietnamese_vocab = extract_vietnamese_vocab_from_dialogue(dialogue_data)
    logger.info(f"Extracted Vietnamese vocabulary words: {', '.join(vietnamese_vocab)}")
    
    # Pre-generate all Vietnamese words for both genders to cache them
    logger.info("Pre-generating Vietnamese words for caching...")
    for word in vietnamese_vocab:
        # Generate for male voice (Michael)
        get_vietnamese_audio(word, VOICE_MICHAEL, "male")
        # Generate for female voice (Mira)
        get_vietnamese_audio(word, VOICE_MIRA, "female")
    
    # Create a combined audio for the entire dialogue
    combined_audio = AudioSegment.empty()
    
    for i, line in enumerate(dialogue_data["english_dialogue"]):
        speaker = line["speaker"]
        logger.info(f"Processing line {i+1}/{len(dialogue_data['english_dialogue'])} by {speaker}")
        
        # Process the line
        line_audio = process_dialogue_line(line, speaker, output_dir, vietnamese_vocab)
        
        # Add the line to the combined audio
        if line_audio:
            if i > 0:  # Add pause between speakers, but not before the first line
                pause = AudioSegment.silent(duration=SPEAKER_PAUSE_DURATION_MS)
                combined_audio += pause
            
            combined_audio += line_audio
    
    # Save the combined audio
    output_file = os.path.join(output_dir, f"dialogue_{dialogue_id}_elevenlabs_slow.mp3")
    combined_audio.export(output_file, format="mp3")
    
    logger.info(f"Generated audio for entire dialogue saved to: {output_file}")
    return output_file

def main():
    """Main function to process a dialogue file that hasn't been processed before."""
    # Get all dialogue files
    dialogue_files = sorted(Path(config.DIALOGUES_PATH).glob("*.json"))
    if not dialogue_files:
        logger.error("No dialogue files found.")
        return
    
    # Get already processed dialogue IDs
    processed_ids = get_processed_dialogues()
    
    # Find a dialogue that hasn't been processed yet
    unprocessed_file = None
    for file_path in dialogue_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            dialogue_data = json.load(f)
        
        dialogue_id = dialogue_data["id"]
        # Check if we have a version with "_elevenlabs_slow" suffix
        if f"dialogue_{dialogue_id}_elevenlabs_slow.mp3" not in [os.path.basename(f) for f in glob.glob(os.path.join(config.AUDIO_PATH, "*.mp3"))]:
            unprocessed_file = file_path
            break
    
    if not unprocessed_file:
        logger.info("All dialogues have been processed with ElevenLabs. No new dialogues to generate.")
        return
    
    logger.info(f"Processing dialogue file: {unprocessed_file}")
    
    # Process the file
    output_file = process_dialogue_file(unprocessed_file, config.AUDIO_PATH)
    
    if output_file:
        logger.info(f"Audio generation complete. Output file: {output_file}")
    else:
        logger.error("Failed to generate audio.")

if __name__ == "__main__":
    main() 