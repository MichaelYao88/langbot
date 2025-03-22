#!/usr/bin/env python3
"""
Simple test script for FPT API using the exact format from the user's example.
"""

import sys
import os
import requests
import logging
from pydub import AudioSegment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fpt_simple_test')

def test_fpt_simple():
    """Test the FPT API with the simplest possible request format."""
    
    # Test text
    text = "Xin chào"
    logger.info(f"Testing FPT API with text: '{text}'")
    
    # Exact format from user example
    url = 'https://api.fpt.ai/hmi/tts/v5'
    payload = text
    headers = {
        'api-key': 'k4SgZs2NVP7O7Ibv3Oi99yQNSxSxYYPZ',
        'speed': '',
        'voice': 'banmai'
    }
    
    logger.info("Making request with exact format from example")
    response = requests.post(url, data=payload.encode('utf-8'), headers=headers)
    
    logger.info(f"Response status: {response.status_code}")
    logger.info(f"Response content: {response.text}")
    
    # Parse the response to get the audio URL
    try:
        response_data = response.json()
        audio_url = response_data.get("async")
        
        if audio_url:
            # Download the audio
            logger.info(f"Downloading audio from: {audio_url}")
            audio_response = requests.get(audio_url)
            
            if audio_response.status_code == 200:
                # Save the audio
                output_file = "fpt_simple_test.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_response.content)
                logger.info(f"Audio saved to {output_file}")
                
                # Let's try applying a very small boost
                try:
                    audio = AudioSegment.from_mp3(output_file)
                    # Apply a minimal 2dB boost
                    boosted_audio = audio + 2.0
                    boosted_output = "fpt_simple_test_boosted.mp3"
                    boosted_audio.export(boosted_output, format="mp3")
                    logger.info(f"Boosted audio saved to {boosted_output}")
                except Exception as e:
                    logger.error(f"Error boosting audio: {str(e)}")
                
                return True
            else:
                logger.error(f"Failed to download audio: {audio_response.status_code}")
        else:
            logger.error("No audio URL found in response")
            
    except Exception as e:
        logger.error(f"Error processing response: {str(e)}")
    
    return False

if __name__ == "__main__":
    success = test_fpt_simple()
    if success:
        print("Test completed successfully!")
    else:
        print("Test failed!")
        sys.exit(1) 