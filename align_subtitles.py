#!/usr/bin/env python3
"""
Script to align auto-generated subtitles with original dialogue text using Anthropic's API.
This script sends both the auto-generated subtitles and the original dialogue to Anthropic
and asks it to adjust the subtitles to match the original dialogue while preserving timing.
"""

import os
import json
import glob
import re
import argparse
import shutil
import config
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Anthropic API key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")

def load_json_file(file_path):
    """
    Load a JSON file.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        The loaded JSON data, or None if the file doesn't exist or is invalid
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        print(f"Invalid JSON file: {file_path}")
        return None
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        return None

def find_dialogue_file(dialogue_id):
    """
    Find the original dialogue file for a given dialogue ID.
    
    Args:
        dialogue_id: The dialogue ID to find
    
    Returns:
        The dialogue data as a dictionary, or None if not found
    """
    dialogue_files = glob.glob("data/dialogues/*.json")
    for file_path in dialogue_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                dialogue_data = json.load(f)
                if dialogue_data["id"] == dialogue_id:
                    return dialogue_data
        except:
            continue
    return None

def format_dialogue_for_anthropic(dialogue_data):
    """
    Format the original dialogue data for sending to Anthropic.
    
    Args:
        dialogue_data: The original dialogue data
    
    Returns:
        Formatted dialogue text
    """
    formatted_text = "Original Dialogue:\n\n"
    
    for entry in dialogue_data["english_dialogue"]:
        speaker = entry["speaker"]
        text = entry["text"]
        formatted_text += f"{speaker}: {text}\n"
    
    return formatted_text

def format_auto_subtitles_for_anthropic(auto_data):
    """
    Format the auto-generated subtitles for sending to Anthropic.
    
    Args:
        auto_data: The auto-generated subtitle data
    
    Returns:
        Formatted subtitle text with timestamps
    """
    formatted_text = "Auto-Generated Subtitles (with timestamps):\n\n"
    
    # Sort by start time
    sorted_dialogue = sorted(auto_data["dialogue"], key=lambda x: x["start_time"])
    
    for entry in sorted_dialogue:
        speaker = entry["speaker"]
        text = entry["text"]
        start_time = entry["start_time"]
        end_time = entry["end_time"]
        formatted_text += f"{speaker} [{start_time:.2f}-{end_time:.2f}]: {text}\n"
    
    return formatted_text

def call_anthropic_api(original_dialogue, auto_subtitles, dialogue_id, topic_word):
    """
    Call Anthropic's API to align the subtitles.
    
    Args:
        original_dialogue: Formatted original dialogue text
        auto_subtitles: Formatted auto-generated subtitles
        dialogue_id: The dialogue ID
        topic_word: The Vietnamese topic word
    
    Returns:
        Anthropic's response
    """
    prompt = f"""
I need you to align auto-generated subtitles with the original dialogue text for a language learning video.

The video is teaching Vietnamese, and the topic word is "{topic_word}".

Original dialogue: {original_dialogue}

Auto-generated subtitles: {auto_subtitles}

Task: Create a new JSON array of dialogue entries that:
1. Uses the exact text from the original dialogue
2. Keeps the timestamps from the auto-generated subtitles
3. IMPORTANT: Split ALL sentences into VERY small phrases of 2-3 words each ideally, though 1 and 4 are allowed. No phrase should contain more than 4 words unless it's a single Vietnamese word with its tags. Also respect sentences stops and pauses.
4. Respect periods and commas in the original dialogue by breaking them into smaller segments.
5. Ensures Vietnamese words are properly highlighted with <vietnamese>word</vietnamese> tags

Format each entry as:
{{
  "speaker": "Speaker Name",
  "text": "Text with <vietnamese>Vietnamese words</vietnamese> highlighted",
  "start_time": start_time_in_seconds,
  "end_time": end_time_in_seconds
}}

