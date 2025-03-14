#!/usr/bin/env python3
"""
Script to generate accurate dialogue timestamps using automatic speech recognition.
This script uses the Vosk library to perform speech recognition on audio files
and generate precise timestamps for each word, which are then combined into phrases
for subtitle display.
"""

import os
import json
import glob
import re
import subprocess
import argparse
import wave
import sys
from pathlib import Path
import config
import tempfile
import shutil
import csv

# Check if Vosk is installed
try:
    from vosk import Model, KaldiRecognizer, SetLogLevel
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("Vosk is not installed. Please install it with: pip install vosk")
    print("You will also need to download a model from https://alphacephei.com/vosk/models")

def convert_to_wav(audio_file, output_file=None):
    """
    Convert an audio file to WAV format with 16kHz sample rate and mono channel.
    
    Args:
        audio_file: Path to the input audio file
        output_file: Path to save the output WAV file (optional)
    
    Returns:
        Path to the converted WAV file
    """
    if output_file is None:
        # Create a temporary file
        temp_dir = tempfile.mkdtemp()
        output_file = os.path.join(temp_dir, "temp_audio.wav")
    
    # Use FFmpeg to convert the audio file
    cmd = [
        "ffmpeg",
        "-i", audio_file,
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",      # Mono channel
        "-y",            # Overwrite output file if it exists
        output_file
    ]
    
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    if not os.path.exists(output_file):
        raise FileNotFoundError(f"Failed to convert {audio_file} to WAV format")
    
    return output_file

def get_audio_duration(audio_file):
    """
    Get the duration of an audio file using ffprobe.
    
    Args:
        audio_file: Path to the audio file
    
    Returns:
        Duration in seconds
    """
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audio_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return float(result.stdout.strip())

def find_dialogue_file(dialogue_id):
    """
    Find a dialogue JSON file by ID.
    
    Args:
        dialogue_id: The dialogue ID to find
    
    Returns:
        The dialogue data as a dictionary, or None if not found
    """
    dialogue_files = glob.glob("data/dialogues/*.json")
    for file_path in dialogue_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            dialogue_data = json.load(f)
            if dialogue_data["id"] == dialogue_id:
                return dialogue_data
    return None

def extract_vietnamese_vocab(dialogue_data):
    """
    Extract Vietnamese vocabulary words from the dialogue data.
    
    Args:
        dialogue_data: The dialogue data dictionary
    
    Returns:
        Set of Vietnamese vocabulary words
    """
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

def is_vietnamese_word(word, vietnamese_vocab=None):
    """
    Check if a word is Vietnamese based on diacritics or vocabulary.
    
    Args:
        word: The word to check
        vietnamese_vocab: Set of Vietnamese vocabulary words to check against
    
    Returns:
        Boolean indicating if the word is Vietnamese
    """
    if not vietnamese_vocab:
        vietnamese_vocab = set()
    
    # Remove punctuation for checking
    clean_word = re.sub(r'[^\w\s]', '', word.lower())
    
    # Check if the word is in the Vietnamese vocabulary
    if clean_word in vietnamese_vocab:
        return True
    
    # Check for Vietnamese diacritics
    vietnamese_pattern = r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]'
    return bool(re.search(vietnamese_pattern, word))

def recognize_speech(wav_file, model_path="models/vosk-model-small-en-us-0.15"):
    """
    Perform speech recognition on a WAV file using Vosk.
    
    Args:
        wav_file: Path to the WAV file
        model_path: Path to the Vosk model
    
    Returns:
        List of recognized words with timestamps
    """
    if not VOSK_AVAILABLE:
        print("Vosk is not available. Cannot perform speech recognition.")
        return None
    
    # Check if the model exists
    if not os.path.exists(model_path):
        print(f"Vosk model not found at {model_path}")
        print("Please download a model from https://alphacephei.com/vosk/models")
        print("and extract it to the models directory")
        return None
    
    # Reduce log output
    SetLogLevel(-1)
    
    # Load the model
    model = Model(model_path)
    
    # Open the WAV file
    wf = wave.open(wav_file, "rb")
    
    # Check if the WAV file has the correct format
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
        print("Audio file must be WAV format mono PCM.")
        return None
    
    # Create a recognizer
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)  # Enable word timestamps
    
    # Process the audio file
    results = []
    
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        if rec.AcceptWaveform(data):
            part_result = json.loads(rec.Result())
            if "result" in part_result:
                results.extend(part_result["result"])
    
    # Get the final result
    part_result = json.loads(rec.FinalResult())
    if "result" in part_result:
        results.extend(part_result["result"])
    
    return results

