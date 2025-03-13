#!/usr/bin/env python3
"""
Test script for Azure Speech API
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Azure Speech API key
azure_speech_key = os.getenv("AZURE_SPEECH_KEY")
azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "eastus")

print(f"Azure Speech Key: {azure_speech_key}")
print(f"Azure Speech Region: {azure_speech_region}")

if azure_speech_key:
    print("Azure Speech Key is loaded correctly")
    
    # Try to import Azure Speech SDK
    try:
        import azure.cognitiveservices.speech as speechsdk
        print("Azure Speech SDK imported successfully")
        
        # Try to create a speech config
        speech_config = speechsdk.SpeechConfig(subscription=azure_speech_key, region=azure_speech_region)
        print("Speech config created successfully")
        
        # Try to create a speech synthesizer
        speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        print("Speech synthesizer created successfully")
        
        # Try to synthesize speech
        result = speech_synthesizer.speak_text_async("Hello, world!").get()
        print(f"Speech synthesis result: {result.reason}")
        
    except ImportError:
        print("Azure Speech SDK not found. Install with: pip install azure-cognitiveservices-speech")
    except Exception as e:
        print(f"Error: {str(e)}")
else:
    print("Azure Speech Key is not loaded correctly") 