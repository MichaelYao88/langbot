#!/usr/bin/env python3
"""
Script to generate JSON files with dialogue timestamps for audio files.
This script analyzes the audio files and creates corresponding JSON files
with the same name (without the _elevenlabs_slow suffix) containing dialogue
with timestamps broken into very small phrases for better subtitle display.
"""

import os
import json
import glob
from pathlib import Path
import subprocess
import re
import config
from pydub import AudioSegment
import nltk

# Download NLTK data if not already downloaded
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

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

def extract_vietnamese_phrases(text, vietnamese_vocab=None):
    """
    Extract Vietnamese phrases from text, including multi-word phrases.
    
    Args:
        text: The text to analyze
        vietnamese_vocab: Set of Vietnamese vocabulary words to check against
    
    Returns:
        List of Vietnamese phrases found in the text
    """
    # First, identify common Vietnamese multi-word phrases
    common_phrases = [
        "bóng đá", "giấc mơ", "Sài Gòn", "trùng hợp", "cổ vũ", "đánh giá",
        "tiếng Việt", "người Việt", "Việt Nam", "phở bò", "bánh mì", "cà phê",
        "cơm tấm", "bún chả", "hủ tiếu", "bánh xèo", "chả giò", "gỏi cuốn"
    ]
    
    # Add any phrases from the vocabulary
    if vietnamese_vocab:
        for word in vietnamese_vocab:
            if " " in word and word not in common_phrases:
                common_phrases.append(word)
    
    # Find all Vietnamese phrases in the text
    viet_phrases = []
    
    # First check for multi-word phrases
    for phrase in common_phrases:
        if phrase in text:
            viet_phrases.append(phrase)
    
    # Then check for individual Vietnamese words
    # But exclude words that are already part of identified phrases
    words = re.findall(r'\b\w+\b', text)
    for word in words:
        if is_vietnamese_word(word, vietnamese_vocab):
            # Check if this word is already part of a phrase
            is_in_phrase = False
            for phrase in viet_phrases:
                if word in phrase.split():
                    is_in_phrase = True
                    break
            
            if not is_in_phrase:
                viet_phrases.append(word)
    
    return viet_phrases

def split_text_into_words(text, vietnamese_vocab=None):
    """
    Split text into individual words for more precise subtitle timing.
    Ensures Vietnamese words and phrases aren't broken apart.
    
    Args:
        text: The text to split
        vietnamese_vocab: Set of Vietnamese vocabulary words to check against
    
    Returns:
        List of dictionaries with text and Vietnamese word flags
    """
    # First, identify and protect Vietnamese tags
    # Find all Vietnamese tag pairs and their content
    vietnamese_tags = re.findall(r'<vietnamese>([^<]+)</vietnamese>', text)
    text_with_placeholders = text
    
    # Replace each Vietnamese tag pair with a special token
    viet_tag_map = {}
    for i, viet_content in enumerate(vietnamese_tags):
        placeholder = f"__VIET_TAG_{i}__"
        viet_tag_map[placeholder] = {
            "text": viet_content,
            "full_tag": f"<vietnamese>{viet_content}</vietnamese>"
        }
        text_with_placeholders = text_with_placeholders.replace(
            f"<vietnamese>{viet_content}</vietnamese>", 
            f" {placeholder} "
        )
    
    # Extract all Vietnamese phrases in the text (those not in tags)
    viet_phrases = extract_vietnamese_phrases(text_with_placeholders, vietnamese_vocab)
    
    # Create a clean version of the text for processing
    clean_text = text_with_placeholders
    
    # Sort phrases by length (descending) to handle longer phrases first
    sorted_phrases = sorted(viet_phrases, key=len, reverse=True)
    
    # Replace each Vietnamese phrase with a special token
    token_map = {}
    for i, phrase in enumerate(sorted_phrases):
        token = f"__VIET_{i}__"
        token_map[token] = {"text": phrase, "is_viet": True}
        clean_text = clean_text.replace(phrase, f" {token} ")
    
    # Split the text into words, preserving punctuation as separate tokens
    # This regex splits on whitespace but keeps punctuation as separate tokens
    word_tokens = []
    for part in re.findall(r'\S+|\s+', clean_text):
        if part.strip():
            # Check if it's a Vietnamese tag placeholder
            if part.strip() in viet_tag_map:
                word_tokens.append(part.strip())
            # Check if it's a Vietnamese token
            elif part.startswith("__VIET_") and part.endswith("__"):
                word_tokens.append(part)
            else:
                # Check if the token contains punctuation
                punctuation_split = re.findall(r'[a-zA-Z0-9\'-]+|[.,!?;:]', part)
                if len(punctuation_split) > 1:
                    word_tokens.extend(punctuation_split)
                else:
                    word_tokens.append(part)
    
    # Process tokens into words
    words = []
    for token in word_tokens:
        # Check if it's a Vietnamese tag placeholder
        if token in viet_tag_map:
            # It's a Vietnamese tag
            viet_info = viet_tag_map[token]
            words.append({
                "text": viet_info["full_tag"],
                "viet_words": [viet_info["text"]],
                "is_punctuation": False
            })
        elif token.startswith("__VIET_") and token.endswith("__"):
            # It's a Vietnamese phrase
            phrase_info = token_map[token]
            words.append({
                "text": phrase_info["text"],
                "viet_words": [phrase_info["text"]],
                "is_punctuation": False
            })
        elif re.match(r'[.,!?;:]', token):
            # It's punctuation
            words.append({
                "text": token,
                "viet_words": [],
                "is_punctuation": True
            })
        else:
            # It's a regular word
            words.append({
                "text": token,
                "viet_words": [],
                "is_punctuation": False
            })
    
    return words

