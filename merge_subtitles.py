#!/usr/bin/env python3
"""
Script to merge auto-generated subtitles with original dialogue text.
This script uses the auto-generated subtitles as a baseline (for accurate timestamps)
and replaces the text with the correct text from the original dialogue files.
"""

import os
import json
import glob
import re
import argparse
import shutil
import config
from difflib import SequenceMatcher

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

def clean_text_for_comparison(text):
    """
    Clean text for comparison by removing punctuation, extra spaces, and converting to lowercase.
    
    Args:
        text: The text to clean
    
    Returns:
        The cleaned text
    """
    # Remove HTML-like tags (e.g., <vietnamese>...</vietnamese>)
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def extract_vietnamese_words(text, dialogue_data):
    """
    Extract Vietnamese words from text based on the dialogue data.
    
    Args:
        text: The text to analyze
        dialogue_data: The dialogue data containing Vietnamese words
    
    Returns:
        List of Vietnamese words found in the text
    """
    viet_words = []
    
    # Get Vietnamese words from the dialogue data
    topic_word = dialogue_data.get("topic_word", "")
    if topic_word:
        viet_words.append(topic_word)
    
    common_words = dialogue_data.get("common_words", [])
    for word_data in common_words:
        if "word" in word_data:
            viet_words.append(word_data["word"])
    
    # Find Vietnamese words in the text
    found_words = []
    for word in viet_words:
        if word.lower() in text.lower():
            found_words.append(word)
    
    return found_words

def get_speaker_segments(auto_data):
    """
    Get segments of continuous speech by each speaker from auto data.
    
    Args:
        auto_data: The auto-generated subtitle data
    
    Returns:
        Dictionary mapping speakers to lists of (start_time, end_time) tuples
    """
    speaker_segments = {}
    
    # Sort auto phrases by start time
    sorted_phrases = sorted(auto_data["dialogue"], key=lambda x: x["start_time"])
    
    current_speaker = None
    segment_start = None
    segment_end = None
    
    for phrase in sorted_phrases:
        speaker = phrase["speaker"]
        start_time = phrase["start_time"]
        end_time = phrase["end_time"]
        
        # Initialize speaker segments if needed
        if speaker not in speaker_segments:
            speaker_segments[speaker] = []
        
        # If this is a new speaker or there's a gap, start a new segment
        if speaker != current_speaker or start_time > segment_end + 1.0:
            # Save the previous segment if it exists
            if current_speaker is not None and segment_start is not None:
                speaker_segments[current_speaker].append((segment_start, segment_end))
            
            # Start a new segment
            segment_start = start_time
            segment_end = end_time
            current_speaker = speaker
        else:
            # Extend the current segment
            segment_end = max(segment_end, end_time)
    
    # Add the last segment
    if current_speaker is not None and segment_start is not None:
        speaker_segments[current_speaker].append((segment_start, segment_end))
    
    return speaker_segments

