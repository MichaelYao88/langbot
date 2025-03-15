import os
import random
import subprocess
import argparse
import glob
import json
from pathlib import Path
import re
from remove_punctuation import remove_punctuation_from_dialogue

def verify_video_file(video_path):
    """
    Verify that a video file is not corrupt by using ffprobe.
    
    Args:
        video_path: Path to the video file to verify
        
    Returns:
        bool: True if the video is valid, False otherwise
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_type",
        "-of", "json",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # If ffprobe returns an error, the video is likely corrupt
        if result.returncode != 0:
            print(f"Video verification failed: {result.stderr}")
            return False
        
        # Check if we can extract stream information
        try:
            data = json.loads(result.stdout)
            if "streams" in data and len(data["streams"]) > 0:
                print(f"Video file verified successfully: {video_path}")
                return True
            else:
                print(f"Video file has no valid streams: {video_path}")
                return False
        except json.JSONDecodeError:
            print(f"Could not parse ffprobe output: {result.stdout}")
            return False
            
    except Exception as e:
        print(f"Error verifying video file: {str(e)}")
        return False

def cleanup_associated_files(dialogue_id, audio_path):
    """
    Clean up JSON and CSV files associated with a dialogue ID after a background video is generated.
    
    Args:
        dialogue_id: The dialogue ID to clean up files for
        audio_path: The path to the audio file used for the video
    """
    print(f"\nCleaning up associated files for dialogue ID: {dialogue_id}")
    
    # Define patterns for files to clean up - EXCLUDING JSON files
    patterns = [
        # Removed JSON patterns to preserve them
        # f"dialogue_{dialogue_id}.json",
        # f"dialogue_{dialogue_id}_auto.json",
        # f"dialogue_{dialogue_id}_adjusted.json",
        # f"dialogue_{dialogue_id}_no_punctuation.json",
        # f"dialogue_{dialogue_id}_original.json",
        # f"word_timestamps_{dialogue_id}.json",
        f"word_timestamps_{dialogue_id}.csv"
    ]
    
    # Get the directory of the audio file
    audio_dir = os.path.dirname(audio_path)
    
    # Count how many files were deleted
    deleted_count = 0
    
    # Delete each file if it exists
    for pattern in patterns:
        file_path = os.path.join(audio_dir, pattern)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"Deleted: {file_path}")
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    
    if deleted_count > 0:
        print(f"Successfully cleaned up {deleted_count} files for dialogue ID: {dialogue_id}")
    else:
        print(f"No files found to clean up for dialogue ID: {dialogue_id}")
    
    print(f"JSON files were preserved for dialogue ID: {dialogue_id}")

def generate_random_color_shift():
    """
    Generate random color shift parameters for hue, saturation, and brightness.
    
    Returns:
        tuple: (hue_shift, saturation_shift, brightness_shift) values for FFmpeg colorchannelmixer filter
    """
    # Generate random shift percentage between -7% and +7%
    shift_percent = random.uniform(-0.07, 0.07)
    
    # For hue, we'll use the eq filter with a value between 0.93 and 1.07
    # For saturation and brightness, we'll use values between 0.93 and 1.07
    hue_shift = 1.0 + shift_percent
    saturation_shift = 1.0 + shift_percent
    brightness_shift = 1.0 + shift_percent
    
    # Randomize the direction of each parameter independently for more variety
    if random.choice([True, False]):
        hue_shift = 2.0 - hue_shift  # Invert the hue shift direction
    
    if random.choice([True, False]):
        saturation_shift = 2.0 - saturation_shift  # Invert the saturation shift direction
    
    print(f"Applying color shift - Hue: {hue_shift:.3f}, Saturation: {saturation_shift:.3f}, Brightness: {brightness_shift:.3f}")
    
    return hue_shift, saturation_shift, brightness_shift

def get_color_shift_filter(hue, saturation, brightness):
    """
    Create an FFmpeg filter string for color shifting.
    
    Args:
        hue: Hue shift value (0.93-1.07)
        saturation: Saturation multiplier (0.93-1.07)
        brightness: Brightness multiplier (0.93-1.07)
        
    Returns:
        str: FFmpeg filter string for color shifting
    """
    # Use hue and saturation adjustments
    # For hue, we use the hue filter which takes degrees (0-360)
    # Convert our 0.93-1.07 range to a small degree shift (-25 to +25 degrees)
    hue_degrees = (hue - 1.0) * 360  # This gives us roughly -25 to +25 degrees
    
    # For saturation, we use the eq filter
    # For brightness, we use the eq filter
    return f"hue=h={hue_degrees:.2f}:s={saturation:.3f},eq=brightness={brightness-1:.3f}"

def generate_background(output_path=None, test=False, audio_path=None, simple=False, cleanup=True, cleanup_json=False):
    """
    Generate a background video from Subway Surfers with audio.
    The video length will match the full duration of a randomly selected audio file.
    The segment will be at least 340 seconds after start and 60 seconds from the end.
    The output will be in portrait mode (9:16 aspect ratio) for TikTok/Reel/YouTube.
    Subtitles will be added using the timestamps from the corresponding JSON file.
    Character photos will be displayed when they are speaking.
    
    Args:
        output_path (str, optional): Path to save the output video. Defaults to 'output/[topic_word]_[dialogue_id].mp4'.
        test (bool, optional): If True, generate a 10-second test clip. Defaults to False.
        audio_path (str, optional): Path to a specific audio file to use. If None, a random unprocessed file is selected.
        simple (bool, optional): If True, use a simplified FFmpeg command. Defaults to False.
        cleanup (bool, optional): If True, clean up associated CSV files after successful generation. Defaults to True.
        cleanup_json (bool, optional): If True, clean up JSON files as well. Defaults to False.
    """
    # Define paths
    # Get all video files from the subway folder
    subway_videos = glob.glob("data/videos/subway/*.mp4")
    if not subway_videos:
        raise ValueError("No video files found in data/videos/subway directory")

    # Select a random video from the subway folder
    video_path = random.choice(subway_videos)
    print(f"Selected background video: {video_path}")
    
    # If audio_path is not provided, find an unprocessed audio file
    if audio_path is None:
        # Get all audio files
        audio_files = glob.glob("data/audio/*.mp3")
        if not audio_files:
            raise ValueError("No audio files found in data/audio directory")
        
        # Get all existing video files
        video_files = glob.glob("output/*.mp4")
        processed_ids = set()
        
        # Extract dialogue IDs from existing video files
        for video_file in video_files:
            # Extract the dialogue ID from the filename (last part before .mp4)
            filename = os.path.basename(video_file)
            parts = filename.split('_')
            if len(parts) > 1:
                dialogue_id = parts[-1].replace('.mp4', '')
                processed_ids.add(dialogue_id)
        
        # Find unprocessed audio files that have corresponding JSON files
        unprocessed_files = []
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
            
            # Determine which pattern matched
            if old_pattern_match:
                dialogue_id = old_pattern_match.group(1)
            elif new_pattern_without_topic_match:
                dialogue_id = new_pattern_without_topic_match.group(1)
            elif new_pattern_with_topic_match:
                dialogue_id = new_pattern_with_topic_match.group(1)
            else:
                continue  # Skip files that don't match any pattern
            
            # Check if this dialogue has already been processed
            if dialogue_id in processed_ids:
                continue
            
            # Check if a corresponding JSON file exists
            json_path = os.path.join(os.path.dirname(audio_file), f"dialogue_{dialogue_id}.json")
            if not os.path.exists(json_path):
                print(f"Skipping {audio_file} - no corresponding JSON file found")
                continue
                
            # This audio file has a JSON file and hasn't been processed yet
            unprocessed_files.append(audio_file)
        
        if not unprocessed_files:
            raise ValueError("No unprocessed audio files with corresponding JSON files found. All eligible files have already been processed.")
        
        # Select a random unprocessed audio file
        audio_path = random.choice(unprocessed_files)
    
    print(f"Selected audio file: {audio_path}")
    
    # Get the dialogue ID from the audio filename
    audio_filename = os.path.basename(audio_path)
    
    # Try different filename patterns
    # Old pattern: dialogue_ID_elevenlabs_slow.mp3
    old_pattern_match = re.match(r'dialogue_([a-f0-9]+)_elevenlabs_slow\.mp3', audio_filename)
    
    # New pattern without topic word: dialogue_ID.mp3
    new_pattern_without_topic_match = re.match(r'dialogue_([a-f0-9]+)\.mp3', audio_filename)
    
    # New pattern with topic word: topic_word_ID.mp3
    new_pattern_with_topic_match = re.match(r'.*_([a-f0-9]+)\.mp3', audio_filename)
    
    # Determine which pattern matched
    if old_pattern_match:
        dialogue_id = old_pattern_match.group(1)
    elif new_pattern_without_topic_match:
        dialogue_id = new_pattern_without_topic_match.group(1)
    elif new_pattern_with_topic_match:
        dialogue_id = new_pattern_with_topic_match.group(1)
    else:
        raise ValueError(f"Could not extract dialogue ID from filename: {audio_filename}")
    
    # Check if a video for this dialogue ID already exists in the output directory
    existing_videos = glob.glob(f"output/*_{dialogue_id}.mp4") + glob.glob(f"output/dialogue_{dialogue_id}.mp4")
    if existing_videos and not test:
        raise ValueError(f"A video for dialogue ID {dialogue_id} already exists: {existing_videos[0]}. Use --test to generate a test clip anyway.")
    
    # Look for the corresponding JSON file with timestamps
    original_json_path = os.path.join(os.path.dirname(audio_path), f"dialogue_{dialogue_id}.json")
    auto_json_path = os.path.join(os.path.dirname(audio_path), f"dialogue_{dialogue_id}_auto.json")
    
    # Use the best available timestamp file
    if os.path.exists(original_json_path):
        json_path = original_json_path
        print(f"Using timestamps from {json_path}")
    elif os.path.exists(auto_json_path):
        json_path = auto_json_path
        print(f"Using auto-generated timestamps from {json_path}")
    else:
        raise ValueError(f"No timestamp JSON file found for dialogue ID {dialogue_id}. Cannot generate video without subtitles.")
    
    # Load the JSON file to make sure it has dialogue entries
    with open(json_path, 'r', encoding='utf-8') as f:
        subtitle_data = json.load(f)
        
    if not subtitle_data or "dialogue" not in subtitle_data or not subtitle_data["dialogue"]:
        raise ValueError(f"The JSON file {json_path} does not contain any dialogue entries. Cannot generate video.")
        
    topic_word = subtitle_data.get("topic_word", "")
    
    # Process the JSON file to remove punctuation if it exists
    no_punctuation_json_path = json_path.replace('.json', '_no_punctuation.json')
    
    # Check if the no-punctuation version already exists, if not create it
    # Commenting out the no-punctuation code to use the original JSON file with small phrases
    # if not os.path.exists(no_punctuation_json_path):
    #     print(f"Removing punctuation from {json_path}")
    #     remove_punctuation_from_dialogue(json_path)
    
    # Use the no-punctuation version if it exists, otherwise fall back to the original
    # if os.path.exists(no_punctuation_json_path):
    #     with open(no_punctuation_json_path, 'r', encoding='utf-8') as f:
    #         subtitle_data = json.load(f)
    #         print(f"Loaded subtitle data without punctuation from {no_punctuation_json_path}")
    #         topic_word = subtitle_data.get("topic_word", "")
    # else:
    #     with open(json_path, 'r', encoding='utf-8') as f:
    #         subtitle_data = json.load(f)
    #         print(f"Loaded subtitle data from {json_path}")
    #         topic_word = subtitle_data.get("topic_word", "")
    
    # Set the output path based on the dialogue ID and topic word if not provided
    if output_path is None:
        if topic_word:
            output_path = f"output/{topic_word}_{dialogue_id}.mp4"
        else:
            output_path = f"output/dialogue_{dialogue_id}.mp4"
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
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
    
    # Calculate start time ensuring we have enough duration for the audio
    max_start_time = total_video_duration - audio_duration
    min_start_time = 0  # No restriction on start time

    # Check if the video is long enough for the audio
    if max_start_time <= min_start_time:
        print(f"Video is shorter than audio duration. Video length: {total_video_duration:.2f}s, Audio length: {audio_duration:.2f}s")
        print("Will loop the video to cover the entire audio duration")
        
        # We'll handle looping in the filter complex
        needs_looping = True
        start_time = random.uniform(0, total_video_duration)
        print(f"Starting at random point {start_time:.2f}s and looping as needed")
    else:
        needs_looping = False
        start_time = random.uniform(min_start_time, max_start_time)
        print(f"Video segment will start at {start_time:.2f}s and last for {audio_duration:.2f}s (using full video range)")
    
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
    original_width, original_height = map(int, result.stdout.strip().split('x'))
    print(f"Original video dimensions: {original_width}x{original_height}")
    
    # Store original dimensions for reference
    width = original_width
    height = original_height
    
    # Downscale to 720p if the video is higher resolution
    if height > 720:
        print(f"Downscaling video from {width}x{height} to 720p for better performance")
        # Calculate new width maintaining aspect ratio
        width = int((width / height) * 720)
        height = 720
        print(f"Downscaled dimensions: {width}x{height}")

    # Calculate dimensions for 9:16 aspect ratio (portrait mode)
    # We'll crop from the center of the original video
    target_width = height * 9 // 16
    print(f"Target width for 9:16 aspect ratio: {target_width}")
    
    # Generate random color shift parameters
    hue_shift, saturation_shift, brightness_shift = generate_random_color_shift()
    color_shift_filter = get_color_shift_filter(hue_shift, saturation_shift, brightness_shift)
    
    # If original video is wider than needed, we'll crop the sides
    # If it's narrower, we'll add black bars
    if width >= target_width:
        # Crop from center - ensure we're taking the exact center
        x_offset = (width - target_width) // 2
        print(f"Cropping from center: width={width}, target_width={target_width}, x_offset={x_offset}")
        print(f"Final crop dimensions will be: {target_width}x{height} starting at x={x_offset}, y=0")
        
        # First scale the video if needed, then crop from center
        if height != original_height:
            # If we're downscaling, first scale then crop
            base_crop_filter = f"scale={width}:{height},crop={target_width}:{height}:{x_offset}:0"
            print(f"Using scale-then-crop approach for downscaled video")
        else:
            # If no downscaling, just crop
            base_crop_filter = f"crop={target_width}:{height}:{x_offset}:0"
    else:
        # Add padding (black bars) on sides
        pad_width = height * 9 // 16
        x_offset = (pad_width - width) // 2
        print(f"Adding padding: width={width}, pad_width={pad_width}, x_offset={x_offset}")
        print(f"Final padded dimensions will be: {pad_width}x{height} with padding of {x_offset} pixels on each side")
        
        # First scale the video if needed, then add padding
        if height != original_height:
            # If we're downscaling, first scale then pad
            base_crop_filter = f"scale={width}:{height},pad={pad_width}:{height}:{x_offset}:0:black"
            print(f"Using scale-then-pad approach for downscaled video")
        else:
            # If no downscaling, just pad
            base_crop_filter = f"pad={pad_width}:{height}:{x_offset}:0:black"

    # If we need looping, modify the filter to handle it
    if needs_looping:
        # Calculate how many times we need to loop the video
        loop_count = int(audio_duration / total_video_duration) + 1
        # Calculate the exact number of loops needed to cover the audio duration
        exact_loops_needed = audio_duration / total_video_duration
        print(f"Video will be looped {loop_count} times to cover audio duration")
        print(f"Exact loops needed: {exact_loops_needed:.2f} (audio: {audio_duration:.2f}s / video: {total_video_duration:.2f}s)")
        
        # For looping, we'll use the 'loop' filter with better parameters
        # loop=count:size:start - count is number of loops, size is number of frames to loop, start is the first frame to loop
        # -1 for count means loop indefinitely, 0 for size means all frames
        # We'll use -1 for count and let the -shortest option handle the duration
        loop_filter = f"loop=-1:0:0"
        
        # The loop filter must be applied first, before any other filters
        if height != original_height:
            # If we're downscaling, we need to: loop -> scale -> crop/pad -> color shift
            if width >= target_width:
                # Loop -> scale -> crop -> color shift
                base_crop_filter = f"{loop_filter},scale={width}:{height},crop={target_width}:{height}:{x_offset}:0"
            else:
                # Loop -> scale -> pad -> color shift
                base_crop_filter = f"{loop_filter},scale={width}:{height},pad={pad_width}:{height}:{x_offset}:0:black"
        else:
            # If no downscaling, we need to: loop -> crop/pad -> color shift
            if width >= target_width:
                # Loop -> crop -> color shift
                base_crop_filter = f"{loop_filter},crop={target_width}:{height}:{x_offset}:0"
            else:
                # Loop -> pad -> color shift
                base_crop_filter = f"{loop_filter},pad={pad_width}:{height}:{x_offset}:0:black"
        
        # Add color shift to the base crop filter
        crop_filter = f"{base_crop_filter},{color_shift_filter}"
        print(f"Using infinite loop filter chain with -shortest option: {crop_filter}")
    else:
        # Add color shift to the base crop filter
        crop_filter = f"{base_crop_filter},{color_shift_filter}"

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
    if "dialogue" in subtitle_data:
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
    else:
        print(f"Warning: No dialogue entries found in the JSON file. Subtitles will not be added.")
    
    # Check if we have character photos
    michael_photo = "data/photo/michael.png"
    mira_photo = "data/photo/mira.png"
    
    # Optimize the encoding process by combining operations
    print("Generating video with optimized encoding process")
    
    # Prepare character overlay expressions if needed
    character_overlay = ""
    if subtitle_file and os.path.exists(michael_photo) and os.path.exists(mira_photo):
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
        
        # Sort segments by start time
        michael_segments.sort(key=lambda x: x["start_time"])
        mira_segments.sort(key=lambda x: x["start_time"])
        
        # Create continuous visibility segments for each character
        # A character should be visible from when they start speaking until the other character starts speaking
        michael_visibility = []
        mira_visibility = []
        
        # Initialize with empty lists if no segments
        if not michael_segments and not mira_segments:
            # No characters speaking
            pass
        elif not michael_segments:
            # Only Mira speaks
            mira_start = mira_segments[0]["start_time"]
            mira_end = mira_segments[-1]["end_time"]
            mira_visibility.append({"start_time": mira_start, "end_time": mira_end})
        elif not mira_segments:
            # Only Michael speaks
            michael_start = michael_segments[0]["start_time"]
            michael_end = michael_segments[-1]["end_time"]
            michael_visibility.append({"start_time": michael_start, "end_time": michael_end})
        else:
            # Both characters speak - create interleaved visibility segments
            
            # Combine all segments and sort by start time
            all_segments = []
            for segment in michael_segments:
                all_segments.append({"speaker": "Michael", "time": segment["start_time"], "type": "start"})
                all_segments.append({"speaker": "Michael", "time": segment["end_time"], "type": "end"})
            for segment in mira_segments:
                all_segments.append({"speaker": "Mira", "time": segment["start_time"], "type": "start"})
                all_segments.append({"speaker": "Mira", "time": segment["end_time"], "type": "end"})
            
            all_segments.sort(key=lambda x: x["time"])
            
            # Track which character is currently visible
            michael_visible = False
            mira_visible = False
            michael_current_start = None
            mira_current_start = None
            
            # Process events in time order
            for event in all_segments:
                if event["speaker"] == "Michael":
                    if event["type"] == "start":
                        # Michael starts speaking
                        michael_visible = True
                        if michael_current_start is None:
                            michael_current_start = event["time"]
                        
                        # If Mira was visible, end her visibility
                        if mira_visible and mira_current_start is not None:
                            mira_visibility.append({"start_time": mira_current_start, "end_time": event["time"]})
                            mira_visible = False
                            mira_current_start = None
                    
                    # We don't end Michael's visibility when he stops speaking
                    # It will end when Mira starts speaking
                
                elif event["speaker"] == "Mira":
                    if event["type"] == "start":
                        # Mira starts speaking
                        mira_visible = True
                        if mira_current_start is None:
                            mira_current_start = event["time"]
                        
                        # If Michael was visible, end his visibility
                        if michael_visible and michael_current_start is not None:
                            michael_visibility.append({"start_time": michael_current_start, "end_time": event["time"]})
                            michael_visible = False
                            michael_current_start = None
                    
                    # We don't end Mira's visibility when she stops speaking
                    # It will end when Michael starts speaking
            
            # Add final visibility segments if characters were still visible at the end
            if michael_visible and michael_current_start is not None:
                michael_visibility.append({"start_time": michael_current_start, "end_time": audio_duration})
            
            if mira_visible and mira_current_start is not None:
                mira_visibility.append({"start_time": mira_current_start, "end_time": audio_duration})
        
        # Create enable expressions for both characters based on visibility segments
        mira_enable = "+".join([f"between(t,{s['start_time']},{s['end_time']})" for s in mira_visibility]) if mira_visibility else "0"
        michael_enable = "+".join([f"between(t,{s['start_time']},{s['end_time']})" for s in michael_visibility]) if michael_visibility else "0"
        
        # Calculate base character size based on video height (approximately 35% of the video height - reduced from 40%)
        base_character_width = int(height * 0.35)  # Reduced by ~15% from original 0.4

        # Add random variation of ±5% to each character's width
        mira_width = int(base_character_width * random.uniform(0.95, 1.05))
        michael_width = int(base_character_width * random.uniform(0.95, 1.05))

        print(f"Base character width: {base_character_width}px (35% of video height: {height}px)")
        print(f"Mira width with variation: {mira_width}px")
        print(f"Michael width with variation: {michael_width}px")

        # Create the character overlay part of the filter chain
        character_overlay = (
            f";[1:v]scale={mira_width}:-1[mira_scaled];"
            f"[2:v]scale={michael_width}:-1[michael_scaled];"
            f"[cropped][mira_scaled]overlay=x=0:y=H-h:enable='{mira_enable}'[with_mira];"
            f"[with_mira][michael_scaled]overlay=x=W-w:y=H-h:enable='{michael_enable}'[with_characters]"
        )
    
    # Build the complete FFmpeg command based on what features are needed
    if subtitle_file and character_overlay:
        # Case 1: Video with character overlays and subtitles
        # Split the complex filter into multiple steps to reduce complexity
        print("Generating video with optimized encoding process - characters and subtitles")
        
        # Step 1: Crop the video and add character overlays
        temp_video_with_chars = "output/temp_video_with_chars.mp4"

        # Adjust the input parameters based on whether we need looping
        if needs_looping:
            # When looping, we need to handle the start time differently
            # We'll use the trim filter to start at the correct position before looping
            input_params = ["-i", video_path]
            
            # Modify the filter to include trimming at the start
            if start_time > 0:
                print(f"Adding trim filter to start at {start_time:.2f}s before looping")
                # Insert trim filter at the beginning of the filter chain
                filter_complex_chars = (
                    f"[0:v]trim=start={start_time},setpts=PTS-STARTPTS,{crop_filter}[cropped]{character_overlay}"
                )
            else:
                filter_complex_chars = (
                    f"[0:v]{crop_filter}[cropped]{character_overlay}"
                )
        else:
            # When not looping, use normal seeking
            input_params = ["-ss", str(start_time), "-t", str(audio_duration), "-i", video_path]
            filter_complex_chars = (
                f"[0:v]{crop_filter}[cropped]{character_overlay}"
            )

        cmd_chars = [
            "ffmpeg",
        ] + input_params + [
            "-i", mira_photo,
            "-i", michael_photo,
            "-filter_complex", filter_complex_chars,
            "-map", "[with_characters]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",
            temp_video_with_chars
        ]
        
        print("Step 1: Creating video with character overlays")
        result_chars = subprocess.run(cmd_chars, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result_chars.returncode != 0:
            print(f"Error in step 1: {result_chars.stderr}")
            print("Falling back to simpler approach without character overlays")
            # Fall back to subtitle-only approach
            subtitle_file_exists = True
            character_overlay = None
        else:
            # Step 2: Add subtitles and audio
            cmd = [
                "ffmpeg",
                "-i", temp_video_with_chars,
                "-i", audio_path_to_use,
                "-vf", f"subtitles={subtitle_file}:force_style='FontName=Montserrat ExtraBold,FontSize=14,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BackColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=150'",
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                "-y",
                output_path
            ]
            
            print("Step 2: Adding subtitles and audio to final video")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Clean up temporary file
            if os.path.exists(temp_video_with_chars):
                try:
                    os.remove(temp_video_with_chars)
                except:
                    pass
            
            if result.returncode != 0:
                print(f"Error in step 2: {result.stderr}")
                print("Falling back to simpler approach")
                # Fall back to subtitle-only approach
                subtitle_file_exists = True
                character_overlay = None
            else:
                # Successfully created video with both characters and subtitles
                if verify_video_file(output_path):
                    print(f"Successfully generated video with characters and subtitles: {output_path}")
                    # Clean up associated JSON and CSV files if requested
                    if cleanup:
                        cleanup_associated_files(dialogue_id, audio_path)
                    return output_path
                else:
                    print("Generated video is corrupt, trying simpler approach")
                    # Fall back to subtitle-only approach
                    subtitle_file_exists = True
                    character_overlay = None
    
    if subtitle_file and not character_overlay:
        # Case 2: Video with subtitles only
        print("Generating video with subtitles only")
        
        # Use a simpler approach with separate steps
        # Step 1: Create video with crop filter
        temp_video_cropped = "output/temp_video_cropped.mp4"

        # Adjust the input parameters based on whether we need looping
        if needs_looping:
            # When looping, we need to handle the start time differently
            # We'll use the trim filter to start at the correct position before looping
            input_params = ["-i", video_path]
            
            # Modify the filter to include trimming at the start
            if start_time > 0:
                print(f"Adding trim filter to start at {start_time:.2f}s before looping")
                # Insert trim filter at the beginning of the filter chain
                vf_filter = f"trim=start={start_time},setpts=PTS-STARTPTS,{crop_filter}"
            else:
                vf_filter = crop_filter
        else:
            # When not looping, use normal seeking
            input_params = ["-ss", str(start_time), "-t", str(audio_duration), "-i", video_path]
            vf_filter = crop_filter

        cmd_crop = [
            "ffmpeg",
        ] + input_params + [
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",
            temp_video_cropped
        ]
        
        print("Step 1: Creating cropped video")
        result_crop = subprocess.run(cmd_crop, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result_crop.returncode != 0:
            print(f"Error in step 1: {result_crop.stderr}")
            print("Falling back to very simple approach")
            # Fall back to no-subtitle approach
            subtitle_file = None
        else:
            # Step 2: Add subtitles and audio
            cmd = [
                "ffmpeg",
                "-i", temp_video_cropped,
                "-i", audio_path_to_use,
                "-vf", f"subtitles={subtitle_file}:force_style='FontName=Montserrat ExtraBold,FontSize=14,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,BackColour=&H000000,BorderStyle=1,Outline=1,Shadow=0,MarginV=150'",
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                "-y",
                output_path
            ]
            
            print("Step 2: Adding subtitles and audio to final video")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Clean up temporary file
            if os.path.exists(temp_video_cropped):
                try:
                    os.remove(temp_video_cropped)
                except:
                    pass
            
            if result.returncode != 0:
                print(f"Error in step 2: {result.stderr}")
                print("Falling back to very simple approach")
                # Fall back to no-subtitle approach
                subtitle_file = None
            else:
                # Successfully created video with subtitles
                if verify_video_file(output_path):
                    print(f"Successfully generated video with subtitles: {output_path}")
                    # Clean up associated JSON and CSV files if requested
                    if cleanup:
                        cleanup_associated_files(dialogue_id, audio_path)
                    return output_path
                else:
                    print("Generated video is corrupt, trying simplest approach")
                    # Fall back to no-subtitle approach
                    subtitle_file = None
    
    if not subtitle_file:
        # Case 3: Video without subtitles or character overlays (simplest approach)
        print("Generating video with simplest approach - no subtitles or characters")

        # Adjust the input parameters based on whether we need looping
        if needs_looping:
            # When looping, we need to handle the start time differently
            # We'll use the trim filter to start at the correct position before looping
            input_params = ["-i", video_path]
            
            # Modify the filter to include trimming at the start
            if start_time > 0:
                print(f"Adding trim filter to start at {start_time:.2f}s before looping")
                # Insert trim filter at the beginning of the filter chain
                crop_filter = f"trim=start={start_time},setpts=PTS-STARTPTS,{crop_filter}"
        else:
            # When not looping, use normal seeking
            input_params = ["-ss", str(start_time), "-t", str(audio_duration), "-i", video_path]

        cmd = [
            "ffmpeg",
        ] + input_params + [
            "-i", audio_path_to_use,
            "-vf", crop_filter,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            "-y",
            output_path
        ]

        print(f"Generating basic video: {output_path}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"Error generating basic video: {result.stderr}")
            print("Trying ultra-simple approach...")
            
            # Try one last approach with very basic settings
            print("Trying one final encoding approach with basic settings...")

            # Create a simplified filter for the fallback approach
            if needs_looping:
                # Use the same infinite loop filter as the main approach
                simple_filter = f"loop=-1:0:0"
                if start_time > 0:
                    simple_filter = f"trim=start={start_time},setpts=PTS-STARTPTS,{simple_filter}"
            else:
                simple_filter = "null" # Null filter that does nothing

            basic_cmd = [
                "ffmpeg",
            ] + input_params + [
                "-i", audio_path_to_use,
                "-vf", simple_filter,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                "-shortest",
                "-y",
                output_path
            ]
            
            subprocess.run(basic_cmd)
    
    # Verify the generated video file
    if os.path.exists(output_path):
        if verify_video_file(output_path):
            print(f"Background video with audio generated successfully: {output_path}")
            # Clean up associated JSON and CSV files if requested
            if cleanup:
                cleanup_associated_files(dialogue_id, audio_path)
        else:
            print(f"Generated video file appears to be corrupt: {output_path}")
            
            # Try one last approach with very basic settings
            print("Trying one final encoding approach with basic settings...")

            # Create a simplified filter for the fallback approach
            if needs_looping:
                # Use the same infinite loop filter as the main approach
                simple_filter = f"loop=-1:0:0"
                if start_time > 0:
                    simple_filter = f"trim=start={start_time},setpts=PTS-STARTPTS,{simple_filter}"
                input_params = ["-i", video_path]
            else:
                simple_filter = "null" # Null filter that does nothing
                input_params = ["-ss", str(start_time), "-t", str(audio_duration), "-i", video_path]

            basic_cmd = [
                "ffmpeg",
            ] + input_params + [
                "-i", audio_path_to_use,
                "-vf", simple_filter,
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "28",
                "-c:a", "aac",
                "-shortest",
                "-y",
                output_path
            ]
            
            subprocess.run(basic_cmd)
            
            if verify_video_file(output_path):
                print(f"Basic video encoding successful: {output_path}")
                # Clean up associated JSON and CSV files if requested
                if cleanup:
                    cleanup_associated_files(dialogue_id, audio_path)
            else:
                print(f"All encoding attempts failed. Video may still be corrupt.")
    else:
        print(f"Output file was not created: {output_path}")
    
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
    
    return output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a background video from Subway Surfers with full audio and subtitles")
    parser.add_argument("--output", type=str, default=None, help="Output path for the video")
    parser.add_argument("--test", action="store_true", help="Generate a 10-second test clip")
    parser.add_argument("--audio", type=str, default=None, help="Specific audio file to use")
    parser.add_argument("--video", type=str, default=None, help="Specific background video file to use")
    parser.add_argument("--simple", action="store_true", help="Use simplified FFmpeg command")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up associated files")
    parser.add_argument("--cleanup-json", action="store_true", help="Clean up JSON files (by default they are preserved)")
    args = parser.parse_args()
    
    # If test mode is enabled, disable cleanup by default
    cleanup = not args.no_cleanup
    if args.test:
        cleanup = False
        print("Test mode enabled - cleanup disabled to preserve JSON files")
    
    # Modify the function to accept a specific video file
    if args.video:
        # Save the original function
        original_glob = glob.glob
        
        # Mock the glob.glob function to return only the specified video
        def mock_glob(pattern):
            if pattern == "data/videos/subway/*.mp4":
                return [args.video]
            return original_glob(pattern)
        
        # Replace glob.glob with our mock version
        glob.glob = mock_glob
        
        print(f"Using specified background video: {args.video}")
    
    generate_background(args.output, args.test, args.audio, args.simple, cleanup, args.cleanup_json) 