import os
import random
import subprocess
import argparse
import glob
import json
from pathlib import Path
import re
from remove_punctuation import remove_punctuation_from_dialogue

def generate_background(output_path=None, test=False, audio_path=None):
    """
    Generate a background video from Subway Surfers with audio.
    The video length will match the full duration of a randomly selected audio file.
    The segment will be at least 15 seconds after the start and 15 seconds from the end.
    The output will be in portrait mode (9:16 aspect ratio) for TikTok/Reel/YouTube.
    Subtitles will be added using the timestamps from the corresponding JSON file.
    Character photos will be displayed when they are speaking.
    
    Args:
        output_path (str, optional): Path to save the output video. Defaults to 'output/background_[dialogue_id].mp4'.
        test (bool, optional): If True, generate a 10-second test clip. Defaults to False.
        audio_path (str, optional): Path to a specific audio file to use. If None, a random file is selected.
    """
    # Define paths
    video_path = "data/videos/subway/Subway Surfers Gameplay (PC UHD) [4K60FPS] (2160p_60fps_AV1-128kbit_AAC).mp4"
    
    # Get a random audio file from data/audio if audio_path is not provided
    if audio_path is None:
        audio_files = glob.glob("data/audio/dialogue_*_elevenlabs_slow.mp3")
        if not audio_files:
            raise ValueError("No audio files found in data/audio directory")
        
        # Select a random audio file
        audio_path = random.choice(audio_files)
    
    print(f"Selected audio file: {audio_path}")
    
    # Get the dialogue ID from the audio filename
    audio_filename = os.path.basename(audio_path)
    match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', audio_filename)
    if not match:
        raise ValueError(f"Could not extract dialogue ID from filename: {audio_filename}")
    
    dialogue_id = match.group(1)
    
    # Set the output path based on the dialogue ID if not provided
    if output_path is None:
        output_path = f"output/background_{dialogue_id}.mp4"
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Look for the corresponding JSON file with timestamps
    json_path = os.path.join(os.path.dirname(audio_path), f"dialogue_{dialogue_id}.json")
    if not os.path.exists(json_path):
        print(f"Warning: No timestamp JSON file found at {json_path}. Subtitles will not be added.")
        subtitle_data = None
    else:
        # Process the JSON file to remove punctuation
        no_punctuation_json_path = json_path.replace('.json', '_no_punctuation.json')
        
        # Check if the no-punctuation version already exists, if not create it
        if not os.path.exists(no_punctuation_json_path):
            print(f"Removing punctuation from {json_path}")
            remove_punctuation_from_dialogue(json_path)
        
        # Use the no-punctuation version if it exists, otherwise fall back to the original
        if os.path.exists(no_punctuation_json_path):
            with open(no_punctuation_json_path, 'r', encoding='utf-8') as f:
                subtitle_data = json.load(f)
                print(f"Loaded subtitle data without punctuation from {no_punctuation_json_path}")
        else:
            with open(json_path, 'r', encoding='utf-8') as f:
                subtitle_data = json.load(f)
                print(f"Loaded subtitle data from {json_path}")
    
    # Get audio duration
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        audio_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    audio_duration = float(result.stdout.strip())
    print(f"Audio duration: {audio_duration:.2f} seconds")
    
    # If test mode is enabled, limit to 10 seconds
    if test:
        audio_duration = min(10.0, audio_duration)
        print(f"Test mode enabled. Using only the first {audio_duration:.2f} seconds.")
    
    # Get video duration using ffprobe
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    total_video_duration = float(result.stdout.strip())
    
    # Calculate start time (at least 15 seconds after start and ensuring we have enough duration)
    # Also ensure we don't use the last 60 seconds (1 minute) of the video
    max_start_time = total_video_duration - audio_duration - 60  # Changed from 15 to 60 seconds
    min_start_time = 21
    
    if max_start_time <= min_start_time:
        raise ValueError(f"Video is too short for the audio duration. Video length: {total_video_duration}s, Audio length: {audio_duration}s")
    
    start_time = random.uniform(min_start_time, max_start_time)
    print(f"Video segment will start at {start_time:.2f}s and last for {audio_duration:.2f}s")
    
    # Get video dimensions
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-select_streams", "v:0", 
        "-show_entries", "stream=width,height", 
        "-of", "csv=s=x:p=0", 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    width, height = map(int, result.stdout.strip().split('x'))
    
    # Calculate dimensions for 9:16 aspect ratio (portrait mode)
    # We'll crop from the center of the original video
    target_width = height * 9 // 16
    
    # If original video is wider than needed, we'll crop the sides
    # If it's narrower, we'll add black bars
    if width >= target_width:
        # Crop from center
        x_offset = (width - target_width) // 2
        crop_filter = f"crop={target_width}:{height}:{x_offset}:0"
    else:
        # Add padding (black bars) on sides
        pad_width = height * 9 // 16
        x_offset = (pad_width - width) // 2
        crop_filter = f"pad={pad_width}:{height}:{x_offset}:0:black"
    
    # Create a temporary file for the audio (possibly trimmed for test mode)
    temp_audio = "output/temp_audio.mp3"
    
    # If test mode is enabled, trim the audio to 10 seconds
    if test:
        cmd = [
            "ffmpeg",
            "-i", audio_path,
            "-t", "10",
            "-c:a", "copy",
            "-y",
            temp_audio
        ]
        print("Trimming audio to 10 seconds for test mode")
        subprocess.run(cmd)
        audio_path_to_use = temp_audio
    else:
        audio_path_to_use = audio_path
    
    # If we have subtitle data, create a subtitle file
    subtitle_file = None
    if subtitle_data and "dialogue" in subtitle_data:
        subtitle_file = "output/subtitles.srt"
        
        # Create SRT subtitle file with explicit UTF-8 encoding
        with open(subtitle_file, 'w', encoding='utf-8') as f:
            for i, line in enumerate(subtitle_data["dialogue"]):
                # Skip lines that start after our test duration if in test mode
                if test and line["start_time"] >= 10.0:
                    continue
                
                # Calculate end time (cap at test duration if in test mode)
                end_time = min(line["end_time"], 10.0) if test else line["end_time"]
                
                # Skip if the line is completely outside our duration
                if end_time <= 0 or (test and line["start_time"] >= 10.0):
                    continue
                
                # Format timestamps for SRT (HH:MM:SS,mmm)
                start_h = int(line["start_time"] // 3600)
                start_m = int((line["start_time"] % 3600) // 60)
                start_s = int(line["start_time"] % 60)
                start_ms = int((line["start_time"] * 1000) % 1000)
                
                end_h = int(end_time // 3600)
                end_m = int((end_time % 3600) // 60)
                end_s = int(end_time % 60)
                end_ms = int((end_time * 1000) % 1000)
                
                # Get the text and highlight Vietnamese words
                text = line["text"]
                
                # First, convert any <vietnamese> tags to font color tags
                text = re.sub(r'<vietnamese>([^<]+)</vietnamese>', r'<font color="#FFFF00">\1</font>', text)
                
                # If there are Vietnamese words to highlight
                if "viet_words" in line and line["viet_words"]:
                    # Replace Vietnamese words with yellow-colored versions using SRT formatting
                    for viet_word in line["viet_words"]:
                        # Only replace if not already highlighted
                        if f'<font color="#FFFF00">{viet_word}</font>' not in text:
                            text = text.replace(viet_word, f'<font color="#FFFF00">{viet_word}</font>')
                
                # Write SRT entry
                f.write(f"{i+1}\n")
                f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> {end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n")
                f.write(f"{text}\n\n")
        
        print(f"Created subtitle file: {subtitle_file}")
    
    # Check if we have character photos
    michael_photo = "data/photo/michael.png"
    mira_photo = "data/photo/mira.png"
    
    # Optimize the encoding process by combining operations
    print("Generating video with optimized encoding process")
    
    # Prepare character overlay expressions if needed
    character_overlay = ""
    if subtitle_file and os.path.exists(michael_photo) and os.path.exists(mira_photo) and subtitle_data:
        print("Found character photos, preparing overlay expressions")
        
        # Sort dialogue by start time
        sorted_dialogue = sorted(subtitle_data["dialogue"], key=lambda x: x["start_time"])
        
        # Group all segments by speaker to find their total speaking time
        michael_segments = []
        mira_segments = []
        
        for line in sorted_dialogue:
            # Skip lines that start after our test duration if in test mode
            if test and line["start_time"] >= 10.0:
                continue
                
            # Calculate end time (cap at test duration if in test mode)
            end_time = min(line["end_time"], 10.0) if test else line["end_time"]
            
            # Skip if the line is completely outside our duration
            if end_time <= 0 or (test and line["start_time"] >= 10.0):
                continue
            
            if line["speaker"] == "Michael":
                michael_segments.append({
                    "start_time": line["start_time"],
                    "end_time": end_time
                })
            elif line["speaker"] == "Mira":
                mira_segments.append({
                    "start_time": line["start_time"],
                    "end_time": end_time
                })
        
        # Create enable expressions for both characters
        mira_enable = "+".join([f"between(t,{s['start_time']},{s['end_time']})" for s in mira_segments]) if mira_segments else "0"
        michael_enable = "+".join([f"between(t,{s['start_time']},{s['end_time']})" for s in michael_segments]) if michael_segments else "0"
        
        # Create the character overlay part of the filter chain
        character_overlay = (
            f";[1:v]scale=800:-1[mira_scaled];"
            f"[2:v]scale=800:-1[michael_scaled];"
            f"[cropped][mira_scaled]overlay=x=0:y=H-h:enable='{mira_enable}'[with_mira];"
            f"[with_mira][michael_scaled]overlay=x=W-w:y=H-h:enable='{michael_enable}'[with_characters]"
        )
    
    # Build the complete FFmpeg command based on what features are needed
    if subtitle_file and character_overlay:
        # Case 1: Video with character overlays and subtitles
        filter_complex = (
            f"[0:v]{crop_filter}[cropped]{character_overlay};"
            f"[with_characters]subtitles={subtitle_file}:force_style='FontName=Montserrat ExtraBold,FontSize=14,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BackColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=150,Fontsize=24'[v]"
        )
        
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-t", str(audio_duration),
            "-i", video_path,
            "-i", mira_photo,
            "-i", michael_photo,
            "-i", audio_path_to_use,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "3:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            "-y",
            output_path
        ]
    elif subtitle_file:
        # Case 2: Video with subtitles only
        filter_complex = (
            f"[0:v]{crop_filter}[cropped];"
            f"[cropped]subtitles={subtitle_file}:force_style='FontName=Montserrat ExtraBold,FontSize=14,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BackColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=150,Fontsize=24'[v]"
        )
        
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-t", str(audio_duration),
            "-i", video_path,
            "-i", audio_path_to_use,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            "-y",
            output_path
        ]
    else:
        # Case 3: Video without subtitles or character overlays
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-t", str(audio_duration),
            "-i", video_path,
            "-i", audio_path_to_use,
            "-filter_complex", f"[0:v]{crop_filter}[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-shortest",
            "-y",
            output_path
        ]
    
    print(f"Generating video with a single encoding pass: {output_path}")
    subprocess.run(cmd)
    
    # Clean up temporary files
    try:
        if test and os.path.exists(temp_audio):
            os.remove(temp_audio)
        if subtitle_file and os.path.exists(subtitle_file):
            # Comment out to keep subtitle file for inspection
            # os.remove(subtitle_file)
            pass
        print("Temporary files cleaned up")
    except Exception as e:
        print(f"Warning: Could not clean up temporary files: {e}")
    
    print(f"Background video with audio generated successfully: {output_path}")
    
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a background video from Subway Surfers with full audio and subtitles")
    parser.add_argument("--output", type=str, default=None, help="Output path for the video")
    parser.add_argument("--test", action="store_true", help="Generate a 10-second test clip")
    parser.add_argument("--audio", type=str, default=None, help="Specific audio file to use")
    args = parser.parse_args()
    
    generate_background(args.output, args.test, args.audio) 