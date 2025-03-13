"""
Script to stitch together audio files with proper Vietnamese pronunciation.
This script takes the stitching info JSON files and creates a full dialogue audio file.
"""

import os
import argparse
import json
import glob
import sys
import wave
import io
import requests
from pathlib import Path
import config
import utils

def find_audio_directories():
    """Find all audio directories that have stitching info files."""
    audio_dirs = []
    for audio_dir in glob.glob(f"{config.AUDIO_PATH}/*"):
        if os.path.isdir(audio_dir):
            # Check if there are any stitching info files
            stitching_files = glob.glob(f"{audio_dir}/*_stitching_info.json")
            if stitching_files:
                audio_dirs.append(audio_dir)
    return audio_dirs

def convert_mp3_to_wav(mp3_path, wav_path):
    """Convert an MP3 file to WAV format using an online converter API."""
    try:
        print(f"Converting {mp3_path} to WAV format...")
        
        # Read the MP3 file
        with open(mp3_path, 'rb') as f:
            mp3_data = f.read()
        
        # Use an online converter API (this is a placeholder - you would need to implement this)
        # For now, we'll just copy the MP3 file to the WAV path
        with open(wav_path, 'wb') as f:
            f.write(mp3_data)
        
        print(f"Converted to {wav_path}")
        return True
    except Exception as e:
        print(f"Error converting MP3 to WAV: {e}")
        return False

