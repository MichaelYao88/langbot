#!/usr/bin/env python3
"""
Script to adjust the timings in the generated timestamp JSON files based on the auto-generated timestamps.
This script compares the original timestamp JSON files with the auto-generated ones and adjusts the timings
to match the auto-generated timestamps for the starting and ending words of each phrase.
By default, the adjusted file will replace the original file, making it the default version.
"""

import os
import json
import glob
import re
import argparse
import config
import shutil
from pathlib import Path

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

def find_word_sequence_in_auto_timestamps(words, auto_word_timestamps, position=None):
    """
    Find a sequence of words in the auto-generated word timestamps.
    
    Args:
        words: List of words to find in sequence
        auto_word_timestamps: List of auto-generated word timestamps
        position: Approximate position in the audio (in seconds)
    
    Returns:
        Tuple of (start_timestamp, end_timestamp) for the sequence, or (None, None) if not found
    """
    if not words:
        return None, None
    
    # Clean the words for comparison
    clean_words = [re.sub(r'[^\w\s]', '', word.lower()) for word in words]
    
    # If we have position information, try to find sequences close to that position first
    candidates = []
    
    # Try to find the sequence in the auto timestamps
    for i in range(len(auto_word_timestamps) - len(clean_words) + 1):
        match = True
        for j, clean_word in enumerate(clean_words):
            auto_word = auto_word_timestamps[i + j]["word"].lower()
            # Check for exact match or if one contains the other
            if not (auto_word == clean_word or 
                   clean_word in auto_word or 
                   auto_word in clean_word):
                match = False
                break
        
        if match:
            start_timestamp = auto_word_timestamps[i]
            end_timestamp = auto_word_timestamps[i + len(clean_words) - 1]
            
            # If we have position information, calculate how close this sequence is
            if position is not None:
                sequence_midpoint = (start_timestamp["start"] + end_timestamp["end"]) / 2
                time_diff = abs(sequence_midpoint - position)
                candidates.append((start_timestamp, end_timestamp, time_diff))
            else:
                return start_timestamp, end_timestamp
    
    # If we have candidates with position information, return the closest one
    if candidates and position is not None:
        candidates.sort(key=lambda x: x[2])  # Sort by time difference
        return candidates[0][0], candidates[0][1]
    
    # If no sequence match found, fall back to finding individual words
    first_word = clean_words[0]
    last_word = clean_words[-1]
    
    first_timestamp = None
    last_timestamp = None
    
    # Try to find the first word
    for timestamp in auto_word_timestamps:
        auto_word = timestamp["word"].lower()
        if auto_word == first_word or first_word in auto_word or auto_word in first_word:
            first_timestamp = timestamp
            break
    
    # Try to find the last word
    for timestamp in reversed(auto_word_timestamps):
        auto_word = timestamp["word"].lower()
        if auto_word == last_word or last_word in auto_word or auto_word in last_word:
            last_timestamp = timestamp
            break
    
    return first_timestamp, last_timestamp

