"""
Script to generate vocabulary lists for language learning content.
This script uses an LLM API to generate vocabulary words for the target language.
"""

import os
import argparse
import time
import random
from openai import OpenAI
import anthropic
import config
import utils
import re

def map_difficulty_level(difficulty_number):
    """Map numeric difficulty level (1-10) to descriptive difficulty."""
    if 1 <= difficulty_number <= 3:
        return "beginner"
    elif 4 <= difficulty_number <= 7:
        return "intermediate"
    else:  # 8-10
        return "advanced"

def generate_vocab_with_openai(num_words=20, difficulty_number=5, topic="most commonly used words"):
    """Generate vocabulary words using OpenAI API."""
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    difficulty = map_difficulty_level(difficulty_number)
    used_words = utils.get_used_words()
    
    prompt = f"""
    Generate a list of {num_words} {config.TARGET_LANGUAGE} vocabulary words related to the topic: "{topic}".
    The difficulty level is {difficulty_number} on a scale of 1-10 (where 1 is absolute beginner and 10 is advanced).
    
    For each word, provide:
    1. The word in {config.TARGET_LANGUAGE}
    2. Its pronunciation guide
    3. Its translation in {config.SOURCE_LANGUAGE}
    4. A brief description of usage context
    
    Format each entry as:
    word | pronunciation | translation | context
    
    The words should be useful in everyday conversation and should NOT include any of these already used words:
    {', '.join(used_words)}
    
    Focus on words that would be interesting in short dialogues between two people.
    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful language learning assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    
    return response.choices[0].message.content

def generate_vocab_with_anthropic(num_words=20, difficulty_number=5, topic="most commonly used words"):
    """Generate vocabulary words using Anthropic API."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    
    difficulty = map_difficulty_level(difficulty_number)
    used_words = utils.get_used_words()
    
    prompt = f"""
    Generate a list of {num_words} {config.TARGET_LANGUAGE} vocabulary words related to the topic: "{topic}".
    The difficulty level is {difficulty_number} on a scale of 1-10 (where 1 is absolute beginner and 10 is advanced).
    
    For each word, provide:
    1. The word in {config.TARGET_LANGUAGE}
    2. Its pronunciation guide
    3. Its translation in {config.SOURCE_LANGUAGE}
    4. A brief description of usage context
    
    Format each entry as:
    word | pronunciation | translation | context
    
    The words should be useful in everyday conversation and should NOT include any of these already used words:
    {', '.join(used_words)}
    
    Focus on words that would be interesting in short dialogues between two people.
    
    IMPORTANT: Make sure all words are in Vietnamese, not English. The word field should contain Vietnamese words only.
    """
    
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )
    
    return response.content[0].text

def parse_vocab_response(response_text):
    """Parse the response from the LLM into a structured vocabulary list."""
    vocab_list = []
    
    lines = response_text.strip().split('\n')
    for line in lines:
        if '|' in line:
            parts = [part.strip() for part in line.split('|')]
            if len(parts) >= 3:  # At minimum, we need word, pronunciation, and translation
                # Clean the word: remove numbers, dots, and extra whitespace
                word = parts[0].strip()
                # Remove numbering patterns like "1. ", "1) ", "1 - ", etc.
                word = re.sub(r'^\d+[\.\)\-\s]+\s*', '', word)
                # Remove any remaining leading/trailing whitespace
                word = word.strip()
                
                pronunciation = parts[1].strip()
                translation = parts[2].strip()
                context = parts[3].strip() if len(parts) > 3 else ""
                
                vocab_list.append({
                    "word": word,
                    "pronunciation": pronunciation,
                    "translation": translation,
                    "context": context
                })
    
    return vocab_list

def save_vocab_to_file(vocab_list, output_file=None, topic="general"):
    """Save the vocabulary list to a file."""
    if output_file is None:
        # Include topic in filename
        safe_topic = ''.join(c if c.isalnum() or c in ['-', '_'] else '_' for c in topic)
        output_file = f"data/vocab_list_{safe_topic}_{int(time.time())}.json"
    
    import json
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(vocab_list, f, ensure_ascii=False, indent=2)
    
    # Also save just the words to the main vocab list file
    words_only = [item["word"] for item in vocab_list]
    utils.save_vocab_list(words_only)
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Generate vocabulary list for language learning content')
    parser.add_argument('--num_words', type=int, default=20, help='Number of vocabulary words to generate')
    parser.add_argument('--difficulty', type=int, default=5, 
                        choices=range(1, 11),
                        help='Difficulty level of vocabulary words (1-10, where 1 is beginner and 10 is advanced)')
    parser.add_argument('--topic', type=str, default='most commonly used words',
                        help='Topic for vocabulary words (e.g., food, travel, greetings)')
    parser.add_argument('--provider', type=str, default=config.DEFAULT_PROVIDER, 
                        choices=['openai', 'anthropic'],
                        help='LLM provider to use')
    parser.add_argument('--output', type=str, help='Output file path')
    
    args = parser.parse_args()
    
    utils.ensure_directories_exist()
    
    difficulty_description = map_difficulty_level(args.difficulty)
    print(f"Generating {args.num_words} {config.TARGET_LANGUAGE} vocabulary words on topic '{args.topic}'")
    print(f"Difficulty level: {args.difficulty}/10 ({difficulty_description})")
    print(f"Using provider: {args.provider}")
    
    if args.provider == 'openai':
        response_text = generate_vocab_with_openai(args.num_words, args.difficulty, args.topic)
    else:
        response_text = generate_vocab_with_anthropic(args.num_words, args.difficulty, args.topic)
    
    vocab_list = parse_vocab_response(response_text)
    
    output_file = save_vocab_to_file(vocab_list, args.output, args.topic)
    
    print(f"Generated {len(vocab_list)} vocabulary words and saved to {output_file}")
    print("\nSample vocabulary words:")
    for i, item in enumerate(vocab_list[:5]):  # Show first 5 words
        print(f"{i+1}. {item['word']} ({item['pronunciation']}) - {item['translation']}")
    
    if len(vocab_list) > 5:
        print(f"... and {len(vocab_list) - 5} more words")

if __name__ == "__main__":
    main() 