def assign_speakers_to_words(recognized_words, dialogue_data):
    """
    Assign speakers to recognized words based on the dialogue data.
    
    Args:
        recognized_words: List of recognized words with timestamps
        dialogue_data: The dialogue data dictionary
    
    Returns:
        List of recognized words with speaker information
    """
    if not recognized_words or not dialogue_data or "english_dialogue" not in dialogue_data:
        return recognized_words
    
    # Extract the dialogue lines
    dialogue_lines = dialogue_data["english_dialogue"]
    
    # Calculate the total audio duration based on the last word's end time
    if recognized_words:
        total_duration = recognized_words[-1]["end"]
    else:
        return recognized_words
    
    # Calculate the approximate start and end times for each dialogue line
    # based on their relative position in the text
    total_text_length = sum(len(line["text"]) for line in dialogue_lines)
    line_timestamps = []
    current_time = 0
    
    for line in dialogue_lines:
        line_length = len(line["text"])
        line_duration = (line_length / total_text_length) * total_duration if total_text_length > 0 else 0
        line_end_time = current_time + line_duration
        
        line_timestamps.append({
            "speaker": line["speaker"],
            "start_time": current_time,
            "end_time": line_end_time,
            "text": line["text"]
        })
        
        current_time = line_end_time
    
    # Assign speakers to words based on their timestamps
    for word in recognized_words:
        word_time = (word["start"] + word["end"]) / 2
        
        # Find the dialogue line that contains this word
        for line in line_timestamps:
            if line["start_time"] <= word_time <= line["end_time"]:
                word["speaker"] = line["speaker"]
                break
        
        # Default speaker if not found
        if "speaker" not in word:
            word["speaker"] = "Unknown"
    
    return recognized_words

def group_words_into_phrases(recognized_words, max_words_per_phrase=3):
    """
    Group recognized words into phrases for better subtitle display.
    
    Args:
        recognized_words: List of recognized words with timestamps and speakers
        max_words_per_phrase: Maximum number of words per phrase
    
    Returns:
        List of phrases with timestamps and speakers
    """
    if not recognized_words:
        return []
    
    phrases = []
    current_phrase = {
        "words": [],
        "speaker": recognized_words[0]["speaker"],
        "start_time": recognized_words[0]["start"],
        "end_time": recognized_words[0]["end"],
        "word_timestamps": []  # Add a list to store individual word timestamps
    }
    
    for word in recognized_words:
        # If the speaker changes or we've reached the maximum words per phrase,
        # or if we encounter punctuation, end the current phrase
        is_punctuation = word["word"] in ['.', ',', '!', '?', ';', ':']
        
        if (word["speaker"] != current_phrase["speaker"] or 
            len(current_phrase["words"]) >= max_words_per_phrase or
            is_punctuation):
            
            # Add punctuation to the current phrase
            if is_punctuation:
                current_phrase["words"].append(word["word"])
                current_phrase["end_time"] = word["end"]
                current_phrase["word_timestamps"].append({
                    "word": word["word"],
                    "start": word["start"],
                    "end": word["end"]
                })
            
            # Finalize the current phrase
            if current_phrase["words"]:
                phrase_text = ' '.join(current_phrase["words"])
                phrases.append({
                    "speaker": current_phrase["speaker"],
                    "text": phrase_text,
                    "start_time": round(current_phrase["start_time"], 2),
                    "end_time": round(current_phrase["end_time"], 2),
                    "word_timestamps": current_phrase["word_timestamps"]
                })
            
            # Start a new phrase
            if not is_punctuation:
                current_phrase = {
                    "words": [word["word"]],
                    "speaker": word["speaker"],
                    "start_time": word["start"],
                    "end_time": word["end"],
                    "word_timestamps": [{
                        "word": word["word"],
                        "start": word["start"],
                        "end": word["end"]
                    }]
                }
            else:
                current_phrase = {
                    "words": [],
                    "speaker": word["speaker"],
                    "start_time": word["end"],
                    "end_time": word["end"],
                    "word_timestamps": []
                }
        else:
            # Add the word to the current phrase
            current_phrase["words"].append(word["word"])
            current_phrase["end_time"] = word["end"]
            current_phrase["word_timestamps"].append({
                "word": word["word"],
                "start": word["start"],
                "end": word["end"]
            })
    
    # Add the last phrase if it's not empty
    if current_phrase["words"]:
        phrase_text = ' '.join(current_phrase["words"])
        phrases.append({
            "speaker": current_phrase["speaker"],
            "text": phrase_text,
            "start_time": round(current_phrase["start_time"], 2),
            "end_time": round(current_phrase["end_time"], 2),
            "word_timestamps": current_phrase["word_timestamps"]
        })
    
    return phrases