def adjust_phrase_timestamps(phrase, auto_word_timestamps, all_phrases=None, phrase_index=None):
    """
    Adjust the timestamps for a phrase based on auto-generated word timestamps.
    
    Args:
        phrase: The phrase to adjust
        auto_word_timestamps: List of auto-generated word timestamps
        all_phrases: List of all phrases (for context)
        phrase_index: Index of the current phrase in all_phrases
    
    Returns:
        The adjusted phrase
    """
    # Create a copy of the phrase to avoid modifying the original text
    adjusted_phrase = phrase.copy()
    
    # Extract words from the phrase
    words = re.findall(r'\b\w+\b', phrase["text"])
    if not words:
        return adjusted_phrase
    
    # Get approximate position based on original timestamps
    position_midpoint = (phrase["start_time"] + phrase["end_time"]) / 2
    
    # Try different approaches for finding the phrase in the auto timestamps
    
    # 1. Try with the full sequence of words
    start_timestamp, end_timestamp = find_word_sequence_in_auto_timestamps(
        words, 
        auto_word_timestamps, 
        position=position_midpoint
    )
    
    # 2. If that fails, try with the first few words and last few words
    if not start_timestamp or not end_timestamp:
        # Try with first 2-3 words
        first_words = words[:min(3, len(words))]
        start_timestamp, _ = find_word_sequence_in_auto_timestamps(
            first_words, 
            auto_word_timestamps, 
            position=phrase["start_time"]
        )
        
        # Try with last 2-3 words
        last_words = words[-min(3, len(words)):]
        _, end_timestamp = find_word_sequence_in_auto_timestamps(
            last_words, 
            auto_word_timestamps, 
            position=phrase["end_time"]
        )
    
    # 3. If we still don't have both timestamps, try with context from surrounding phrases
    if (not start_timestamp or not end_timestamp) and all_phrases and phrase_index is not None:
        # Add words from previous phrase
        if phrase_index > 0 and not start_timestamp:
            prev_words = re.findall(r'\b\w+\b', all_phrases[phrase_index - 1]["text"])
            if prev_words:
                # Try to find the transition between phrases
                transition_words = prev_words[-min(2, len(prev_words)):] + words[:min(2, len(words))]
                start_timestamp, _ = find_word_sequence_in_auto_timestamps(
                    transition_words, 
                    auto_word_timestamps
                )
                
                # If we found a match, make sure we only use the timestamp for our phrase's words
                if start_timestamp:
                    # Find where our phrase's words start in the transition sequence
                    for i, word in enumerate(auto_word_timestamps):
                        if word == start_timestamp:
                            # Skip past the previous phrase's words
                            offset = min(2, len(prev_words))
                            if i + offset < len(auto_word_timestamps):
                                start_timestamp = auto_word_timestamps[i + offset]
                            break
        
        # Add words from next phrase
        if phrase_index < len(all_phrases) - 1 and not end_timestamp:
            next_words = re.findall(r'\b\w+\b', all_phrases[phrase_index + 1]["text"])
            if next_words:
                # Try to find the transition between phrases
                transition_words = words[-min(2, len(words)):] + next_words[:min(2, len(next_words))]
                _, end_timestamp = find_word_sequence_in_auto_timestamps(
                    transition_words, 
                    auto_word_timestamps
                )
                
                # If we found a match, make sure we only use the timestamp for our phrase's words
                if end_timestamp:
                    # Find where the next phrase's words start in the transition sequence
                    for i, word in enumerate(auto_word_timestamps):
                        if word == end_timestamp:
                            # Don't include the next phrase's words
                            offset = min(2, len(words))
                            if i - offset >= 0:
                                end_timestamp = auto_word_timestamps[i - offset]
                            break
    
    # Adjust the start time if found
    if start_timestamp:
        adjusted_phrase["start_time"] = round(start_timestamp["start"], 2)
    
    # Adjust the end time if found
    if end_timestamp:
        adjusted_phrase["end_time"] = round(end_timestamp["end"], 2)
    
    # Ensure we're not modifying the original text
    adjusted_phrase["text"] = phrase["text"]
    
    return adjusted_phrase

def validate_and_fix_timestamps(phrases):
    """
    Validate and fix timestamps to ensure they are logical.
    
    Args:
        phrases: List of phrases with timestamps
    
    Returns:
        List of phrases with validated and fixed timestamps
    """
    # Sort phrases by start time
    phrases.sort(key=lambda x: x["start_time"])
    
    # Check and fix each phrase
    for i, phrase in enumerate(phrases):
        # Ensure start_time is less than end_time
        if phrase["start_time"] >= phrase["end_time"]:
            # If this is the first phrase, set start_time to 0
            if i == 0:
                phrase["start_time"] = 0.0
            else:
                # Otherwise, set start_time to the end_time of the previous phrase
                phrase["start_time"] = phrases[i-1]["end_time"]
            
            # Ensure there's at least a small gap between start and end
            if phrase["start_time"] >= phrase["end_time"]:
                phrase["end_time"] = phrase["start_time"] + 0.5
        
        # Check for overlaps with the next phrase
        if i < len(phrases) - 1:
            next_phrase = phrases[i+1]
            if phrase["end_time"] > next_phrase["start_time"]:
                # If there's an overlap, adjust the end time of the current phrase
                # to match the start time of the next phrase
                phrase["end_time"] = next_phrase["start_time"]
    
    return phrases

