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
from pathlib import Path
from pydub import AudioSegment
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import tempfile
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('dialogue_timestamps')

@dataclass
class DialogueSegment:
    """Represents a segment of dialogue with timing information."""
    text: str
    start_time: float  # in milliseconds
    end_time: float    # in milliseconds
    is_vietnamese: bool
    speaker: str

@dataclass
class DialogueLine:
    """Represents a complete line of dialogue with its segments."""
    speaker: str
    segments: List[DialogueSegment]
    start_time: float
    end_time: float

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
    
    # Original timestamp generation logic
    current_time = 0.0
    pause_between_lines = 0.5  # 500ms pause between lines
    
    for entry in dialogue_data["english_dialogue"]:
        text = entry["text"]
        speaker = entry["speaker"]
        
        # Calculate duration using character count (0.1 seconds per character)
        duration = max(1.0, len(text) * 0.1)  # Minimum 1 second per line
        
        # Detect Vietnamese words using simple substring matching
        viet_words = []
        for word_data in dialogue_data.get("common_words", []):
            if word_data["word"].lower() in text.lower():
                viet_words.append(word_data["word"])
        if dialogue_data.get("topic_word"):
            if dialogue_data["topic_word"].lower() in text.lower():
                viet_words.append(dialogue_data["topic_word"])
        
        # Create timestamp entry
        timestamp_entry = {
            "speaker": speaker,
            "text": text,
            "start_time": current_time,
            "end_time": current_time + duration,
            "viet_words": viet_words
        }
        
        timestamp_data["dialogue"].append(timestamp_entry)
        
        # Update current time with pause between lines
        current_time += duration + pause_between_lines
    
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

def split_into_subsegments(text: str, max_words: int = 6) -> List[str]:
    """Split text into subsegments of no more than max_words words each."""
    words = text.split()
    subsegments = []
    current_segment = []
    
    for word in words:
        current_segment.append(word)
        if len(current_segment) >= max_words:
            subsegments.append(" ".join(current_segment))
            current_segment = []
    
    if current_segment:  # Add any remaining words
        subsegments.append(" ".join(current_segment))
    
    return subsegments

def extract_segments_with_vietnamese(text: str) -> List[Tuple[str, bool]]:
    """
    Extract segments from text, separating Vietnamese and English parts.
    Ensures no segment is longer than 6 words.
    Returns list of (text, is_vietnamese) tuples.
    """
    # Pattern to match Vietnamese text within tags
    pattern = r'<vietnamese>(.*?)</vietnamese>'
    
    segments = []
    last_end = 0
    
    for match in re.finditer(pattern, text):
        # Add English text before Vietnamese if any
        if match.start() > last_end:
            english_text = text[last_end:match.start()].strip()
            if english_text:
                # Split English text into subsegments
                for subsegment in split_into_subsegments(english_text):
                    segments.append((subsegment, False))
        
        # Add Vietnamese text
        viet_text = match.group(1).strip()
        if viet_text:
            # Split Vietnamese text into subsegments
            for subsegment in split_into_subsegments(viet_text):
                segments.append((subsegment, True))
        
        last_end = match.end()
    
    # Add remaining English text if any
    if last_end < len(text):
        english_text = text[last_end:].strip()
        if english_text:
            # Split remaining English text into subsegments
            for subsegment in split_into_subsegments(english_text):
                segments.append((subsegment, False))
    
    return segments

def calculate_segment_duration(text: str, is_vietnamese: bool) -> float:
    """
    Calculate the duration of a segment based on its text and language.
    This matches the timing logic in generate_audio.py.
    
    Returns:
        Duration in milliseconds
    """
    # Constants matching generate_audio.py
    PAUSE_DURATION_MS = 1  # Duration of pause between segments
    VIETNAMESE_SPEECH_RATE = 0.8  # 80% of normal speed for Vietnamese
    ENGLISH_SPEECH_RATE = 0.8  # 80% of normal speed for English
    
    # Base character rate (matching generate_audio.py's timing)
    if is_vietnamese:
        chars_per_second = 10 * VIETNAMESE_SPEECH_RATE
    else:
        chars_per_second = 12 * ENGLISH_SPEECH_RATE
    
    # Calculate duration
    char_count = len(text.strip())
    duration_ms = (char_count / chars_per_second) * 1000
    
    # Ensure minimum duration
    return max(500, duration_ms)  # Minimum 500ms per segment

