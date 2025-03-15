#!/usr/bin/env python3
"""
Script to generate JSON files with dialogue timestamps for audio files.

This script performs the following steps:
1. Generate initial timestamp JSON file
2. Run speech recognition for accurate timestamps
3. Align subtitles with original dialogue using Anthropic's API
"""

import os
import sys
import glob
import json
import argparse
import shutil
import re
import config
from auto_subtitle import generate_auto_timestamps
from align_subtitles import align_subtitles

def generate_initial_timestamps(audio_file, output_file=None):
    """
    Generate initial timestamp JSON file for an audio file.
    
    Args:
        audio_file: Path to the audio file
        output_file: Path to save the JSON file (optional)
    
    Returns:
        Path to the generated JSON file, or None if failed
    """
    # Extract the dialogue ID from the audio filename
    match = re.search(r'([a-f0-9]+)\.mp3$', audio_file)
    if not match:
        print(f"Could not extract dialogue ID from filename: {audio_file}")
        return None
    
    dialogue_id = match.group(1)
    
    # Find the dialogue file
    dialogue_files = glob.glob("data/dialogues/*.json")
    dialogue_data = None
    
    for file_path in dialogue_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data["id"] == dialogue_id:
                    dialogue_data = data
                    break
        except:
            continue
    
    if not dialogue_data:
        print(f"Could not find dialogue file for ID: {dialogue_id}")
        return None
    
    # Set the output file path if not provided
    if not output_file:
        output_file = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
    
    # Create a copy of the dialogue data
    timestamp_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": []
    }
    
    # Add placeholder timestamps to each dialogue entry
    current_time = 0.0
    
    for entry in dialogue_data["english_dialogue"]:
        # Extract the text and speaker
        text = entry["text"]
        speaker = entry["speaker"]
        
        # Calculate a rough duration based on the text length (1 second per 10 characters)
        duration = max(1.0, len(text) / 10)
        
        # Extract Vietnamese words
        viet_words = []
        topic_word = dialogue_data.get("topic_word", "")
        if topic_word and topic_word.lower() in text.lower():
            viet_words.append(topic_word)
        
        common_words = dialogue_data.get("common_words", [])
        for word_data in common_words:
            if "word" in word_data and word_data["word"].lower() in text.lower():
                viet_words.append(word_data["word"])
        
        # Create a timestamp entry
        timestamp_entry = {
            "speaker": speaker,
            "text": text,
            "start_time": current_time,
            "end_time": current_time + duration,
            "viet_words": viet_words
        }
        
        timestamp_data["dialogue"].append(timestamp_entry)
        
        # Update the current time
        current_time += duration
    
    # Write the timestamp JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timestamp_data, f, ensure_ascii=False, indent=2)
    
    print(f"Initial timestamp JSON file saved to: {output_file}")
    
    return output_file

def process_audio_file(audio_file, skip_auto=False, skip_adjust=False):
    """
    Process an audio file to generate timestamp JSON files.
    
    Args:
        audio_file: Path to the audio file
        skip_auto: If True, skip the speech recognition step
        skip_adjust: If True, skip the timestamp adjustment step
    
    Returns:
        Path to the final timestamp JSON file, or None if failed
    """
    # Extract the dialogue ID from the audio filename
    match = re.search(r'([a-f0-9]+)\.mp3$', audio_file)
    if not match:
        print(f"Could not extract dialogue ID from filename: {audio_file}")
        return None
    
    dialogue_id = match.group(1)
    
    # Generate initial timestamp JSON file
    initial_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
    generate_initial_timestamps(audio_file, initial_json_path)
    
    # Run speech recognition for accurate timestamps
    auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}_auto.json")
    
    if not skip_auto:
        print(f"Running speech recognition for accurate timestamps...")
        generate_auto_timestamps(audio_file)
    else:
        print(f"Skipping speech recognition step...")
    
    # Align subtitles with original dialogue if available
    if not skip_adjust and os.path.exists(auto_json_path):
        print(f"Aligning subtitles with original dialogue...")
        align_subtitles(auto_json_path, replace_original=True)
    
    return initial_json_path