def adjust_timestamps(original_json_path, auto_json_path, output_path=None, replace_original=True):
    """
    Adjust the timings in the original timestamp JSON file based on the auto-generated timestamps.
    
    Args:
        original_json_path: Path to the original timestamp JSON file
        auto_json_path: Path to the auto-generated timestamp JSON file
        output_path: Path to save the adjusted JSON file (optional)
        replace_original: If True, replace the original file with the adjusted one
    
    Returns:
        Path to the adjusted JSON file, or None if failed
    """
    # Load the original and auto-generated JSON files
    original_data = load_json_file(original_json_path)
    auto_data = load_json_file(auto_json_path)
    
    if not original_data or not auto_data:
        return None
    
    # Load the raw word timestamps
    dialogue_id = original_data["id"]
    raw_word_json_path = os.path.join(config.AUDIO_PATH, f"word_timestamps_{dialogue_id}.json")
    auto_word_timestamps = load_json_file(raw_word_json_path)
    
    if not auto_word_timestamps:
        print(f"Raw word timestamps not found: {raw_word_json_path}")
        return None
    
    # Create a copy of the original data
    adjusted_data = original_data.copy()
    
    # Adjust the timestamps for each phrase
    for i, phrase in enumerate(adjusted_data["dialogue"]):
        adjusted_data["dialogue"][i] = adjust_phrase_timestamps(
            phrase, 
            auto_word_timestamps,
            all_phrases=adjusted_data["dialogue"],
            phrase_index=i
        )
        
        # Double-check that we haven't modified the text
        if adjusted_data["dialogue"][i]["text"] != original_data["dialogue"][i]["text"]:
            print(f"Warning: Text was modified for phrase {i}. Restoring original text.")
            adjusted_data["dialogue"][i]["text"] = original_data["dialogue"][i]["text"]
    
    # Validate and fix the timestamps
    adjusted_data["dialogue"] = validate_and_fix_timestamps(adjusted_data["dialogue"])
    
    # Set the output path if not provided
    if not output_path:
        output_path = original_json_path.replace('.json', '_adjusted.json')
    
    # Write the adjusted JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(adjusted_data, f, ensure_ascii=False, indent=2)
    
    print(f"Adjusted timestamp JSON file saved to: {output_path}")
    
    # If replace_original is True, copy the adjusted file over the original
    if replace_original:
        # Create a backup of the original file
        backup_path = original_json_path.replace('.json', '_original.json')
        shutil.copy2(original_json_path, backup_path)
        print(f"Original file backed up to: {backup_path}")
        
        # Copy the adjusted file over the original
        shutil.copy2(output_path, original_json_path)
        print(f"Adjusted file copied to original location: {original_json_path}")
    
    return output_path

