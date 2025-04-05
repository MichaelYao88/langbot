#!/usr/bin/env python3
"""
Script to generate a complete video by running:
1. generate_audio.py - Creates the audio file
2. generate_dialogue_timestamps.py - Creates timestamp data
3. generate_background.py - Creates the final video
"""

import os
import sys
import json
import logging
import argparse
import subprocess
from pathlib import Path
import config
from generate_audio import main as generate_audio
from generate_dialogue_timestamps import main as generate_timestamps
import glob
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_complete_video')

def run_generate_audio(dialogue_id=None):
    """Run generate_audio.py to create the audio file."""
    logger.info("Step 1: Generating audio...")
    try:
        if dialogue_id:
            # Find the dialogue file
            dialogue_file = None
            for file in Path(config.DIALOGUES_PATH).glob("*.json"):
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data["id"] == dialogue_id:
                        dialogue_file = file
                        break
            
            if not dialogue_file:
                logger.error(f"Could not find dialogue file for ID: {dialogue_id}")
                return False
            
            # Run generate_audio with specific file
            sys.argv = ['generate_audio.py', str(dialogue_file)]
        else:
            # Run generate_audio normally
            sys.argv = ['generate_audio.py']
        
        generate_audio()
        return True
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return False

def run_generate_timestamps(dialogue_id=None):
    """Run generate_dialogue_timestamps.py to create timestamp data."""
    logger.info("Step 2: Generating timestamps...")
    try:
        if dialogue_id:
            # Find the audio file
            audio_file = None
            for file in Path(config.AUDIO_PATH).glob("*.mp3"):
                if dialogue_id in file.name:
                    audio_file = file
                    break
            
            if not audio_file:
                logger.error(f"Could not find audio file for ID: {dialogue_id}")
                return False
            
            # Run generate_timestamps with specific file
            sys.argv = ['generate_dialogue_timestamps.py', '--audio', str(audio_file), '--force']
        else:
            # Run generate_timestamps normally
            sys.argv = ['generate_dialogue_timestamps.py', '--count', '1']
        
        generate_timestamps()
        return True
    except Exception as e:
        logger.error(f"Error generating timestamps: {str(e)}")
        return False

def run_generate_background(dialogue_id=None):
    """Run generate_background.py to create the final video."""
    logger.info("Step 3: Generating background video...")
    try:
        cmd = ['python', 'generate_background.py']
        if dialogue_id:
            # Find the timestamp file
            timestamp_file = None
            for file in Path(config.AUDIO_PATH).glob("*.json"):
                if dialogue_id in file.name:
                    timestamp_file = file
                    break
            
            if not timestamp_file:
                logger.error(f"Could not find timestamp file for ID: {dialogue_id}")
                return False
            
            # Add timestamp file argument
            cmd.extend(['--timestamps', str(timestamp_file)])
        
        # Run generate_background as a subprocess
        logger.info(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"generate_background.py failed with output: {result.stderr}")
            return False
            
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running generate_background.py: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error generating background: {str(e)}")
        return False

