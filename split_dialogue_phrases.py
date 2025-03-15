#!/usr/bin/env python3
"""
Script to split dialogue phrases into smaller chunks of 2-3 words each.
This script takes the existing dialogue JSON files and breaks up the text
into smaller phrases while preserving the Vietnamese words and using
the auto-generated subtitles as a reference for timing.
"""

import os
import json
import glob
import re
import argparse
import shutil
import config

def load_json_file(file_path):
    """
    Load a JSON file.
    
    Args:
        file_path: Path to the JSON file
    
    Returns:
        The loaded JSON data, or None if the file doesn't exist or is invalid
    """
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError:
        print(f"Invalid JSON file: {file_path}")
        return None
    except Exception as e:
        print(f"Error loading file {file_path}: {str(e)}")
        return None

def extract_vietnamese_words(text, dialogue_data):
    """
    Extract Vietnamese words from text based on the dialogue data.
    
    Args:
        text: The text to analyze
        dialogue_data: The dialogue data containing Vietnamese words
    
    Returns:
        List of Vietnamese words found in the text
    """
    viet_words = []
    
    # Get Vietnamese words from the dialogue data
    topic_word = dialogue_data.get("topic_word", "")
    if topic_word:
        viet_words.append(topic_word)
    
    common_words = dialogue_data.get("common_words", [])
    for word_data in common_words:
        if "word" in word_data:
            viet_words.append(word_data["word"])
    
    # Find Vietnamese words in the text
    found_words = []
    for word in viet_words:
        if word.lower() in text.lower():
            found_words.append(word)
    
    return found_words

def protect_vietnamese_tags(text):
    """
    Protect Vietnamese tags from being split by replacing them with placeholders.
    
    Args:
        text: The text to process
    
    Returns:
        Tuple of (processed text, dictionary mapping placeholders to original tags)
    """
    # Find all Vietnamese tag pairs and their content
    vietnamese_tags = re.findall(r'<vietnamese>([^<]+)</vietnamese>', text)
    text_with_placeholders = text
    
    # Replace each Vietnamese tag pair with a special token
    tag_map = {}
    for i, viet_content in enumerate(vietnamese_tags):
        placeholder = f"__VIET_TAG_{i}__"
        tag_map[placeholder] = f"<vietnamese>{viet_content}</vietnamese>"
        text_with_placeholders = text_with_placeholders.replace(
            f"<vietnamese>{viet_content}</vietnamese>", 
            f" {placeholder} "
        )
    
    return text_with_placeholders, tag_map

def restore_vietnamese_tags(text, tag_map):
    """
    Restore Vietnamese tags from placeholders.
    
    Args:
        text: The text with placeholders
        tag_map: Dictionary mapping placeholders to original tags
    
    Returns:
        Text with original tags restored
    """
    restored_text = text
    for placeholder, original_tag in tag_map.items():
        restored_text = restored_text.replace(placeholder, original_tag)
    
    return restored_text

def protect_vietnamese_words(text, viet_words):
    """
    Protect Vietnamese words from being split by replacing them with placeholders.
    
    Args:
        text: The text to process
        viet_words: List of Vietnamese words to protect
    
    Returns:
        Tuple of (processed text, dictionary mapping placeholders to original words)
    """
    text_with_placeholders = text
    word_map = {}
    
    # Sort Vietnamese words by length (descending) to handle longer phrases first
    sorted_viet_words = sorted(viet_words, key=len, reverse=True)
    
    for i, word in enumerate(sorted_viet_words):
        placeholder = f"__VIET_WORD_{i}__"
        word_map[placeholder] = word
        
        # Use word boundary pattern to avoid partial matches
        pattern = r'\b' + re.escape(word) + r'\b'
        text_with_placeholders = re.sub(pattern, placeholder, text_with_placeholders, flags=re.IGNORECASE)
    
    return text_with_placeholders, word_map

def restore_vietnamese_words(text, word_map):
    """
    Restore Vietnamese words from placeholders.
    
    Args:
        text: The text with placeholders
        word_map: Dictionary mapping placeholders to original words
    
    Returns:
        Text with original words restored
    """
    restored_text = text
    for placeholder, original_word in word_map.items():
        restored_text = restored_text.replace(placeholder, original_word)
    
    return restored_text

def simple_tokenize(text):
    """
    Simple tokenization function that splits text into words and punctuation.
    
    Args:
        text: The text to tokenize
    
    Returns:
        List of tokens
    """
    # Split on whitespace
    tokens = []
    for part in text.split():
        # Check if the part ends with punctuation
        if part and part[-1] in '.,:;!?)]}"\'':
            # Split the punctuation from the word
            if len(part) > 1:
                tokens.append(part[:-1])
            tokens.append(part[-1])
        # Check if the part starts with punctuation
        elif part and part[0] in '([{"\'':
            # Split the punctuation from the word
            if len(part) > 1:
                tokens.append(part[0])
                tokens.append(part[1:])
            else:
                tokens.append(part)
        else:
            tokens.append(part)
    
    return tokens