def find_word_by_timing(word, auto_word_timestamps, expected_time, tolerance=1.7):
    """
    Find a word in the auto-generated word timestamps based on expected timing.
    
    Args:
        word: The word to find
        auto_word_timestamps: List of auto-generated word timestamps
        expected_time: Expected time (in seconds) where the word should be
        tolerance: Time tolerance in seconds (default: 1.7)
    
    Returns:
        The timestamp data for the word, or None if not found
    """
    # Clean the word for comparison
    clean_word = re.sub(r'[^\w\s]', '', word.lower())
    
    # Skip common words that appear frequently and can cause matching issues
    common_words = ["i", "you", "the", "a", "an", "and", "is", "are", "to", "in", "it", "that", "of", "for", "on", "with"]
    if clean_word in common_words:
        print(f"Skipping common word '{clean_word}' for timing adjustment")
        return None
    
    # Find all instances of the word within the tolerance window
    matching_timestamps = []
    
    for timestamp in auto_word_timestamps:
        auto_word = timestamp["word"].lower()
        # Check for exact match or if one contains the other
        if auto_word == clean_word or clean_word in auto_word or auto_word in clean_word:
            # Calculate the midpoint of the timestamp
            time_midpoint = (timestamp["start"] + timestamp["end"]) / 2
            # Check if it's within the tolerance
            if abs(time_midpoint - expected_time) <= tolerance:
                matching_timestamps.append((timestamp, abs(time_midpoint - expected_time)))
    
    # If we found exactly one match within the tolerance, return it
    if len(matching_timestamps) == 1:
        return matching_timestamps[0][0]
    # If we found multiple matches, check if one is significantly closer than the others
    elif len(matching_timestamps) > 1:
        # Sort by time difference
        matching_timestamps.sort(key=lambda x: x[1])
        # If the closest match is at least 0.5 seconds closer than the next closest, use it
        if len(matching_timestamps) > 1 and matching_timestamps[0][1] + 0.5 < matching_timestamps[1][1]:
            return matching_timestamps[0][0]
        else:
            print(f"Multiple matches found for '{clean_word}' around {expected_time}s, skipping to avoid ambiguity")
            return None
    
    # If no match found within tolerance, try to find any instance of the word
    # but only if it's not a common word and there's only one instance in the entire transcript
    if clean_word not in common_words:
        exact_matches = []
        for timestamp in auto_word_timestamps:
            auto_word = timestamp["word"].lower()
            if auto_word == clean_word or clean_word in auto_word or auto_word in clean_word:
                exact_matches.append(timestamp)
        
        # Only use if there's exactly one match in the entire transcript
        if len(exact_matches) == 1:
            return exact_matches[0]
    
    return None

def simple_adjust_timestamps(original_json_path, auto_json_path, output_path=None, replace_original=True):
    """
    A simpler approach to adjust timestamps based on finding words with similar timings.
    
    Args:
        original_json_path: Path to the original timestamp JSON file
        auto_json_path: Path to the auto-generated timestamp JSON file
        output_path: Path to save the adjusted JSON file (optional)
        replace_original: If True, replace the original file with the adjusted one
    
    Returns:
        Path to the adjusted JSON file, or None if failed
    """
    # Load the original and auto-generated JSON files
    original_data = load_json_file(original_json_path)
    auto_data = load_json_file(auto_json_path)
    
    if not original_data or not auto_data:
        return None
    
    # Load the raw word timestamps
    dialogue_id = original_data["id"]
    raw_word_json_path = os.path.join(config.AUDIO_PATH, f"word_timestamps_{dialogue_id}.json")
    auto_word_timestamps = load_json_file(raw_word_json_path)
    
    if not auto_word_timestamps:
        print(f"Raw word timestamps not found: {raw_word_json_path}")
        return None
    
    # Create a copy of the original data
    adjusted_data = original_data.copy()
    
    # Process each phrase in the dialogue
    for i, phrase in enumerate(adjusted_data["dialogue"]):
        # Create a copy of the phrase to avoid modifying the original
        adjusted_phrase = phrase.copy()
        
        # Extract words from the phrase, excluding common words at the beginning and end
        words = re.findall(r'\b\w+\b', phrase["text"])
        if not words:
            continue
        
        # Try to find non-common words at the beginning and end of the phrase
        common_words = ["i", "you", "the", "a", "an", "and", "is", "are", "to", "in", "it", "that", "of", "for", "on", "with"]
        
        # Find the first non-common word
        first_word_index = 0
        while first_word_index < len(words) and words[first_word_index].lower() in common_words:
            first_word_index += 1
        
        # Find the last non-common word
        last_word_index = len(words) - 1
        while last_word_index >= 0 and words[last_word_index].lower() in common_words:
            last_word_index -= 1
        
        # If we couldn't find non-common words, use the original first and last words
        if first_word_index >= len(words) or last_word_index < 0:
            first_word = words[0]
            last_word = words[-1]
        else:
            first_word = words[first_word_index]
            last_word = words[last_word_index]
        
        # Get the expected times from the original phrase
        start_expected = phrase["start_time"]
        end_expected = phrase["end_time"]
        
        # Find the first word based on timing
        first_word_timestamp = find_word_by_timing(
            first_word, 
            auto_word_timestamps, 
            start_expected
        )
        
        # Find the last word based on timing
        last_word_timestamp = find_word_by_timing(
            last_word, 
            auto_word_timestamps, 
            end_expected
        )
        
        # Adjust the start time if the first word was found
        if first_word_timestamp:
            adjusted_phrase["start_time"] = round(first_word_timestamp["start"], 2)
        
        # Adjust the end time if the last word was found
        if last_word_timestamp:
            adjusted_phrase["end_time"] = round(last_word_timestamp["end"], 2)
        
        # Update the phrase in the adjusted data
        adjusted_data["dialogue"][i] = adjusted_phrase
    
    # Validate and fix the timestamps to ensure they are logical
    # This will handle cases where the end of one phrase needs to match the start of the next
    adjusted_data["dialogue"] = validate_and_fix_timestamps(adjusted_data["dialogue"])
    
    # Set the output path if not provided
    if not output_path:
        output_path = original_json_path.replace('.json', '_adjusted.json')
    
    # Write the adjusted JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(adjusted_data, f, ensure_ascii=False, indent=2)
    
    print(f"Adjusted timestamp JSON file saved to: {output_path}")
    
    # If replace_original is True, copy the adjusted file over the original
    if replace_original:
        # Create a backup of the original file
        backup_path = original_json_path.replace('.json', '_original.json')
        shutil.copy2(original_json_path, backup_path)
        print(f"Original file backed up to: {backup_path}")
        
        # Copy the adjusted file over the original
        shutil.copy2(output_path, original_json_path)
        print(f"Adjusted file copied to original location: {original_json_path}")
    
    return output_path