def find_unprocessed_audio_file():
    """Find an audio file that hasn't been processed yet."""
    # Get all audio files
    audio_files = glob.glob("data/audio/*.mp3")
    if not audio_files:
        raise ValueError("No audio files found in data/audio directory")
    
    # Get all existing video files
    video_files = glob.glob("output/*.mp4")
    processed_ids = set()
    
    # Extract dialogue IDs from existing video files
    for video_file in video_files:
        # Extract the dialogue ID from the filename
        filename = os.path.basename(video_file)
        
        # Try to extract dialogue ID from various video filename patterns
        video_id_match = re.search(r'([a-f0-9]{8})', filename)
        if video_id_match:
            dialogue_id = video_id_match.group(1)
            processed_ids.add(dialogue_id)
            logger.info(f"Found processed dialogue ID: {dialogue_id} from video: {filename}")
    
    logger.info(f"Found {len(processed_ids)} processed dialogue IDs")
    
    # Find unprocessed audio files
    for audio_file in audio_files:
        # Extract the dialogue ID from the filename
        filename = os.path.basename(audio_file)
        
        # Try different filename patterns
        # Old pattern: dialogue_ID_elevenlabs_slow.mp3
        old_pattern_match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
        
        # New pattern without topic word: dialogue_ID.mp3
        new_pattern_without_topic_match = re.match(r'dialogue_([a-f0-9]+)\.mp3', filename)
        
        # New pattern with topic word: topic_word_ID.mp3
        new_pattern_with_topic_match = re.match(r'.*_([a-f0-9]+)\.mp3', filename)
        
        # Get the dialogue ID based on which pattern matched
        dialogue_id = None
        if old_pattern_match:
            dialogue_id = old_pattern_match.group(1)
        elif new_pattern_without_topic_match:
            dialogue_id = new_pattern_without_topic_match.group(1)
        elif new_pattern_with_topic_match:
            dialogue_id = new_pattern_with_topic_match.group(1)
        
        if dialogue_id:
            if dialogue_id in processed_ids:
                logger.info(f"Skipping processed audio file: {filename} (ID: {dialogue_id})")
                continue
                
            # Check if dialogue file exists
            dialogue_path = find_dialogue_file(audio_file)
            if dialogue_path:
                logger.info(f"Found unprocessed audio file: {filename} (ID: {dialogue_id})")
                return audio_file
            else:
                logger.info(f"No dialogue file found for: {filename} (ID: {dialogue_id})")
    
    logger.info("No unprocessed audio files found")
    return None

def find_dialogue_file(audio_path):
    """Find the corresponding dialogue JSON file for an audio file."""
    # Extract the dialogue ID from the filename
    filename = os.path.basename(audio_path)
    
    # Try different filename patterns to extract dialogue ID
    old_pattern_match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
    new_pattern_without_topic_match = re.match(r'dialogue_([a-f0-9]+)\.mp3', filename)
    new_pattern_with_topic_match = re.match(r'.*_([a-f0-9]+)\.mp3', filename)
    
    dialogue_id = None
    if old_pattern_match:
        dialogue_id = old_pattern_match.group(1)
    elif new_pattern_without_topic_match:
        dialogue_id = new_pattern_without_topic_match.group(1)
    elif new_pattern_with_topic_match:
        dialogue_id = new_pattern_with_topic_match.group(1)
    
    if not dialogue_id:
        return None
    
    # Look for dialogue file with matching ID
    for file in Path("data/dialogues").glob("*.json"):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get("id") == dialogue_id:
                    return str(file)
        except:
            continue
    
    return None