def split_text_into_small_phrases(text, viet_words, max_words=3):
    """
    Split text into small phrases of max_words each, preserving Vietnamese words.
    
    Args:
        text: The text to split
        viet_words: List of Vietnamese words to preserve
        max_words: Maximum number of words per phrase
    
    Returns:
        List of small phrases
    """
    # First, protect Vietnamese tags
    text_with_tag_placeholders, tag_map = protect_vietnamese_tags(text)
    
    # Then, protect Vietnamese words
    text_with_placeholders, word_map = protect_vietnamese_words(text_with_tag_placeholders, viet_words)
    
    # Tokenize the text into words using simple tokenization
    words = simple_tokenize(text_with_placeholders)
    
    # Group words into small phrases
    small_phrases = []
    current_phrase = []
    word_count = 0
    
    for word in words:
        # Check if this is a Vietnamese placeholder (either tag or word)
        is_viet_placeholder = word.startswith("__VIET_") and word.endswith("__")
        
        # If adding this word would exceed max_words and it's not a Vietnamese placeholder,
        # or if it's a sentence-ending punctuation mark, end the current phrase
        if ((word_count >= max_words and not is_viet_placeholder) or 
            word in ['.', '!', '?']):
            
            if current_phrase:
                # Add the current word if it's a punctuation mark
                if word in ['.', ',', '!', '?', ';', ':', ')', ']', '}']:
                    current_phrase.append(word)
                
                # Join the current phrase and restore Vietnamese words and tags
                phrase_text = ' '.join(current_phrase)
                phrase_text = restore_vietnamese_words(phrase_text, word_map)
                phrase_text = restore_vietnamese_tags(phrase_text, tag_map)
                
                # Clean up extra spaces
                phrase_text = re.sub(r'\s+', ' ', phrase_text).strip()
                phrase_text = re.sub(r'\s([.,!?;:])', r'\1', phrase_text)
                
                small_phrases.append(phrase_text)
                
                # Start a new phrase
                current_phrase = []
                word_count = 0
                
                # Skip to the next word if we just added a punctuation mark
                if word in ['.', '!', '?']:
                    continue
        
        # Add the current word to the phrase
        current_phrase.append(word)
        
        # Only count non-punctuation and non-Vietnamese placeholder words
        if (word not in [',', '.', '!', '?', ';', ':', '(', ')', '[', ']', '{', '}'] and 
            not is_viet_placeholder):
            word_count += 1
    
    # Add the last phrase if it's not empty
    if current_phrase:
        phrase_text = ' '.join(current_phrase)
        phrase_text = restore_vietnamese_words(phrase_text, word_map)
        phrase_text = restore_vietnamese_tags(phrase_text, tag_map)
        
        # Clean up extra spaces
        phrase_text = re.sub(r'\s+', ' ', phrase_text).strip()
        phrase_text = re.sub(r'\s([.,!?;:])', r'\1', phrase_text)
        
        small_phrases.append(phrase_text)
    
    # Remove any empty phrases
    small_phrases = [phrase for phrase in small_phrases if phrase.strip()]
    
    return small_phrases

def calculate_effective_length(phrase):
    """
    Calculate the effective length of a phrase, excluding Vietnamese tags.
    
    Args:
        phrase: The phrase to calculate length for
    
    Returns:
        Effective length of the phrase (excluding Vietnamese tags)
    """
    # Remove Vietnamese tags
    text_without_tags = re.sub(r'<vietnamese>[^<]+</vietnamese>', '', phrase)
    return len(text_without_tags)

def distribute_time_proportionally(start_time, end_time, phrases):
    """
    Distribute time proportionally across phrases based on their effective length.
    
    Args:
        start_time: Start time of the entire text
        end_time: End time of the entire text
        phrases: List of phrases to distribute time across
    
    Returns:
        List of (phrase, start_time, end_time) tuples
    """
    total_duration = end_time - start_time
    # Use effective length (excluding Vietnamese tags)
    total_length = sum(calculate_effective_length(phrase) for phrase in phrases)
    
    result = []
    current_time = start_time
    
    for phrase in phrases:
        # Calculate duration proportionally to phrase effective length
        effective_length = calculate_effective_length(phrase)
        phrase_duration = (effective_length / total_length) * total_duration if total_length > 0 else 1.0
        phrase_end_time = current_time + phrase_duration
        
        # Ensure minimum duration
        if phrase_end_time - current_time < 0.3:
            phrase_end_time = current_time + 0.3
        
        result.append((phrase, current_time, phrase_end_time))
        current_time = phrase_end_time
    
    # Adjust the last phrase to match the original end time
    if result:
        result[-1] = (result[-1][0], result[-1][1], end_time)
    
    return result

