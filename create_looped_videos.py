import os
import subprocess
import glob
import tempfile
import argparse

def get_video_duration(video_path):
    """Get the duration of a video file in seconds using ffprobe."""
    cmd = [
        "ffprobe", 
        "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Error getting duration for {video_path}: {result.stderr}")
        return None
    
    try:
        return float(result.stdout.strip())
    except ValueError:
        print(f"Could not parse duration for {video_path}: {result.stdout}")
        return None

def create_looped_video(video_path, output_path, target_duration=90):
    """Create a looped version of the video that is at least target_duration seconds long."""
    # Get the original duration
    original_duration = get_video_duration(video_path)
    if original_duration is None:
        print(f"Skipping {video_path} due to duration detection failure")
        return False
    
    # Calculate how many times we need to loop the video
    loop_count = int(target_duration / original_duration) + 1
    print(f"Video: {video_path}")
    print(f"  Original duration: {original_duration:.2f} seconds")
    print(f"  Target duration: {target_duration:.2f} seconds")
    print(f"  Will loop {loop_count} times")
    
    # Create a temporary file with the list of videos to concatenate
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
        for _ in range(loop_count):
            temp_file.write(f"file '{os.path.abspath(video_path)}'\n")
        temp_file_path = temp_file.name
    
    try:
        # Use the concat demuxer to create the looped video
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", temp_file_path,
            "-c", "copy",
            "-t", str(target_duration),
            "-y",  # Overwrite output file if it exists
            output_path
        ]
        
        print(f"  Creating looped video: {output_path}")
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"  Error creating looped video: {result.stderr}")
            return False
        
        # Verify the new duration
        new_duration = get_video_duration(output_path)
        if new_duration is None:
            print(f"  Failed to verify duration of output video")
            return False
        
        print(f"  Successfully created looped video with duration: {new_duration:.2f} seconds")
        return True
    
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def main():
    parser = argparse.ArgumentParser(description="Create looped versions of videos that are shorter than a specified duration")
    parser.add_argument("--source_dir", type=str, default="data/videos/subway", help="Directory containing source videos")
    parser.add_argument("--output_dir", type=str, default="data/videos/subway_looped", help="Directory to save looped videos")
    parser.add_argument("--min_duration", type=float, default=89, help="Minimum duration threshold in seconds")
    parser.add_argument("--target_duration", type=float, default=90, help="Target duration for looped videos in seconds")
    parser.add_argument("--force", action="store_true", help="Force recreation of looped videos even if they already exist")
    parser.add_argument("--list_only", action="store_true", help="Only list video durations without creating looped versions")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Get all video files from the source directory
    video_files = glob.glob(os.path.join(args.source_dir, "*.mp4"))
    if not video_files:
        print(f"No video files found in {args.source_dir}")
        return
    
    print(f"Found {len(video_files)} video files in {args.source_dir}")
    
    # Process each video
    short_videos = []
    all_videos = []
    
    for video_path in video_files:
        duration = get_video_duration(video_path)
        if duration is None:
            continue
        
        filename = os.path.basename(video_path)
        all_videos.append((filename, duration))
        
        if duration < args.min_duration:
            short_videos.append((video_path, duration))
    
    # Print all video durations
    print("\nAll videos and their durations:")
    for filename, duration in sorted(all_videos, key=lambda x: x[1]):
        print(f"  {filename}: {duration:.2f} seconds")
    
    print(f"\nFound {len(short_videos)} videos shorter than {args.min_duration} seconds")
    
    # If list_only is specified, don't create looped videos
    if args.list_only:
        return
    
    # Create looped versions of short videos
    for video_path, duration in short_videos:
        # Get the filename without extension
        filename = os.path.basename(video_path)
        base_name = os.path.splitext(filename)[0]
        output_path = os.path.join(args.output_dir, f"{base_name}_{args.target_duration:.0f}s.mp4")
        
        # Skip if the output file already exists and force is not enabled
        if os.path.exists(output_path) and not args.force:
            print(f"Skipping {filename} - looped version already exists at {output_path}")
            print(f"  Use --force to recreate")
            continue
        
        # Create the looped video
        create_looped_video(video_path, output_path, args.target_duration)
    
    print("Finished processing videos")

if __name__ == "__main__":
    main() 