def concat_videos(video1_path, video2_path, output_path):
    """
    Concatenate two videos using FFmpeg's filter_complex.
    The first video (title) has no audio, the second video has audio.
    Also sets the first frame of the title card as the video thumbnail.
    """
    try:
        # First concatenate the videos
        cmd = [
            "ffmpeg",
            "-i", video1_path,   # Title video (no audio)
            "-i", video2_path,   # Background video (with audio)
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1[outv];[1:a]acopy[outa]",  # Concat video, pass through audio
            "-map", "[outv]",    # Map concatenated video
            "-map", "[outa]",    # Map audio from second video
            "-c:v", "libx264",   # Use same video codec
            "-c:a", "aac",       # Use same audio codec
            "-movflags", "+faststart",  # Enable fast start for streaming
            "-y",
            output_path
        ]
        
        logger.info(f"Running FFmpeg concat command: {' '.join(cmd)}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error concatenating videos: {result.stderr}")
            return False
        
        # Now extract the first frame from title video
        temp_thumb = "output/temp_thumb.jpg"
        cmd_thumb = [
            "ffmpeg",
            "-i", video1_path,
            "-vframes", "1",  # Extract first frame
            "-y",
            temp_thumb
        ]
        
        logger.info("Extracting thumbnail from title card...")
        result = subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            logger.error(f"Error extracting thumbnail: {result.stderr}")
            return False
        
        # Finally, inject the thumbnail into the video
        temp_output = "output/temp_output.mp4"
        os.rename(output_path, temp_output)
        
        cmd_inject = [
            "ffmpeg",
            "-i", temp_output,
            "-i", temp_thumb,
            "-map", "0",  # Map all streams from first input
            "-map", "1",  # Map thumbnail from second input
            "-c", "copy",  # Copy all streams without re-encoding
            "-disposition:v:1", "attached_pic",  # Set second video stream as poster
            "-y",
            output_path
        ]
        
        logger.info("Setting video thumbnail...")
        result = subprocess.run(cmd_inject, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Clean up temporary files
        os.remove(temp_thumb)
        os.remove(temp_output)
        
        if result.returncode != 0:
            logger.error(f"Error setting thumbnail: {result.stderr}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error running FFmpeg: {str(e)}")
        # Clean up any temporary files that might exist
        for temp_file in ["output/temp_thumb.jpg", "output/temp_output.mp4"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        return False

def generate_complete_video(audio_path=None):
    """
    Generate a complete video with title card and background video.
    
    Args:
        audio_path (str, optional): Path to a specific audio file to use.
                                  If None, an unprocessed file will be selected.
    """
    # Import the required functions from other scripts
    from generate_background import generate_background
    from generate_title import generate_title_card
    
    # Create temporary output paths
    os.makedirs("output", exist_ok=True)
    temp_background = "output/temp_background.mp4"
    temp_title = "output/temp_title.mp4"
    
    # If no audio path provided, find an unprocessed audio file
    if audio_path is None:
        audio_path = find_unprocessed_audio_file()
        if not audio_path:
            raise ValueError("No unprocessed audio files found")
        print(f"Selected unprocessed audio file: {audio_path}")
    
    # Find the corresponding dialogue file
    dialogue_path = find_dialogue_file(audio_path)
    if not dialogue_path:
        raise ValueError(f"No dialogue file found for audio: {audio_path}")
    print(f"Found corresponding dialogue file: {dialogue_path}")
    
    print("Step 1: Generating title card...")
    title_result = generate_title_card(dialogue_path, temp_title)
    if not title_result:
        raise ValueError("Failed to generate title card")
    
    print("\nStep 2: Generating background video...")
    background_result = generate_background(temp_background, audio_path=audio_path, cleanup=False)
    if not background_result:
        raise ValueError("Failed to generate background video")
    
    # Get the base name for the final output
    filename = os.path.basename(audio_path)
    dialogue_id = None
    
    # Extract dialogue ID using the same patterns
    old_pattern_match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', filename)
    new_pattern_without_topic_match = re.match(r'dialogue_([a-f0-9]+)\.mp3', filename)
    new_pattern_with_topic_match = re.match(r'.*_([a-f0-9]+)\.mp3', filename)
    
    if old_pattern_match:
        dialogue_id = old_pattern_match.group(1)
    elif new_pattern_without_topic_match:
        dialogue_id = new_pattern_without_topic_match.group(1)
    elif new_pattern_with_topic_match:
        dialogue_id = new_pattern_with_topic_match.group(1)
    
    # Find the corresponding dialogue file to get the topic word
    topic_word = None
    if dialogue_path:
        try:
            with open(dialogue_path, 'r', encoding='utf-8') as f:
                dialogue_data = json.load(f)
                topic_word = dialogue_data.get("topic_word", "").strip()
                # Replace spaces with underscores and remove special characters
                topic_word = re.sub(r'[^\w\s-]', '', topic_word).replace(' ', '_')
        except Exception as e:
            print(f"Warning: Could not extract topic word from dialogue file: {str(e)}")
    
    # Use topic_word in the filename if available, otherwise use dialogue prefix
    if topic_word:
        final_output = f"output/{topic_word}_{dialogue_id}.mp4"
    else:
        final_output = f"output/dialogue_{dialogue_id}.mp4"
    
    print("\nStep 3: Combining videos...")
    if concat_videos(temp_title, temp_background, final_output):
        print(f"\nComplete video generated successfully: {final_output}")
        print("Temporary files kept for debugging: temp_title.mp4 and temp_background.mp4")
        return final_output
    else:
        raise ValueError("Failed to combine videos")

def main():
    """Main function to run the complete video generation process."""
    parser = argparse.ArgumentParser(description="Generate a complete video with title card and background")
    parser.add_argument("--audio", type=str, help="Path to the audio file to use", default=None)
    args = parser.parse_args()
    
    try:
        generate_complete_video(args.audio)
    except Exception as e:
        logger.error(f"Error generating complete video: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 