def identify_vietnamese_words(phrases, vietnamese_vocab):
    """
    Identify Vietnamese words in phrases.
    
    Args:
        phrases: List of phrases
        vietnamese_vocab: Set of Vietnamese vocabulary words
    
    Returns:
        List of phrases with Vietnamese words identified
    """
    for phrase in phrases:
        viet_words = []
        
        # Check each word in the phrase
        words = re.findall(r'\b\w+\b', phrase["text"])
        for word in words:
            if is_vietnamese_word(word, vietnamese_vocab):
                viet_words.append(word)
        
        # Add Vietnamese words to the phrase
        phrase["viet_words"] = viet_words
    
    return phrases

def create_word_timestamp_log(recognized_words, output_path):
    """
    Create a CSV log file with word-by-word timestamps.
    
    Args:
        recognized_words: List of recognized words with timestamps
        output_path: Path to save the CSV file
    """
    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Write the CSV file
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Word', 'Start Time', 'End Time', 'Speaker'])
        
        for word in recognized_words:
            writer.writerow([
                word["word"],
                round(word["start"], 3),
                round(word["end"], 3),
                word.get("speaker", "Unknown")
            ])
    
    print(f"Word timestamp log saved to: {output_path}")

def generate_auto_timestamps(audio_file, model_path="models/vosk-model-small-en-us-0.15"):
    """
    Generate accurate timestamps for an audio file using speech recognition.
    
    Args:
        audio_file: Path to the audio file
        model_path: Path to the Vosk model
    
    Returns:
        Path to the generated JSON file, or None if failed
    """
    # Extract the dialogue ID from the filename
    filename = os.path.basename(audio_file)
    
    # Try different filename patterns
    # Old pattern: dialogue_ID_elevenlabs_slow.mp3
    old_pattern_match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
    
    # New pattern without topic word: dialogue_ID.mp3
    new_pattern_without_topic_match = re.match(r'dialogue_([a-f0-9]+)\.mp3', filename)
    
    # New pattern with topic word: topic_word_ID.mp3
    new_pattern_with_topic_match = re.match(r'.*_([a-f0-9]+)\.mp3', filename)
    
    # Determine which pattern matched
    if old_pattern_match:
        dialogue_id = old_pattern_match.group(1)
    elif new_pattern_without_topic_match:
        dialogue_id = new_pattern_without_topic_match.group(1)
    elif new_pattern_with_topic_match:
        dialogue_id = new_pattern_with_topic_match.group(1)
    else:
        print(f"Could not extract dialogue ID from filename: {filename}")
        return None
    
    # Find the corresponding dialogue file
    dialogue_data = find_dialogue_file(dialogue_id)
    
    if not dialogue_data:
        print(f"Could not find dialogue file for ID: {dialogue_id}")
        return None
    
    # Extract Vietnamese vocabulary
    vietnamese_vocab = extract_vietnamese_vocab(dialogue_data)
    
    # Convert the audio file to WAV format
    print(f"Converting {audio_file} to WAV format...")
    wav_file = convert_to_wav(audio_file)
    
    # Perform speech recognition
    print(f"Performing speech recognition on {wav_file}...")
    recognized_words = recognize_speech(wav_file, model_path)
    
    # Clean up the temporary WAV file
    if os.path.dirname(wav_file) != os.path.dirname(audio_file):
        temp_dir = os.path.dirname(wav_file)
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    if not recognized_words:
        print(f"Speech recognition failed for {audio_file}")
        return None
    
    # Assign speakers to words
    print("Assigning speakers to recognized words...")
    recognized_words = assign_speakers_to_words(recognized_words, dialogue_data)
    
    # Create a word timestamp log
    log_path = os.path.join(config.AUDIO_PATH, f"word_timestamps_{dialogue_id}.csv")
    create_word_timestamp_log(recognized_words, log_path)
    
    # Save the raw word timestamps
    raw_word_json_path = os.path.join(config.AUDIO_PATH, f"word_timestamps_{dialogue_id}.json")
    with open(raw_word_json_path, 'w', encoding='utf-8') as f:
        json.dump(recognized_words, f, ensure_ascii=False, indent=2)
    print(f"Raw word timestamps saved to: {raw_word_json_path}")
    
    # Group words into phrases
    print("Grouping words into phrases...")
    phrases = group_words_into_phrases(recognized_words)
    
    # Identify Vietnamese words in phrases
    print("Identifying Vietnamese words in phrases...")
    phrases = identify_vietnamese_words(phrases, vietnamese_vocab)
    
    # Create the output JSON data
    output_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": phrases
    }
    
    # Create the output filename
    output_filename = f"dialogue_{dialogue_id}_auto.json"
    output_path = os.path.join(config.AUDIO_PATH, output_filename)
    
    # Write the JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Generated auto timestamp JSON file: {output_path}")
    return output_path