def find_unprocessed_audio_file(processed_ids=None):
    """
    Find an audio file that doesn't have a corresponding JSON file.
    
    Args:
        processed_ids: Set of dialogue IDs that have already been processed
    
    Returns:
        Path to an unprocessed audio file, or None if all files are processed
    """
    # Get all audio files
    audio_files = glob.glob(os.path.join(config.AUDIO_PATH, "*.mp3"))
    
    if not audio_files:
        print("No audio files found.")
        return None
    
    # Initialize processed_ids if not provided
    if processed_ids is None:
        processed_ids = set()
    
    # Get all existing video files in the output directory
    video_files = glob.glob("output/*.mp4")
    video_dialogue_ids = set()
    
    # Extract dialogue IDs from existing video files
    for video_file in video_files:
        # Extract the dialogue ID from the filename (last part before .mp4)
        filename = os.path.basename(video_file)
        parts = filename.split('_')
        if len(parts) > 1:
            dialogue_id = parts[-1].replace('.mp4', '')
            video_dialogue_ids.add(dialogue_id)
    
    # Check each audio file
    for audio_file in audio_files:
        # Extract the dialogue ID from the audio filename
        match = re.search(r'([a-f0-9]+)\.mp3$', audio_file)
        if not match:
            continue
        
        dialogue_id = match.group(1)
        
        # Skip if already processed in this session
        if dialogue_id in processed_ids:
            continue
        
        # Skip if a video already exists for this dialogue
        if dialogue_id in video_dialogue_ids:
            print(f"Skipping {audio_file} - video already exists in output directory")
            processed_ids.add(dialogue_id)  # Add to processed_ids to avoid checking again
            continue
        
        # Check if a JSON file already exists for this dialogue
        json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
        if os.path.exists(json_path):
            print(f"Skipping {audio_file} - JSON file already exists: {json_path}")
            processed_ids.add(dialogue_id)  # Add to processed_ids to avoid checking again
            continue
        
        # This audio file doesn't have a JSON file and doesn't have a video
        return audio_file
    
    return None

def main():
    """Main function to generate dialogue timestamps."""
    parser = argparse.ArgumentParser(description="Generate JSON files with dialogue timestamps for audio files")
    parser.add_argument("--audio", type=str, help="Path to a specific audio file to process")
    parser.add_argument("--skip", type=str, choices=["auto", "adjust"], help="Skip a specific step in the process")
    parser.add_argument("--count", type=int, default=1, help="Number of dialogues to process (default: 1)")
    parser.add_argument("--force", action="store_true", help="Process even if JSON file already exists or video exists in output")
    args = parser.parse_args()
    
    # Determine which steps to skip
    skip_auto = args.skip == "auto"
    skip_adjust = args.skip == "adjust"
    
    # Process a specific audio file if provided
    if args.audio:
        if not os.path.exists(args.audio):
            print(f"Audio file not found: {args.audio}")
            return
        
        # Extract the dialogue ID from the audio filename
        match = re.search(r'([a-f0-9]+)\.mp3$', args.audio)
        if not match:
            print(f"Could not extract dialogue ID from filename: {args.audio}")
            return
        
        dialogue_id = match.group(1)
        
        # Check if a JSON file already exists for this dialogue
        json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}.json")
        if os.path.exists(json_path) and not args.force:
            print(f"JSON file already exists for dialogue {dialogue_id}. Use --force to overwrite.")
            return
        
        # Check if a video already exists for this dialogue
        existing_videos = glob.glob(f"output/*_{dialogue_id}.mp4") + glob.glob(f"output/dialogue_{dialogue_id}.mp4")
        if existing_videos and not args.force:
            print(f"Video already exists for dialogue {dialogue_id}: {existing_videos[0]}. Use --force to process anyway.")
            return
        
        process_audio_file(args.audio, skip_auto, skip_adjust)
        return
    
    # Otherwise, process unprocessed audio files
    processed_count = 0
    processed_ids = set()
    
    while processed_count < args.count:
        # Find an unprocessed audio file
        audio_file = find_unprocessed_audio_file(processed_ids)
        
        if not audio_file:
            print("No more unprocessed audio files found.")
            break
        
        # Extract the dialogue ID from the audio filename
        match = re.search(r'([a-f0-9]+)\.mp3$', audio_file)
        if not match:
            continue
        
        dialogue_id = match.group(1)
        
        # Process the audio file
        print(f"Processing audio file: {audio_file}")
        process_audio_file(audio_file, skip_auto, skip_adjust)
        
        # Add the dialogue ID to the processed set
        processed_ids.add(dialogue_id)
        processed_count += 1
        
        print(f"Processed {processed_count}/{args.count} dialogues")

if __name__ == "__main__":
    main() 