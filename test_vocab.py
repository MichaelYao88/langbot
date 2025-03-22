#!/usr/bin/env python3
"""
Simple test script for Vietnamese vocabulary extraction.
"""

import sys
sys.path.append('.')
from generate_audio import extract_vietnamese_vocab_from_dialogue

# Test data with Vietnamese words
test_data = {
    "topic_word": "cây",
    "common_words": [
        {"word": "ngọt"},
        {"word": "cà phê"}
    ]
}

# Extract vocabulary
vocab = extract_vietnamese_vocab_from_dialogue(test_data)

# Print the result
print("Extracted vocabulary:", sorted(vocab)) 