def merge_subtitles(auto_json_path, output_path=None, replace_original=True):
    """
    Merge auto-generated subtitles with original dialogue text.
    
    Args:
        auto_json_path: Path to the auto-generated subtitle JSON file
        output_path: Path to save the merged JSON file (optional)
        replace_original: If True, replace the original file with the merged one
    
    Returns:
        Path to the merged JSON file, or None if failed
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
    
    # Load the original timestamp file if it exists
    original_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
    original_timestamps = load_json_file(original_json_path)
    
    # Get the original dialogue
    original_dialogue = dialogue_data["english_dialogue"]
    
    # Get speaker segments from auto data
    speaker_segments = get_speaker_segments(auto_data)
    
    # Group original phrases by speaker
    phrases_by_speaker = {}
    for phrase in original_dialogue:
        speaker = phrase["speaker"]
        if speaker not in phrases_by_speaker:
            phrases_by_speaker[speaker] = []
        phrases_by_speaker[speaker].append(phrase)
    
    # Create a new dialogue with the original text but auto timestamps
    merged_dialogue = []
    
    # For each speaker, distribute their segments across their phrases
    for speaker, phrases in phrases_by_speaker.items():
        if speaker not in speaker_segments:
            print(f"Warning: No auto segments found for speaker {speaker}")
            continue
        
        segments = speaker_segments[speaker]
        
        # Calculate total segment duration for this speaker
        total_segment_duration = sum(end - start for start, end in segments)
        
        # Calculate average duration per phrase
        avg_duration_per_phrase = total_segment_duration / len(phrases)
        
        # Distribute phrases across segments
        phrase_index = 0
        
        for segment_start, segment_end in segments:
            segment_duration = segment_end - segment_start
            
            # Calculate how many phrases fit in this segment
            phrases_in_segment = max(1, round(segment_duration / avg_duration_per_phrase))
            
            # Ensure we don't exceed the number of phrases
            phrases_in_segment = min(phrases_in_segment, len(phrases) - phrase_index)
            
            if phrases_in_segment <= 0:
                continue
            
            # Calculate duration per phrase in this segment
            duration_per_phrase = segment_duration / phrases_in_segment
            
            # Distribute phrases in this segment
            current_time = segment_start
            
            for i in range(phrases_in_segment):
                if phrase_index >= len(phrases):
                    break
                
                phrase = phrases[phrase_index]
                
                # Create a merged phrase
                merged_phrase = {
                    "speaker": speaker,
                    "text": phrase["text"],
                    "start_time": current_time,
                    "end_time": current_time + duration_per_phrase,
                    "viet_words": extract_vietnamese_words(phrase["text"], dialogue_data)
                }
                
                merged_dialogue.append(merged_phrase)
                
                # Update the current time and phrase index
                current_time += duration_per_phrase
                phrase_index += 1
        
        # If we have remaining phrases, add them at the end
        if phrase_index < len(phrases):
            print(f"Warning: {len(phrases) - phrase_index} phrases for speaker {speaker} could not be placed in segments")
            
            # Use the last segment's end time as a starting point
            if segments:
                current_time = segments[-1][1] + 0.1
            else:
                # Find the last end time of any speaker
                last_end_time = 0
                for phrase in merged_dialogue:
                    if phrase["end_time"] > last_end_time:
                        last_end_time = phrase["end_time"]
                current_time = last_end_time + 0.1
            
            # Add remaining phrases
            for i in range(phrase_index, len(phrases)):
                phrase = phrases[i]
                
                # Use a default duration
                duration = 2.0
                
                # Create a merged phrase
                merged_phrase = {
                    "speaker": speaker,
                    "text": phrase["text"],
                    "start_time": current_time,
                    "end_time": current_time + duration,
                    "viet_words": extract_vietnamese_words(phrase["text"], dialogue_data)
                }
                
                merged_dialogue.append(merged_phrase)
                
                # Update the current time
                current_time += duration
    
    # Sort the merged dialogue by start time
    merged_dialogue.sort(key=lambda x: x["start_time"])
    
    # Ensure phrases don't overlap
    for i in range(1, len(merged_dialogue)):
        if merged_dialogue[i]["start_time"] < merged_dialogue[i-1]["end_time"]:
            # Adjust the start time of the current phrase
            merged_dialogue[i]["start_time"] = merged_dialogue[i-1]["end_time"] + 0.05
            
            # Ensure the end time is after the start time
            if merged_dialogue[i]["end_time"] <= merged_dialogue[i]["start_time"]:
                merged_dialogue[i]["end_time"] = merged_dialogue[i]["start_time"] + 1.0
    
    # Create the merged data
    merged_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": merged_dialogue
    }
    
    # Set the output path if not provided
    if not output_path:
        output_path = original_json_path.replace('.json', '_merged.json')
    
    # Write the merged JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)
    
    print(f"Merged subtitle JSON file saved to: {output_path}")
    
    # If replace_original is True, copy the merged file over the original
    if replace_original:
        # Create a backup of the original file
        if os.path.exists(original_json_path):
            backup_path = original_json_path.replace('.json', '_original.json')
            shutil.copy2(original_json_path, backup_path)
            print(f"Original file backed up to: {backup_path}")
        
        # Copy the merged file over the original
        shutil.copy2(output_path, original_json_path)
        print(f"Merged file copied to original location: {original_json_path}")
    
    return output_path

def main():
    """Main function to merge subtitles."""
    parser = argparse.ArgumentParser(description="Merge auto-generated subtitles with original dialogue text")
    parser.add_argument("--dialogue-id", type=str, help="Dialogue ID to process")
    parser.add_argument("--no-replace", action="store_true", help="Don't replace the original file with the merged one")
    args = parser.parse_args()
    
    # Determine whether to replace the original file
    replace_original = not args.no_replace
    
    # Process a specific dialogue if provided
    if args.dialogue_id:
        auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{args.dialogue_id}_auto.json")
        
        if not os.path.exists(auto_json_path):
            print(f"Auto-generated JSON file not found: {auto_json_path}")
            return
        
        merge_subtitles(auto_json_path, replace_original=replace_original)
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
        merge_subtitles(auto_json_path, replace_original=replace_original)

if __name__ == "__main__":
    main() 