def generate_timestamps_for_dialogue(dialogue_file: str, audio_file: str) -> List[DialogueLine]:
    """
    Generate timestamps for each segment in the dialogue.
    Ensures segments match the audio stitching from generate_audio.py.
    
    Args:
        dialogue_file: Path to the JSON dialogue file
        audio_file: Path to the generated audio file
    
    Returns:
        List of DialogueLine objects containing timing information
    """
    # Load dialogue data
    with open(dialogue_file, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # Load the full audio file for verification
    full_audio = AudioSegment.from_mp3(audio_file)
    total_audio_duration = len(full_audio)
    
    dialogue_lines = []
    current_time = 0  # Keep track of current position in audio
    
    # Process each line in the dialogue
    for line in dialogue_data["english_dialogue"]:
        text = line["text"]
        speaker = line["speaker"]
        
        # Extract segments (English and Vietnamese)
        segments = extract_segments_with_vietnamese(text)
        
        line_segments = []
        line_start = current_time
        
        # Process each segment
        for i, (segment_text, is_vietnamese) in enumerate(segments):
            # Calculate segment duration based on the audio generation logic
            segment_start = current_time
            segment_duration = calculate_segment_duration(segment_text, is_vietnamese)
            segment_end = segment_start + segment_duration
            
            # Verify we haven't exceeded the total audio duration
            if segment_end > total_audio_duration:
                logger.warning(f"Segment end time {segment_end}ms exceeds audio duration {total_audio_duration}ms")
                segment_end = total_audio_duration
            
            # Create segment object
            segment = DialogueSegment(
                text=segment_text,
                start_time=segment_start,
                end_time=segment_end,
                is_vietnamese=is_vietnamese,
                speaker=speaker
            )
            
            line_segments.append(segment)
            
            # Add pause between segments
            current_time = segment_end + PAUSE_DURATION_MS
        
        # Create line object
        dialogue_line = DialogueLine(
            speaker=speaker,
            segments=line_segments,
            start_time=line_start,
            end_time=current_time
        )
        
        dialogue_lines.append(dialogue_line)
        current_time += SPEAKER_PAUSE_DURATION_MS  # Add pause between speakers
    
    # Verify total duration matches audio file
    if current_time > total_audio_duration:
        logger.warning(f"Total timestamp duration {current_time}ms exceeds audio duration {total_audio_duration}ms")
    
    return dialogue_lines

def save_timestamps(dialogue_lines: List[DialogueLine], output_file: str):
    """
    Save timestamp information in a format readable by generate_background.py.
    Includes verification information for debugging.
    
    Args:
        dialogue_lines: List of DialogueLine objects
        output_file: Path to save the timestamp data
    """
    # Calculate some statistics for verification
    total_segments = sum(len(line.segments) for line in dialogue_lines)
    max_segment_words = max(len(segment.text.split()) for line in dialogue_lines for segment in line.segments)
    
    timestamp_data = {
        "metadata": {
            "total_segments": total_segments,
            "max_segment_words": max_segment_words,
            "total_duration_ms": dialogue_lines[-1].end_time if dialogue_lines else 0
        },
        "lines": [
            {
                "speaker": line.speaker,
                "start_time": line.start_time,
                "end_time": line.end_time,
                "segments": [
                    {
                        "text": segment.text,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "is_vietnamese": segment.is_vietnamese,
                        "word_count": len(segment.text.split())
                    }
                    for segment in line.segments
                ]
            }
            for line in dialogue_lines
        ]
    }
    
    # Log verification information
    logger.info(f"Generated {total_segments} segments")
    logger.info(f"Maximum words per segment: {max_segment_words}")
    logger.info(f"Total duration: {timestamp_data['metadata']['total_duration_ms']}ms")
    
    # Verify no segment exceeds 6 words
    if max_segment_words > 6:
        logger.warning(f"Found segments with more than 6 words! Maximum was {max_segment_words}")
    
    # Save with proper encoding for Vietnamese characters
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(timestamp_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Timestamps saved to {output_file}")

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