def main():
    """Main function to process audio files."""
    parser = argparse.ArgumentParser(description="Generate accurate dialogue timestamps using speech recognition")
    parser.add_argument("--audio", type=str, help="Path to a specific audio file to process")
    parser.add_argument("--model", type=str, default="models/vosk-model-small-en-us-0.15", 
                        help="Path to the Vosk model directory")
    args = parser.parse_args()
    
    # Check if Vosk is available
    if not VOSK_AVAILABLE:
        print("Vosk is not installed. Please install it with: pip install vosk")
        print("You will also need to download a model from https://alphacephei.com/vosk/models")
        return
    
    # Check if the model exists
    if not os.path.exists(args.model):
        print(f"Vosk model not found at {args.model}")
        print("Please download a model from https://alphacephei.com/vosk/models")
        print("and extract it to the models directory")
        return
    
    # Process a specific audio file if provided
    if args.audio:
        if not os.path.exists(args.audio):
            print(f"Audio file not found: {args.audio}")
            return
        
        generate_auto_timestamps(args.audio, args.model)
        return
    
    # Otherwise, process all audio files
    audio_files = []
    
    # Old naming convention
    old_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*_elevenlabs_slow.mp3"))
    audio_files.extend(old_files)
    
    # New naming convention - look for any MP3 files that aren't already covered
    all_mp3_files = glob.glob(os.path.join(config.AUDIO_PATH, "*.mp3"))
    for file in all_mp3_files:
        if file not in old_files and not os.path.basename(file).startswith("dialogue_"):
            audio_files.append(file)
    
    if not audio_files:
        print("No audio files found.")
        return
    
    print(f"Found {len(audio_files)} audio files to process.")
    
    # Process each audio file
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        generate_auto_timestamps(audio_file, args.model)

if __name__ == "__main__":
    main() 