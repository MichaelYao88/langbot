#!/usr/bin/env python3
"""
Final test script for FPT API integration with minimal processing.
"""

import os
import sys
import logging
import requests
import tempfile
from pydub import AudioSegment
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fpt_final_test')

# Constants
FPT_API_KEY = "k4SgZs2NVP7O7Ibv3Oi99yQNSxSxYYPZ"
FPT_API_URL = "https://api.fpt.ai/hmi/tts/v5"
VOICE_MALE_VI = "leminh"
VOICE_FEMALE_VI = "banmai"
FPT_VOLUME_BOOST_DB = 2.0  # Minimal volume boost

def generate_fpt_audio(text, gender, output_file=None):
    """Generate Vietnamese audio using FPT API."""
    logger.info(f"Generating FPT audio for: {text} (Gender: {gender})")
    
    # Determine voice based on gender
    voice = VOICE_MALE_VI if gender == "male" else VOICE_FEMALE_VI
    
    # Use exact format from user example
    headers = {
        "api-key": FPT_API_KEY,
        "speed": "",
        "voice": voice
    }
    
    # Encode text
    try:
        encoded_payload = text.encode('utf-8')
    except UnicodeEncodeError as e:
        logger.error(f"Failed to encode text: {str(e)}")
        return None
    
    logger.info(f"Making request to FPT API: URL={FPT_API_URL}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Payload: {text}")
    
    try:
        # Make request with exact format
        response = requests.post(
            FPT_API_URL,
            data=encoded_payload,
            headers=headers,
            timeout=10
        )
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response content: {response.text}")
        
        if response.status_code != 200:
            logger.error(f"FPT API error: {response.status_code}")
            return None
        
        # Parse response to get audio URL
        response_data = response.json()
        audio_url = response_data.get("async")
        
        if not audio_url:
            logger.error("No audio URL in response")
            return None
        
        # Download audio with retry
        logger.info(f"Downloading audio from: {audio_url}")
        max_retries = 5
        retry_delay = 1
        
        for attempt in range(max_retries):
            # Wait for audio to be ready
            if attempt > 0:
                import time
                logger.info(f"Attempt {attempt+1}/{max_retries}: Waiting {retry_delay}s...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code == 200 and len(audio_response.content) > 1000:
                break
        
        if audio_response.status_code != 200 or len(audio_response.content) <= 1000:
            logger.error("Failed to download audio")
            return None
        
        # Save audio file
        if output_file:
            with open(output_file, "wb") as f:
                f.write(audio_response.content)
            
            # Create boosted version if requested
            output_base, output_ext = os.path.splitext(output_file)
            boosted_output = f"{output_base}_boosted{output_ext}"
            
            audio = AudioSegment.from_mp3(output_file)
            boosted_audio = audio + FPT_VOLUME_BOOST_DB
            boosted_audio.export(boosted_output, format="mp3")
            
            logger.info(f"Audio saved to {output_file}")
            logger.info(f"Boosted audio saved to {boosted_output}")
            
            return output_file
        else:
            # Create temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                temp_file.write(audio_response.content)
                temp_path = temp_file.name
            
            # Load and boost audio
            audio = AudioSegment.from_mp3(temp_path)
            boosted_audio = audio + FPT_VOLUME_BOOST_DB
            
            return boosted_audio
    
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        return None

def test_multiple_words():
    """Test with multiple Vietnamese words to compare quality."""
    test_words = [
        "xin chào",  # Hello
        "cảm ơn",    # Thank you
        "Việt Nam",  # Vietnam
        "chúc mừng", # Congratulations
        "thích",     # Like
        "Đà Lạt"     # Da Lat city
    ]
    
    # Create test output directory
    output_dir = "fpt_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    for word in test_words:
        logger.info("-" * 50)
        logger.info(f"Testing word: '{word}'")
        
        # Generate male voice
        output_file = os.path.join(output_dir, f"{word.replace(' ', '_')}_male.mp3")
        generate_fpt_audio(word, "male", output_file)
        
        # Generate female voice
        output_file = os.path.join(output_dir, f"{word.replace(' ', '_')}_female.mp3")
        generate_fpt_audio(word, "female", output_file)

if __name__ == "__main__":
    logger.info("Starting FPT audio test with minimal processing")
    load_dotenv(override=True)
    test_multiple_words()
    logger.info("Test completed!") 