Return ONLY the JSON array without any explanation or additional text.
"""

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    
    data = {
        "model": "claude-3-7-sonnet-20250219",
        "max_tokens": 4000,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except Exception as e:
        print(f"Error calling Anthropic API: {str(e)}")
        return None

def extend_subtitle_durations(aligned_dialogue, extension=0.1):
    """
    Extend the end time of each subtitle by a small amount to make them linger longer.
    
    Args:
        aligned_dialogue: List of dialogue entries with timestamps
        extension: Amount of time in seconds to extend each subtitle (default: 0.1)
    
    Returns:
        The dialogue entries with extended end times
    """
    # Sort the dialogue by start time to ensure proper ordering
    sorted_dialogue = sorted(aligned_dialogue, key=lambda x: x["start_time"])
    
    # Extend each subtitle's end time, but don't overlap with the next subtitle
    for i in range(len(sorted_dialogue) - 1):
        current_end = sorted_dialogue[i]["end_time"]
        next_start = sorted_dialogue[i + 1]["start_time"]
        
        # Calculate the maximum possible extension without overlapping
        max_extension = next_start - current_end - 0.01  # Leave a small gap
        
        # Apply the extension, but don't exceed the maximum
        if max_extension > 0:
            actual_extension = min(extension, max_extension)
            sorted_dialogue[i]["end_time"] += actual_extension
    
    # For the last subtitle, just add the extension
    if sorted_dialogue:
        sorted_dialogue[-1]["end_time"] += extension
    
    return sorted_dialogue

def verify_phrase_lengths(aligned_dialogue, max_words=3):
    """
    Verify that phrases are limited to the specified maximum number of words.
    If a phrase exceeds the limit, split it into smaller phrases.
    
    Args:
        aligned_dialogue: List of dialogue entries with timestamps
        max_words: Maximum number of words per phrase (default: 3)
    
    Returns:
        The dialogue entries with phrases split to meet the word limit
    """
    verified_dialogue = []
    
    for entry in aligned_dialogue:
        text = entry["text"]
        
        # Count words excluding Vietnamese tags
        text_without_tags = re.sub(r'<vietnamese>[^<]+</vietnamese>', 'VIET_WORD', text)
        words = text_without_tags.split()
        
        # If the phrase is within the limit, keep it as is
        if len(words) <= max_words:
            verified_dialogue.append(entry)
            continue
        
        # Otherwise, split the phrase into smaller phrases
        print(f"Splitting phrase with {len(words)} words: '{text}'")
        
        # Extract Vietnamese tags and replace with placeholders
        viet_tags = re.findall(r'<vietnamese>([^<]+)</vietnamese>', text)
        text_with_placeholders = text
        tag_map = {}
        
        for i, viet_content in enumerate(viet_tags):
            placeholder = f"__VIET_TAG_{i}__"
            tag_map[placeholder] = f"<vietnamese>{viet_content}</vietnamese>"
            text_with_placeholders = text_with_placeholders.replace(
                f"<vietnamese>{viet_content}</vietnamese>", 
                placeholder
            )
        
        # Split the text into words
        words = text_with_placeholders.split()
        
        # Calculate the duration per word
        duration = entry["end_time"] - entry["start_time"]
        duration_per_word = duration / len(words)
        
        # Group words into small phrases
        current_phrase = []
        current_count = 0
        start_time = entry["start_time"]
        
        for i, word in enumerate(words):
            is_viet_placeholder = word.startswith("__VIET_TAG_")
            
            # Add the word to the current phrase
            current_phrase.append(word)
            
            # Only count non-Vietnamese placeholder words
            if not is_viet_placeholder:
                current_count += 1
            
            # If we've reached the limit or this is the last word, create a new phrase
            if current_count == max_words or i == len(words) - 1:
                if current_phrase:
                    # Calculate the end time for this phrase
                    phrase_end_time = start_time + (len(current_phrase) * duration_per_word)
                    
                    # Join the current phrase and restore Vietnamese tags
                    phrase_text = ' '.join(current_phrase)
                    for placeholder, tag in tag_map.items():
                        phrase_text = phrase_text.replace(placeholder, tag)
                    
                    # Create a new entry
                    new_entry = {
                        "speaker": entry["speaker"],
                        "text": phrase_text,
                        "start_time": start_time,
                        "end_time": phrase_end_time
                    }
                    
                    verified_dialogue.append(new_entry)
                    
                    # Update the start time for the next phrase
                    start_time = phrase_end_time
                    
                    # Reset the current phrase
                    current_phrase = []
                    current_count = 0
    
    # Sort the dialogue by start time
    verified_dialogue.sort(key=lambda x: x["start_time"])
    
    return verified_dialogue

def align_subtitles(auto_json_path, output_path=None, replace_original=True):
    """
    Align auto-generated subtitles with original dialogue text.
    
    Args:
        auto_json_path: Path to the auto-generated subtitle JSON file
        output_path: Path to save the aligned JSON file (optional)
        replace_original: If True, replace the original file with the aligned one
    
    Returns:
        Path to the aligned JSON file, or None if failed
    """
    # Load the auto-generated JSON file
    auto_data = load_json_file(auto_json_path)
    if not auto_data:
        return None
    
    # Extract the dialogue ID
    dialogue_id = auto_data["id"]
    
    # Find the original dialogue file
    dialogue_data = find_dialogue_file(dialogue_id)
    if not dialogue_data:
        print(f"Could not find original dialogue file for ID: {dialogue_id}")
        return None
    
    # Format the data for Anthropic
    original_dialogue = format_dialogue_for_anthropic(dialogue_data)
    auto_subtitles = format_auto_subtitles_for_anthropic(auto_data)
    topic_word = dialogue_data.get("topic_word", "")
    
    # Call Anthropic's API
    print(f"Calling Anthropic API to align subtitles for dialogue {dialogue_id}...")
    aligned_dialogue_json = call_anthropic_api(original_dialogue, auto_subtitles, dialogue_id, topic_word)
    
    if not aligned_dialogue_json:
        print("Failed to get a response from Anthropic API")
        return None
    
    # Parse the response
    try:
        # The response should be a JSON array, but it might be wrapped in ```json ... ``` or have other text
        # Extract just the JSON part
        json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', aligned_dialogue_json)
        if json_match:
            aligned_dialogue = json.loads(json_match.group(1))
        else:
            # Try to parse the whole response as JSON
            aligned_dialogue = json.loads(aligned_dialogue_json)
    except json.JSONDecodeError as e:
        print(f"Error parsing Anthropic response as JSON: {str(e)}")
        print("Response:", aligned_dialogue_json[:500] + "..." if len(aligned_dialogue_json) > 500 else aligned_dialogue_json)
        return None
    
    # Verify that phrases are limited to 2-3 words
    print("Verifying phrase lengths...")
    aligned_dialogue = verify_phrase_lengths(aligned_dialogue, max_words=3)
    
    # Extend subtitle durations to make them linger longer
    aligned_dialogue = extend_subtitle_durations(aligned_dialogue)
    
    # Create the aligned data
    aligned_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": aligned_dialogue
    }
    
    # Load the original timestamp file if it exists
    original_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
    
    # Set the output path if not provided
    if not output_path:
        output_path = original_json_path.replace('.json', '_aligned.json')
    
    # Write the aligned JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(aligned_data, f, ensure_ascii=False, indent=2)
    
    print(f"Aligned subtitle JSON file saved to: {output_path}")
    
    # If replace_original is True, copy the aligned file over the original
    if replace_original:
        # Create a backup of the original file
        if os.path.exists(original_json_path):
            backup_path = original_json_path.replace('.json', '_original.json')
            shutil.copy2(original_json_path, backup_path)
            print(f"Original file backed up to: {backup_path}")
        
        # Copy the aligned file over the original
        shutil.copy2(output_path, original_json_path)
        print(f"Aligned file copied to original location: {original_json_path}")
    
    return output_path

def main():
    """Main function to align subtitles."""
    parser = argparse.ArgumentParser(description="Align auto-generated subtitles with original dialogue text")
    parser.add_argument("--dialogue-id", type=str, help="Dialogue ID to process")
    parser.add_argument("--no-replace", action="store_true", help="Don't replace the original file with the aligned one")
    args = parser.parse_args()
    
    # Determine whether to replace the original file
    replace_original = not args.no_replace
    
    # Process a specific dialogue if provided
    if args.dialogue_id:
        auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{args.dialogue_id}_auto.json")
        
        if not os.path.exists(auto_json_path):
            print(f"Auto-generated JSON file not found: {auto_json_path}")
            return
        
        align_subtitles(auto_json_path, replace_original=replace_original)
        return
    
    # Otherwise, process all dialogues
    auto_json_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*_auto.json"))
    
    if not auto_json_files:
        print("No auto-generated JSON files found.")
        return
    
    print(f"Found {len(auto_json_files)} auto-generated JSON files to process.")
    
    # Process each file
    for auto_json_path in auto_json_files:
        # Extract the dialogue ID
        match = re.search(r'dialogue_([a-f0-9]+)_auto\.json', os.path.basename(auto_json_path))
        if not match:
            print(f"Could not extract dialogue ID from filename: {auto_json_path}")
            continue
        
        dialogue_id = match.group(1)
        print(f"Processing dialogue {dialogue_id}...")
        align_subtitles(auto_json_path, replace_original=replace_original)

if __name__ == "__main__":
    main() 