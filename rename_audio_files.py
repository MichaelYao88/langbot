#!/usr/bin/env python3
"""
Script to rename existing audio files to match the new naming convention.
Old format: dialogue_ID_elevenlabs_slow.mp3
New format: topic_word_ID.mp3
"""

import os
import json
import glob
import re

def main():
    # Get all audio files with the old naming convention
    audio_files = glob.glob("data/audio/dialogue_*_elevenlabs_slow.mp3")
    print(f"Found {len(audio_files)} audio files to rename")
    
    for audio_file in audio_files:
        # Extract the dialogue ID from the filename
        filename = os.path.basename(audio_file)
        match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
        
        if not match:
            print(f"Could not extract dialogue ID from filename: {filename}")
            continue
        
        dialogue_id = match.group(1)
        
        # Find the corresponding dialogue file
        dialogue_files = glob.glob(f"data/dialogues/*_{dialogue_id}.json")
        
        if not dialogue_files:
            print(f"Could not find dialogue file for ID: {dialogue_id}")
            continue
        
        # Load the dialogue file to get the topic word
        with open(dialogue_files[0], 'r', encoding='utf-8') as f:
            dialogue_data = json.load(f)
        
        topic_word = dialogue_data.get("topic_word", "")
        
        if not topic_word:
            print(f"No topic word found for dialogue ID: {dialogue_id}")
            continue
        
        # Create the new filename
        new_filename = f"{topic_word}_{dialogue_id}.mp3"
        new_path = os.path.join(os.path.dirname(audio_file), new_filename)
        
        # Rename the file
        print(f"Renaming {filename} to {new_filename}")
        os.rename(audio_file, new_path)
    
    print("Renaming complete")

if __name__ == "__main__":
    main() 