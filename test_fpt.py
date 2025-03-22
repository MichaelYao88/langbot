#!/usr/bin/env python3
"""
Test script for FPT API integration.
"""

import sys
import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('fpt_test')

# Add the current directory to the path
sys.path.append('.')
from generate_audio import generate_fpt_audio

def main():
    """Test the FPT API integration."""
    load_dotenv(override=True)
    
    # Test with a simple Vietnamese phrase
    test_text = "Xin chào"
    logger.info(f"Testing FPT API with text: {test_text}")
    
    # Test male voice
    logger.info("Testing with male voice...")
    male_result = generate_fpt_audio(test_text, "male")
    logger.info(f"Male voice result: {male_result}")
    
    # Test female voice
    logger.info("Testing with female voice...")
    female_result = generate_fpt_audio(test_text, "female")
    logger.info(f"Female voice result: {female_result}")
    
    # Test with a longer phrase
    test_text2 = "Tôi đang học tiếng Việt. Rất vui được gặp bạn."
    logger.info(f"Testing FPT API with longer text: {test_text2}")
    
    # Test male voice with longer text
    logger.info("Testing longer text with male voice...")
    male_result2 = generate_fpt_audio(test_text2, "male")
    logger.info(f"Male voice result for longer text: {male_result2}")

if __name__ == "__main__":
    main() 