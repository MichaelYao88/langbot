#!/usr/bin/env python3
"""
Script to download the required NLTK data for the Language Learning Content Generator.
"""

import nltk
import sys

def main():
    """Download the required NLTK data."""
    print("Downloading NLTK data...")
    
    try:
        # Download the punkt tokenizer
        nltk.download('punkt')
        print("Successfully downloaded NLTK punkt tokenizer.")
        
        return 0
    except Exception as e:
        print(f"Error downloading NLTK data: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 