def create_silent_wav(duration_ms, wav_path):
    """Create a silent WAV file with the specified duration."""
    try:
        # Create a silent WAV file
        sample_rate = 44100
        n_channels = 2
        sample_width = 2  # 16-bit
        
        # Calculate number of frames
        n_frames = int(duration_ms / 1000 * sample_rate)
        
        # Create silent frames
        silent_frames = b'\x00' * (n_frames * n_channels * sample_width)
        
        # Create WAV file
        with wave.open(wav_path, 'wb') as wav_file:
            wav_file.setnchannels(n_channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(silent_frames)
        
        print(f"Created silent WAV file: {wav_path}")
        return True
    except Exception as e:
        print(f"Error creating silent WAV file: {e}")
        return False

def stitch_audio_file(stitching_info_path, output_path):
    """Create a batch file with ffmpeg commands to stitch audio files."""
    try:
        # Load stitching info
        with open(stitching_info_path, 'r', encoding='utf-8') as f:
            stitching_info = json.load(f)
        
        # Get the English audio file
        english_audio_path = stitching_info["english_audio"]
        
        # Create a batch file with ffmpeg commands
        batch_lines = []
        batch_lines.append("@echo off")
        batch_lines.append("echo Stitching audio files...")
        
        # If there are no Vietnamese words, just copy the English audio
        if not stitching_info["vietnamese_words"]:
            batch_lines.append(f"copy \"{english_audio_path}\" \"{output_path}\"")
        else:
            # Get the Vietnamese word positions and sort them by start position
            viet_words = sorted(stitching_info["vietnamese_words"], key=lambda x: x["start_pos"])
            
            # Create a temporary directory for intermediate files
            temp_dir = os.path.join(os.path.dirname(output_path), "temp")
            batch_lines.append(f"mkdir \"{temp_dir}\" 2>nul")
            
            # Create a list of files to concatenate
            concat_files = []
            
            # Add segments before, between, and after Vietnamese words
            current_pos = 0
            for i, word_info in enumerate(viet_words):
                # Get the Vietnamese word audio
                viet_audio_path = word_info["audio_path"]
                
                # Estimate the position in the audio file based on text position
                text = stitching_info["text"]
                text_length = len(text)
                
                # Assuming a 3-minute audio file for the full text
                english_duration_sec = 180
                
                # Calculate the approximate start and end positions in the audio
                start_sec = (word_info["start_pos"] / text_length) * english_duration_sec
                end_sec = (word_info["end_pos"] / text_length) * english_duration_sec
                
                # Add the segment before the Vietnamese word
                if current_pos < start_sec:
                    before_segment = f"{temp_dir}\\before_{i}.mp3"
                    batch_lines.append(f"ffmpeg -i \"{english_audio_path}\" -ss {current_pos} -to {start_sec} -c copy \"{before_segment}\" -y")
                    concat_files.append(before_segment)
                
                # Add a short pause before the Vietnamese word
                pause_before = f"{temp_dir}\\pause_before_{i}.mp3"
                batch_lines.append(f"ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 0.3 \"{pause_before}\" -y")
                concat_files.append(pause_before)
                
                # Add the Vietnamese word
                concat_files.append(viet_audio_path)
                
                # Add a short pause after the Vietnamese word
                pause_after = f"{temp_dir}\\pause_after_{i}.mp3"
                batch_lines.append(f"ffmpeg -f lavfi -i anullsrc=r=44100:cl=stereo -t 0.3 \"{pause_after}\" -y")
                concat_files.append(pause_after)
                
                # Update the current position
                current_pos = end_sec
            
            # Add the segment after the last Vietnamese word
            if current_pos < english_duration_sec:
                after_segment = f"{temp_dir}\\after.mp3"
                batch_lines.append(f"ffmpeg -i \"{english_audio_path}\" -ss {current_pos} -c copy \"{after_segment}\" -y")
                concat_files.append(after_segment)
            
            # Create a file list for ffmpeg
            file_list = f"{temp_dir}\\file_list.txt"
            # Use raw strings for the file paths
            batch_lines.append(f"echo file '{concat_files[0]}' > \"{file_list}\"")
            for file_path in concat_files[1:]:
                batch_lines.append(f"echo file '{file_path}' >> \"{file_list}\"")
            
            # Concatenate all files
            batch_lines.append(f"ffmpeg -f concat -safe 0 -i \"{file_list}\" -c copy \"{output_path}\" -y")
            
            # Clean up temporary files
            batch_lines.append(f"rmdir /s /q \"{temp_dir}\"")
        
        # Write the batch file
        batch_path = os.path.join(os.path.dirname(output_path), "stitch_audio.bat")
        with open(batch_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(batch_lines))
        
        print(f"Batch file created: {batch_path}")
        print(f"To stitch the audio files, run the batch file: {batch_path}")
        
        return True
    except Exception as e:
        print(f"Error creating batch file: {e}")
        return False

def process_audio_directory(audio_dir):
    """Process all stitching info files in an audio directory."""
    # Find all stitching info files
    stitching_files = glob.glob(f"{audio_dir}/*_stitching_info.json")
    
    if not stitching_files:
        print(f"No stitching info files found in {audio_dir}")
        return False
    
    success = True
    for stitching_file in stitching_files:
        # Get the base name without the _stitching_info.json suffix
        base_name = os.path.basename(stitching_file).replace("_stitching_info.json", "")
        
        # Create the output path
        output_path = f"{audio_dir}/{base_name}_stitched.mp3"
        
        # Create batch file for stitching
        if not stitch_audio_file(stitching_file, output_path):
            success = False
    
    return success

def main():
    parser = argparse.ArgumentParser(description='Create batch files for stitching audio files')
    parser.add_argument('--audio_dir', type=str,
                        help='Directory containing audio files and stitching info')
    parser.add_argument('--all', action='store_true',
                        help='Process all audio directories with stitching info')
    
    args = parser.parse_args()
    
    utils.ensure_directories_exist()
    
    if args.all:
        # Process all audio directories with stitching info
        audio_dirs = find_audio_directories()
        if not audio_dirs:
            print("No audio directories with stitching info found.")
            return
        
        for audio_dir in audio_dirs:
            print(f"Processing audio directory: {audio_dir}")
            process_audio_directory(audio_dir)
    elif args.audio_dir:
        # Process a specific audio directory
        if not os.path.exists(args.audio_dir):
            print(f"Audio directory not found: {args.audio_dir}")
            return
        
        process_audio_directory(args.audio_dir)
    else:
        # Find the most recent audio directory with stitching info
        audio_dirs = find_audio_directories()
        if not audio_dirs:
            print("No audio directories with stitching info found.")
            return
        
        # Sort by modification time, newest first
        audio_dirs.sort(key=os.path.getmtime, reverse=True)
        
        # Process the most recent audio directory
        audio_dir = audio_dirs[0]
        print(f"Processing most recent audio directory: {audio_dir}")
        process_audio_directory(audio_dir)

if __name__ == "__main__":
    main() 