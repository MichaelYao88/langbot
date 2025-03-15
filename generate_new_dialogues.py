#!/usr/bin/env python3
"""
Script to generate new dialogues using topic words from common_vietnamese.txt
that haven't been used in existing dialogues yet.
"""

import os
import argparse
import subprocess
import random
import glob
import json
import time
import re
import sys

def get_common_vietnamese_words():
    """Read the list of common Vietnamese words from the file."""
    words = []
    try:
        with open("common_vietnamese.txt", "r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(words)} common Vietnamese words")
    except Exception as e:
        print(f"Error loading common Vietnamese words: {e}")
    return words

def get_used_topic_words():
    """Get a list of topic words that have already been used in existing dialogues."""
    used_words = set()
    
    # Get all dialogue files
    dialogue_files = glob.glob("data/dialogues/*.json")
    
    for file_path in dialogue_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                dialogue_data = json.load(f)
                if "topic_word" in dialogue_data and dialogue_data["topic_word"]:
                    used_words.add(dialogue_data["topic_word"].lower())
        except Exception as e:
            print(f"Error reading dialogue file {file_path}: {e}")
    
    print(f"Found {len(used_words)} already used topic words")
    return used_words

def get_unused_topic_word(common_words, used_words):
    """Get a random topic word that hasn't been used yet."""
    unused_words = [word for word in common_words if word.lower() not in used_words]
    
    if not unused_words:
        print("All common words have been used already!")
        return None
    
    print(f"Found {len(unused_words)} unused topic words")
    return random.choice(unused_words)

def generate_dialogue_with_topic_word(topic_word, provider="anthropic"):
    """Generate a dialogue using the specified topic word."""
    print(f"\nGenerating dialogue with topic word: {topic_word}")
    
    # Create a temporary batch file to set the encoding and run the command
    if sys.platform == "win32":
        batch_file = "temp_run_dialogue.bat"
        with open(batch_file, "w", encoding="utf-8") as f:
            f.write("@echo off\n")
            f.write("chcp 65001 > nul\n")  # Set UTF-8 encoding
            f.write(f'python generate_dialogue.py --topic_word "{topic_word}" --provider {provider}\n')
        
        try:
            # Run the batch file
            subprocess.run(batch_file, shell=True)
            
            # Check if a dialogue file was created with this topic word
            # The filename format is typically topic_word_ID.json
            safe_topic_word = topic_word.replace(" ", "_")
            dialogue_files = glob.glob(f"data/dialogues/{safe_topic_word}_*.json")
            
            # If not found with that pattern, try a more general search
            if not dialogue_files:
                # Get all dialogue files
                all_files = glob.glob("data/dialogues/*.json")
                # Check each file for the topic word
                for file_path in all_files:
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            dialogue_data = json.load(f)
                            if "topic_word" in dialogue_data and dialogue_data["topic_word"] == topic_word:
                                dialogue_files.append(file_path)
                                break
                    except:
                        pass
            
            # Clean up the batch file
            if os.path.exists(batch_file):
                os.remove(batch_file)
            
            if dialogue_files:
                print(f"Successfully generated dialogue: {os.path.basename(dialogue_files[0])}")
                return True
            else:
                print(f"Failed to generate dialogue with topic word: {topic_word}")
                return False
                
        except Exception as e:
            print(f"Error running generate_dialogue.py: {e}")
            # Clean up the batch file
            if os.path.exists(batch_file):
                os.remove(batch_file)
            return False
    else:
        # For non-Windows platforms
        cmd = [
            "python", "generate_dialogue.py",
            "--topic_word", topic_word,
            "--provider", provider
        ]
        
        try:
            subprocess.run(cmd, check=True)
            
            # Check if a dialogue file was created
            safe_topic_word = topic_word.replace(" ", "_")
            dialogue_files = glob.glob(f"data/dialogues/{safe_topic_word}_*.json")
            
            if dialogue_files:
                print(f"Successfully generated dialogue: {os.path.basename(dialogue_files[0])}")
                return True
            else:
                print(f"Failed to generate dialogue with topic word: {topic_word}")
                return False
                
        except subprocess.CalledProcessError as e:
            print(f"Error running generate_dialogue.py: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Generate new dialogues with unused Vietnamese topic words")
    parser.add_argument("--count", type=int, default=1, help="Number of dialogues to generate")
    parser.add_argument("--provider", type=str, default="anthropic", choices=["openai", "anthropic"],
                        help="LLM provider to use")
    args = parser.parse_args()
    
    # Get common Vietnamese words
    common_words = get_common_vietnamese_words()
    if not common_words:
        print("No common Vietnamese words found. Exiting.")
        return
    
    # Get used topic words
    used_words = get_used_topic_words()
    
    # Generate the specified number of dialogues
    successful_count = 0
    for i in range(args.count):
        if i > 0:
            # Wait a bit between generations to avoid rate limiting
            print(f"\nWaiting 5 seconds before generating the next dialogue...")
            time.sleep(5)
            
            # Refresh the list of used words in case new dialogues were generated
            used_words = get_used_topic_words()
        
        # Get an unused topic word
        topic_word = get_unused_topic_word(common_words, used_words)
        if not topic_word:
            print("No more unused topic words available. Exiting.")
            break
        
        # Generate a dialogue with the topic word
        print(f"\nGenerating dialogue {i+1}/{args.count}")
        success = generate_dialogue_with_topic_word(topic_word, args.provider)
        
        if success:
            successful_count += 1
            # Add the word to used words to avoid using it again in this session
            used_words.add(topic_word.lower())
    
    print(f"\nGeneration complete. Successfully generated {successful_count}/{args.count} dialogues.")

if __name__ == "__main__":
    main() 