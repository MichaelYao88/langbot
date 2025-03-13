"""
Configuration settings for the language learning content generation system.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Language settings
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "Vietnamese")  # The language being taught
SOURCE_LANGUAGE = os.getenv("SOURCE_LANGUAGE", "English")     # The language used for translations

# API keys (loaded from environment variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "your_anthropic_api_key_here")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your_elevenlabs_api_key_here")  # For text-to-speech

# Default provider
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "anthropic")  # Default LLM provider to use

# File paths
VOCAB_LIST_PATH = "data/vocab_list.txt"
USED_WORDS_PATH = "data/used_words.txt"
DIALOGUES_PATH = "data/dialogues/"
AUDIO_PATH = "data/audio/"
VIDEO_PATH = "data/videos/"

# Character settings
CHARACTERS = [
    {"name": "Mira", "personality": "A young Russian girl with traditional values who likes chess. She lives in Saigon."},
    {"name": "Michael", "personality": "A liberal Viet-American guy who likes to travel and talk about the world and politics. He lives in Saigon."}
]

# Content settings
DIALOGUE_TURNS = 4  # Number of exchanges in each dialogue
WORDS_PER_DIALOGUE = 1  # Number of target vocabulary words to include in each dialogue

# TTS settings
VOICE_MIRA = os.getenv("VOICE_MIRA", "21m00Tcm4TlvDq8ikWAM")  # Female voice
VOICE_MICHAEL = os.getenv("VOICE_MICHAEL", "AZnzlk1XvdvUeBnXmlld")  # Male voice 