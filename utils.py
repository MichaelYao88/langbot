"""
Utility functions for the language learning content generation system.
"""

import os
import json
import logging
import sys
from pathlib import Path
import config
import unicodedata
import re

# Set up logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("langbot.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Use stdout instead of stderr for better Unicode support
    ]
)
logger = logging.getLogger("langbot")

def ensure_directories_exist():
    """Create necessary directories if they don't exist."""
    directories = [
        os.path.dirname(config.VOCAB_LIST_PATH),
        os.path.dirname(config.USED_WORDS_PATH),
        config.DIALOGUES_PATH,
        config.AUDIO_PATH,
        config.VIDEO_PATH
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def get_used_words():
    """Get the list of already used vocabulary words."""
    if not os.path.exists(config.USED_WORDS_PATH):
        return []
    
    with open(config.USED_WORDS_PATH, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def add_used_word(word):
    """Add a word to the used words list."""
    with open(config.USED_WORDS_PATH, 'a', encoding='utf-8') as f:
        f.write(f"{word}\n")
    logger.info(f"Added '{word}' to used words list")

def save_dialogue(vocab_word, dialogue_data):
    """Save a generated dialogue to a JSON file."""
    ensure_directories_exist()
    
    # Sanitize filename to avoid issues with special characters
    # Replace non-ASCII characters with their closest ASCII equivalents or underscores
    def sanitize_filename(text):
        # Normalize unicode characters
        text = unicodedata.normalize('NFKD', text)
        # Replace non-ASCII characters with underscores
        text = re.sub(r'[^\x00-\x7F]', '_', text)
        # Replace spaces and other problematic characters
        text = re.sub(r'[^\w\-_]', '_', text)
        return text
    
    safe_vocab = sanitize_filename(vocab_word)
    filename = f"{config.DIALOGUES_PATH}/{safe_vocab}_{dialogue_data['id']}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Saved dialogue for '{vocab_word}' to {filename}")
    return filename

def load_vocab_list():
    """Load the vocabulary list from file."""
    if not os.path.exists(config.VOCAB_LIST_PATH):
        logger.warning(f"Vocabulary list not found at {config.VOCAB_LIST_PATH}")
        return []
    
    with open(config.VOCAB_LIST_PATH, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def save_vocab_list(vocab_list):
    """Save the vocabulary list to file."""
    ensure_directories_exist()
    
    with open(config.VOCAB_LIST_PATH, 'w', encoding='utf-8') as f:
        for word in vocab_list:
            f.write(f"{word}\n")
    
    logger.info(f"Saved vocabulary list with {len(vocab_list)} words") 