def estimate_timestamps(audio_file, dialogue_data):
    """
    Estimate timestamps for each line in the dialogue, breaking into individual words.
    This approach distributes the audio duration proportionally based on text length
    and then further breaks down each line into individual words for more precise timing.
    """
    if not dialogue_data or "english_dialogue" not in dialogue_data:
        return None
    
    # Extract Vietnamese vocabulary from the dialogue
    vietnamese_vocab = set()
    if "topic_word" in dialogue_data and dialogue_data["topic_word"]:
        vietnamese_vocab.add(dialogue_data["topic_word"].lower())
    
    if "common_words" in dialogue_data and dialogue_data["common_words"]:
        for word_data in dialogue_data["common_words"]:
            if "word" in word_data and word_data["word"]:
                vietnamese_vocab.add(word_data["word"].lower())
    
    # Get the total duration of the audio file
    total_duration = get_audio_duration(audio_file)
    
    # Calculate the total text length
    total_text_length = sum(len(line["text"]) for line in dialogue_data["english_dialogue"])
    
    # Calculate the duration per character
    duration_per_char = total_duration / total_text_length if total_text_length > 0 else 0
    
    # Calculate timestamps for each line and break into words
    timestamps = []
    current_time = 0
    
    for i, line in enumerate(dialogue_data["english_dialogue"]):
        # Calculate the estimated duration of this line
        line_length = len(line["text"])
        line_duration = line_length * duration_per_char
        
        # Add a small pause between speakers (50ms as defined in generate_audio.py)
        if i > 0:
            current_time += 0.05  # 50ms pause
        
        # Split the line into individual words
        words = split_text_into_words(line["text"], vietnamese_vocab)
        
        # Calculate duration for each word proportionally
        # Punctuation gets a very small duration
        word_durations = []
        total_word_length = sum(3 if word["is_punctuation"] else len(word["text"]) for word in words)
        
        for word in words:
            if word["is_punctuation"]:
                # Punctuation gets a fixed small duration (100ms)
                word_duration = 0.1
            else:
                # Regular words get duration proportional to their length
                word_length = len(word["text"])
                word_duration = (word_length / total_word_length) * line_duration
                # Ensure minimum duration for very short words
                word_duration = max(word_duration, 0.2)
            
            word_durations.append(word_duration)
        
        # Adjust durations to match the total line duration
        total_word_duration = sum(word_durations)
        if total_word_duration > 0:
            adjustment_factor = line_duration / total_word_duration
            word_durations = [duration * adjustment_factor for duration in word_durations]
        
        # Create timestamp entries for each word
        word_start_time = current_time
        
        # Group words into small phrases (1-3 words) for better readability
        phrase_words = []
        phrase_start_time = word_start_time
        phrase_end_time = word_start_time
        phrase_viet_words = []
        
        for j, (word, word_duration) in enumerate(zip(words, word_durations)):
            # Update the end time for this word
            word_end_time = word_start_time + word_duration
            
            # Add word to current phrase
            phrase_words.append(word["text"])
            phrase_end_time = word_end_time
            phrase_viet_words.extend(word["viet_words"])
            
            # Check if we should end the current phrase
            end_phrase = False
            
            # End phrase on punctuation
            if word["is_punctuation"] and word["text"] in ['.', '!', '?', ';']:
                end_phrase = True
            
            # End phrase after 3 words or at the end of the line
            if len(phrase_words) >= 3 or j == len(words) - 1:
                end_phrase = True
            
            if end_phrase and phrase_words:
                # Create a timestamp entry for this phrase
                phrase_text = ' '.join(phrase_words).strip()
                
                # Skip empty phrases
                if phrase_text:
                    timestamp = {
                        "speaker": line["speaker"],
                        "text": phrase_text,
                        "viet_words": list(set(phrase_viet_words)),  # Remove duplicates
                        "start_time": round(phrase_start_time, 2),
                        "end_time": round(phrase_end_time, 2)
                    }
                    timestamps.append(timestamp)
                
                # Reset for next phrase
                phrase_words = []
                phrase_start_time = word_end_time
                phrase_viet_words = []
            
            # Update start time for the next word
            word_start_time = word_end_time
        
        # Update current time for the next line
        current_time += line_duration
    
    return timestamps

def generate_timestamp_json(audio_file):
    """Generate a JSON file with dialogue timestamps for the given audio file."""
    # Extract the dialogue ID from the filename
    filename = os.path.basename(audio_file)
    match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
    
    if not match:
        print(f"Could not extract dialogue ID from filename: {filename}")
        return None
    
    dialogue_id = match.group(1)
    
    # Find the corresponding dialogue file
    dialogue_data = find_dialogue_file(dialogue_id)
    
    if not dialogue_data:
        print(f"Could not find dialogue file for ID: {dialogue_id}")
        return None
    
    # Estimate timestamps
    timestamps = estimate_timestamps(audio_file, dialogue_data)
    
    if not timestamps:
        print(f"Could not estimate timestamps for: {filename}")
        return None
    
    # Create the output JSON data
    output_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": timestamps
    }
    
    # Create the output filename (without _elevenlabs_slow)
    output_filename = f"dialogue_{dialogue_id}.json"
    output_path = os.path.join(config.AUDIO_PATH, output_filename)
    
    # Write the JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Generated timestamp JSON file: {output_path}")
    return output_path

def main():
    """Main function to process all audio files."""
    # Get all audio files
    audio_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*_elevenlabs_slow.mp3"))
    
    if not audio_files:
        print("No audio files found.")
        return
    
    print(f"Found {len(audio_files)} audio files to process.")
    
    # Process each audio file
    for audio_file in audio_files:
        print(f"Processing: {audio_file}")
        generate_timestamp_json(audio_file)

if __name__ == "__main__":
    main() 