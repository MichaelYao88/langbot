#!/usr/bin/env python3
"""
Test script for Vietnamese word identification in generate_audio.py.
"""

import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('viet_word_test')

# Add the current directory to the path
sys.path.append('.')
from generate_audio import identify_vietnamese_segments, extract_vietnamese_vocab_from_dialogue

def test_identify_vietnamese_segments():
    """Test the identify_vietnamese_segments function with various types of Vietnamese words."""
    
    # Test with a basic vocabulary including words with and without diacritics
    vocab = {
        "cây", "cay",         # Tree (with and without accent)
        "ngon", "ngọt",       # Delicious, sweet
        "cà phê", "ca phe",   # Coffee (with and without accents)
        "Việt Nam"            # Vietnam
    }
    
    # Test cases with various Vietnamese words embedded in English text
    test_cases = [
        "I really like Vietnamese cà phê in the morning.",
        "The cay in the garden is very tall.",
        "This fruit is very ngon and sweet.",
        "I think the coffee is too ngọt for me.",
        "People from Việt Nam make delicious food.",
        "Ca phe is one of the most popular drinks in Vietnam.",
        "The word 'cay' in Vietnamese means 'tree' or 'spicy' depending on the context."
    ]
    
    logger.info("Testing identify_vietnamese_segments with vocabulary: %s", ", ".join(sorted(vocab)))
    
    for test_text in test_cases:
        logger.info("-" * 50)
        logger.info("Testing text: %s", test_text)
        
        segments = identify_vietnamese_segments(test_text, vocab)
        
        logger.info("Identified segments:")
        for i, (segment_text, is_vietnamese) in enumerate(segments):
            logger.info("  Segment %d: '%s' - Vietnamese: %s", i+1, segment_text, is_vietnamese)

def test_extract_vietnamese_vocab():
    """Test the extract_vietnamese_vocab_from_dialogue function with a sample dialogue."""
    
    # Sample dialogue data
    dialogue_data = {
        "id": "sample123",
        "topic_word": "Cây",  # Tree with accent
        "topic_word_translation": "Tree",
        "common_words": [
            {"word": "ngọt", "translation": "sweet"},
            {"word": "cà phê", "translation": "coffee"}
        ],
        "vietnamese_dialogue": [
            {"speaker": "Mira", "text": "Cây này rất cao.", "viet_words": ["Cây"]}
        ],
        "english_dialogue": [
            {"speaker": "Mira", "text": "This tree is very tall."}
        ]
    }
    
    logger.info("-" * 50)
    logger.info("Testing extract_vietnamese_vocab_from_dialogue")
    
    vocab = extract_vietnamese_vocab_from_dialogue(dialogue_data)
    
    logger.info("Extracted vocabulary: %s", ", ".join(sorted(vocab)))

def main():
    """Run all tests."""
    load_dotenv(override=True)
    
    # Test Vietnamese word identification
    test_identify_vietnamese_segments()
    
    # Test vocabulary extraction
    test_extract_vietnamese_vocab()

if __name__ == "__main__":
    main() 