def split_dialogue_phrases(dialogue_file, output_file=None, replace_original=True):
    """
    Split dialogue phrases into smaller chunks.
    
    Args:
        dialogue_file: Path to the dialogue JSON file
        output_file: Path to save the output JSON file (optional)
        replace_original: If True, replace the original file with the split version
    
    Returns:
        Path to the output JSON file, or None if failed
    """
    # Load the dialogue file
    dialogue_data = load_json_file(dialogue_file)
    if not dialogue_data:
        return None
    
    # Extract the dialogue ID
    dialogue_id = dialogue_data["id"]
    
    # Try to load the auto-generated subtitles for reference
    auto_json_path = os.path.join(config.AUDIO_PATH, f"dialogue_{dialogue_id}_auto.json")
    auto_data = load_json_file(auto_json_path)
    
    # Create a new dialogue with split phrases
    split_dialogue = []
    
    # Process each phrase in the dialogue
    for phrase in dialogue_data["dialogue"]:
        speaker = phrase["speaker"]
        text = phrase["text"]
        start_time = phrase["start_time"]
        end_time = phrase["end_time"]
        viet_words = phrase.get("viet_words", [])
        
        # Split the text into small phrases
        small_phrases = split_text_into_small_phrases(text, viet_words)
        
        # Distribute time proportionally across small phrases
        timed_phrases = distribute_time_proportionally(start_time, end_time, small_phrases)
        
        # Create a new phrase for each small phrase
        for small_text, phrase_start, phrase_end in timed_phrases:
            # Extract Vietnamese words for this small phrase
            small_viet_words = extract_vietnamese_words(small_text, dialogue_data)
            
            # Create a new phrase
            split_phrase = {
                "speaker": speaker,
                "text": small_text,
                "start_time": phrase_start,
                "end_time": phrase_end,
                "viet_words": small_viet_words
            }
            
            split_dialogue.append(split_phrase)
    
    # Create the output data
    output_data = {
        "id": dialogue_id,
        "topic_word": dialogue_data.get("topic_word", ""),
        "topic_word_translation": dialogue_data.get("topic_word_translation", ""),
        "common_words": dialogue_data.get("common_words", []),
        "dialogue": split_dialogue
    }
    
    # Set the output file path if not provided
    if not output_file:
        output_file = dialogue_file.replace('.json', '_split.json')
    
    # Write the output JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"Split dialogue JSON file saved to: {output_file}")
    
    # If replace_original is True, copy the split file over the original
    if replace_original:
        # Create a backup of the original file
        backup_path = dialogue_file.replace('.json', '_original.json')
        if not os.path.exists(backup_path):  # Only backup if not already backed up
            shutil.copy2(dialogue_file, backup_path)
            print(f"Original file backed up to: {backup_path}")
        
        # Copy the split file over the original
        shutil.copy2(output_file, dialogue_file)
        print(f"Split file copied to original location: {dialogue_file}")
    
    return output_file

def main():
    """Main function to split dialogue phrases."""
    parser = argparse.ArgumentParser(description="Split dialogue phrases into smaller chunks")
    parser.add_argument("--dialogue-id", type=str, help="Dialogue ID to process")
    parser.add_argument("--no-replace", action="store_true", help="Don't replace the original file with the split version")
    args = parser.parse_args()
    
    # Determine whether to replace the original file
    replace_original = not args.no_replace
    
    # Process a specific dialogue if provided
    if args.dialogue_id:
        dialogue_file = os.path.join(config.AUDIO_PATH, f"dialogue_{args.dialogue_id}.json")
        
        if not os.path.exists(dialogue_file):
            print(f"Dialogue file not found: {dialogue_file}")
            return
        
        split_dialogue_phrases(dialogue_file, replace_original=replace_original)
        return
    
    # Otherwise, process all dialogues
    dialogue_files = glob.glob(os.path.join(config.AUDIO_PATH, "dialogue_*.json"))
    
    # Filter out files that already have _split, _original, _auto, etc. in their names
    dialogue_files = [f for f in dialogue_files if not any(suffix in f for suffix in ['_split', '_original', '_auto', '_merged'])]
    
    if not dialogue_files:
        print("No dialogue files found.")
        return
    
    print(f"Found {len(dialogue_files)} dialogue files to process.")
    
    # Process each file
    for dialogue_file in dialogue_files:
        # Extract the dialogue ID
        match = re.search(r'dialogue_([a-f0-9]+)\.json', os.path.basename(dialogue_file))
        if not match:
            print(f"Could not extract dialogue ID from filename: {dialogue_file}")
            continue
        
        dialogue_id = match.group(1)
        print(f"Processing dialogue {dialogue_id}...")
        split_dialogue_phrases(dialogue_file, replace_original=replace_original)

if __name__ == "__main__":
    main() 