def main():
    """Main function to adjust timestamps."""
    parser = argparse.ArgumentParser(description="Adjust the timings in the generated timestamp JSON files based on the auto-generated timestamps")
    parser.add_argument("--dialogue-id", type=str, help="Dialogue ID to process")
    parser.add_argument("--simple", action="store_true", help="Use the simpler timestamp adjustment approach")
    parser.add_argument("--no-replace", action="store_true", help="Don't replace the original file with the adjusted one")
    args = parser.parse_args()
    
    # Determine whether to replace the original file
    replace_original = not args.no_replace
    
    # Process a specific dialogue if provided
    if args.dialogue_id:
        original_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{args.dialogue_id}.json")
        auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{args.dialogue_id}_auto.json")
        
        if not os.path.exists(original_json_path):
            print(f"Original JSON file not found: {original_json_path}")
            return
        
        if not os.path.exists(auto_json_path):
            print(f"Auto-generated JSON file not found: {auto_json_path}")
            return
        
        # Use the simple approach if specified, otherwise use the default approach
        if args.simple:
            print("Using simple timestamp adjustment approach")
            simple_adjust_timestamps(original_json_path, auto_json_path, replace_original=replace_original)
        else:
            adjust_timestamps(original_json_path, auto_json_path, replace_original=replace_original)
        return
    
    # Otherwise, process all dialogues
    original_json_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*.json"))
    
    # Filter out auto-generated and adjusted files
    original_json_files = [f for f in original_json_files if not f.endswith('_auto.json') and not f.endswith('_adjusted.json') and not f.endswith('_no_punctuation.json') and not f.endswith('_original.json')]
    
    if not original_json_files:
        print("No original JSON files found.")
        return
    
    print(f"Found {len(original_json_files)} original JSON files to process.")
    
    # Process each file
    for original_json_path in original_json_files:
        # Extract the dialogue ID
        match = re.search(r'dialogue_([a-f0-9]+)\.json', os.path.basename(original_json_path))
        if not match:
            print(f"Could not extract dialogue ID from filename: {original_json_path}")
            continue
        
        dialogue_id = match.group(1)
        auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}_auto.json")
        
        if not os.path.exists(auto_json_path):
            print(f"Auto-generated JSON file not found for dialogue {dialogue_id}. Skipping.")
            continue
        
        print(f"Processing dialogue {dialogue_id}...")
        # Use the simple approach by default for batch processing
        simple_adjust_timestamps(original_json_path, auto_json_path, replace_original=replace_original)

if __name__ == "__main__":
    main() 