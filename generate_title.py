import os
import random
import subprocess
import json
import glob
import argparse
import re
import shlex

def get_frame_brightness(video_path):
    """
    Get the average brightness of multiple frames using FFmpeg.
    Returns True if the frame is bright (should use red text), False if dark (should use white text).
    """
    # Get video duration
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        duration = float(result.stdout.strip())
        
        # Select a random position for the title card
        random_time = random.uniform(0, max(0, duration - 0.1))
        print(f"Selected random position at {random_time:.2f}s for title card")
        
        # Analyze the exact 0.1 second clip we'll use
        cmd = [
            "ffmpeg",
            "-ss", str(random_time),
            "-i", video_path,
            "-vf", f"trim=duration=0.1,thumbnail,format=gray",  # Convert to grayscale and get representative frame
            "-frames:v", "1",  # Only need one frame
            "-f", "rawvideo",  # Output raw video data
            "-pix_fmt", "gray",
            "pipe:"
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.stdout:
            # Calculate average brightness from the grayscale frame
            frame_data = result.stdout
            avg_brightness = sum(frame_data) / len(frame_data)  # 0-255 range
            print(f"Average brightness of frame: {avg_brightness:.1f}/255")
            # Use threshold of 100 - if brighter than this, use red text
            return avg_brightness > 160, random_time
        else:
            print("No frame data received!")
            print("FFmpeg stderr output:", result.stderr)
    except Exception as e:
        print(f"Error detecting brightness: {str(e)}")
    
    # Default to white text if detection fails
    return False, 0.0

def verify_video_file(video_path):
    """
    Verify that a video file is not corrupt by using ffprobe.
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
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        return "streams" in data and len(data["streams"]) > 0
    except:
        return False

def sanitize_filename(filename):
    """Sanitize filename by replacing special characters with underscores."""
    # Replace any non-alphanumeric character (except dots) with underscore
    return re.sub(r'[^a-zA-Z0-9.]', '_', filename)

def escape_text(text):
    """Escape text for use in FFmpeg drawtext filter."""
    # First, escape any special characters
    text = text.replace('\\', '\\\\')
    text = text.replace(':', '\\:')
    text = text.replace('\'', '\\\'')
    # Then wrap in quotes
    return f"'{text}'"

def format_title_text(text):
    """Split title text into individual words."""
    # Split into words and filter out empty strings
    return [word.strip() for word in text.split() if word.strip()]

def generate_title_card(dialogue_path, output_path=None):
    """
    Generate a 0.1 second title card video with text from the dialogue JSON file.
    Uses a random subway video background and overlays text in large white letters.
    The video is in portrait mode (9:16 aspect ratio) for TikTok/Reel/YouTube.
    Also includes character overlays (Mira and Michael) with larger sizes.
    
    Args:
        dialogue_path (str): Path to the dialogue JSON file
        output_path (str, optional): Path to save the output video. 
                                   Defaults to 'output/title_[dialogue_id].mp4'
    """
    # Read the dialogue JSON file
    with open(dialogue_path, 'r', encoding='utf-8') as f:
        dialogue_data = json.load(f)
    
    # Get the title text and format it
    title_text = dialogue_data.get("title_card", "")
    if not title_text:
        raise ValueError("No title card text found in dialogue file")
    
    # Format the title text into individual words
    words = format_title_text(title_text)
    
    # Get dialogue ID from filename
    dialogue_id = os.path.splitext(os.path.basename(dialogue_path))[0]
    dialogue_id = sanitize_filename(dialogue_id)
    
    # Set output path if not provided
    if not output_path:
        os.makedirs("output", exist_ok=True)
        output_path = f"output/title_{dialogue_id}.mp4"
    
    # Check for character photos
    michael_photo = "data/photo/michael.png"
    mira_photo = "data/photo/mira.png"
    
    if not os.path.exists(michael_photo) or not os.path.exists(mira_photo):
        print("Warning: Character photos not found, proceeding without character overlays")
        has_characters = False
    else:
        has_characters = True
        # Randomly select which character to show (50/50 chance)
        show_mira = random.choice([True, False])
        print(f"Found character photos, will add {'Mira' if show_mira else 'Michael'} overlay")
    
    # Get all video files from the subway folder
    subway_videos = glob.glob("data/videos/subway/*.mp4")
    if not subway_videos:
        raise ValueError("No video files found in data/videos/subway directory")
    
    # Select a random video
    video_path = random.choice(subway_videos)
    print(f"Selected background video: {video_path}")
    
    # Determine text color based on background brightness and get random time position
    is_bright, start_time = get_frame_brightness(video_path)
    text_color = "red" if is_bright else "white"
    print(f"Background is {'bright' if is_bright else 'dark'}, using {text_color} text")
    
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
    target_width = height * 9 // 16
    print(f"Target width for 9:16 aspect ratio: {target_width}")
    
    # Create the crop/pad filter
    if width >= target_width:
        # Crop from center
        x_offset = (width - target_width) // 2
        print(f"Cropping from center: width={width}, target_width={target_width}, x_offset={x_offset}")
        if height != original_height:
            # If we're downscaling, first scale then crop
            crop_filter = f"scale={width}:{height},crop={target_width}:{height}:{x_offset}:0"
        else:
            # If no downscaling, just crop
            crop_filter = f"crop={target_width}:{height}:{x_offset}:0"
    else:
        # Add padding (black bars) on sides
        pad_width = height * 9 // 16
        x_offset = (pad_width - width) // 2
        print(f"Adding padding: width={width}, pad_width={pad_width}, x_offset={x_offset}")
        if height != original_height:
            # If we're downscaling, first scale then pad
            crop_filter = f"scale={width}:{height},pad={pad_width}:{height}:{x_offset}:0:black"
        else:
            # If no downscaling, just pad
            crop_filter = f"pad={pad_width}:{height}:{x_offset}:0:black"
    
    # Calculate character sizes (50% larger than in background videos)
    if has_characters:
        # Base size is 52.5% of video height (35% * 1.5)
        base_character_width = int(height * 0.525)
        # Add random variation of ±5%
        character_width = int(base_character_width * random.uniform(0.95, 1.05))
        print(f"Character size: {character_width}px")
        
        # Create character overlay filter based on selected character
        character_overlay = (
            f";[1:v]scale={character_width}:-1[char_scaled];"
            f"[cropped][char_scaled]overlay=x={'0' if show_mira else 'W-w'}:y=H-h[with_character]"
        )
    else:
        character_overlay = ""
    
    # Calculate font size based on video width and longest word
    # We want the text to take up about 70% of the video width at most
    max_word_length = max(len(word) for word in words)
    # Estimate font size based on the longest word
    font_size = int((target_width * 0.7) / max_word_length * 2.0)  # Significantly reduced multiplier
    # Ensure font size is reasonable with a smaller range
    font_size = min(max(font_size, 72), 200)  # Much smaller range: 72-200
    print(f"Calculated font size: {font_size}")
    
    # Create a drawtext filter for each word
    line_height = int(font_size * 1.2)  # Increased line spacing slightly for better readability at smaller sizes
    total_height = len(words) * line_height
    start_y = f"(h-{total_height})/2"  # Center all lines vertically
    
    drawtext_filters = []
    for i, word in enumerate(words):
        escaped_word = escape_text(word)
        y_position = f"{start_y}+{i}*{line_height}"  # Position each line vertically
        
        filter_text = (
            f"drawtext=text={escaped_word}:"
            "font='Montserrat ExtraBold':"
            f"fontsize={font_size}:"
            f"fontcolor={text_color}@0.9:"  # Use adaptive text color
            "box=0:"
            f"x=(w-tw)/2:"  # Center horizontally
            f"y={y_position}:"  # Position vertically
            "expansion=normal:"  # Proper UTF-8 handling for Vietnamese
            "alpha=1:"  # Full opacity for sharper text
            "fix_bounds=1:"  # Ensure text stays within bounds
            f"fontcolor_expr={text_color}"  # Use adaptive text color
        )
        drawtext_filters.append(filter_text)
    
    # Join all drawtext filters with commas
    drawtext_filter = ','.join(drawtext_filters)
    
    # Build the FFmpeg command
    if has_characters:
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-i", mira_photo if show_mira else michael_photo,  # Only load the selected character's photo
            "-t", "0.1",
            "-filter_complex",
            f"{crop_filter}[cropped]{character_overlay};[with_character]{drawtext_filter}[v]",
            "-map", "[v]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg",
            "-ss", str(start_time),
            "-i", video_path,
            "-t", "0.1",
            "-vf", f"{crop_filter},{drawtext_filter}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-y",
            output_path
        ]
    
    print(f"Generating title card video: {output_path}")
    print(f"Using text: {title_text}")
    print(f"Using filter: {drawtext_filter}")
    
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
        
        if result.returncode != 0:
            print(f"Error generating title card: {result.stderr}")
            return None
        
        # Verify the generated video
        if verify_video_file(output_path):
            print(f"Title card video generated successfully: {output_path}")
            return output_path
        else:
            print("Generated video appears to be corrupt")
            return None
            
    except Exception as e:
        print(f"Error running FFmpeg: {str(e)}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a title card video from dialogue JSON")
    parser.add_argument("dialogue_path", type=str, help="Path to the dialogue JSON file")
    parser.add_argument("--output", type=str, default=None, help="Output path for the video")
    args = parser.parse_args()
    
    generate_title_card(args.dialogue_path, args.output) 