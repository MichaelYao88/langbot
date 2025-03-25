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

def main():
    """Main function to run the complete video generation process."""
    parser = argparse.ArgumentParser(description="Generate complete video by running all steps sequentially")
    parser.add_argument("--dialogue-id", type=str, help="Process a specific dialogue ID")
    parser.add_argument("--skip-to", choices=['timestamps', 'background'], 
                      help="Skip to a specific step (timestamps or background)")
    args = parser.parse_args()

    # Track success of each step
    success = True

    # Run each step sequentially
    if not args.skip_to:
        success = run_generate_audio(args.dialogue_id)
        if not success:
            logger.error("Failed to generate audio. Stopping process.")
            return

    if success and (not args.skip_to or args.skip_to == 'timestamps'):
        success = run_generate_timestamps(args.dialogue_id)
        if not success:
            logger.error("Failed to generate timestamps. Stopping process.")
            return

    if success and (not args.skip_to or args.skip_to == 'background'):
        success = run_generate_background(args.dialogue_id)
        if not success:
            logger.error("Failed to generate background video.")
            return

    if success:
        logger.info("Complete video generation process finished successfully!")
    else:
        logger.error("Video generation process failed.")

if __name__ == "__main__":
    main() 