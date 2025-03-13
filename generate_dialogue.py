"""
Script to generate dialogues for language learning content.
This script generates Vietnamese conversations first, then creates English translations
with specific Vietnamese words left untranslated.
"""

import os
import argparse
import json
import time
import uuid
import random
from openai import OpenAI
import anthropic
import config
import utils
import re

# Character definitions
MIRA = {
    "name": "Mira",
    "description": "A young, slightly tsundere, but ultimately feminine, agreeable Russian girl with traditional conservative values who likes chess. She lives in Saigon."
}

MICHAEL = {
    "name": "Michael",
    "description": "A progressive, pragmatic, agreeable Viet-American guy who likes to travel and talk about the world and politics. He lives in Saigon."
}

# Possible hooks for the dialogues
DIALOGUE_HOOKS = [
    "romantic tension",
    "mysterious event",
    "let's forget about yesterday/last night",
    "gossip",
    "cultural misunderstanding",
    "surprising coincidence",
    "shared secret",
    "unexpected encounter",
    "strange occurrence",
    "hidden feelings",
    "unresolved past",
    "future plans together with ambiguous romantic tension",
    "moral dilemma",
    "mysterious past",
    "cultural clash",
    "intense argument",
    "long-lost connection",
    "backstory reveal",
    "mysterious family history",
    "flirtatious banter",
    "ambiguous relationship with ex",
    "vietnamese slang",
    "stupid joke"
]

# Possible conversation topics
CONVERSATION_TOPICS = [
    "food and dining",
    "travel",
    "family",
    "hobbies",
    "work and career",
    "education",
    "relationships",
    "culture",
    "weather",
    "current events",
    "technology",
    "health",
    "sports",
    "music",
    "movies",
    "books",
    "shopping",
    "holidays",
    "daily routine",
    "future plans"
]

def generate_dialogue_with_openai(topic=None, topic_word=None):
    """Generate a dialogue using OpenAI API."""
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    
    if not hook:
        hook = random.choice(DIALOGUE_HOOKS)
    hook2 = random.choice(DIALOGUE_HOOKS)
    if not topic:
        topic = random.choice(CONVERSATION_TOPICS) 
    topic2 = random.choice(CONVERSATION_TOPICS)
    
    prompt = f"""
    Create a natural, engaging dialogue in Vietnamese between Mira and Michael.
    
    Character information:
    - Mira: {MIRA["description"]}
    - Michael: {MICHAEL["description"]}
    - They are romantically interested in each other but have not yet confessed their feelings.
    
    The dialogue should:
    1. Be 4-6 exchanges long (each character speaks 2-3 times)
    2. Be entirely in Vietnamese
    3. Be about the topic: {topic}
    4. Have a hook related to: {hook}
    5. End unresolved to encourage viewers to check the comments section for more
    6. Be natural and conversational
    7. Avoid greetings and start with hooks
    8. Avoid this positive conversation ending that doesn't sound natural. Conversations should be with some tension and unresolved unless they are humorous.
    
    Format the dialogue as follows:
    Mira: [Vietnamese dialogue]
    Michael: [Vietnamese dialogue]
    
    After creating the dialogue, please:
    1. Choose a topic word or phrase from the dialogue that appears at least 3 times
    2. Choose two common Vietnamese words that appear in the dialogue
    
    Then provide:
    TOPIC_WORD: [the chosen topic word/phrase] - [English translation]
    COMMON_WORD_1: [first common word] - [English translation]
    COMMON_WORD_2: [second common word] - [English translation]
    
    Finally, provide an English translation of the dialogue, but leave the topic word/phrase and the two common words untranslated (in Vietnamese).
    
    Format the English translation as:
    Mira: [English dialogue with Vietnamese words left untranslated]
    Michael: [English dialogue with Vietnamese words left untranslated]
    """
    
    # If a specific topic word is provided, modify the prompt
    if topic_word:
        prompt += f"\nIMPORTANT: Use '{topic_word}' as the topic word/phrase that appears at least 3 times in the dialogue."
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful language learning content creator."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
    )
    
    return response.choices[0].message.content

def generate_dialogue_with_anthropic(topic=None, topic_word=None):
    """Generate a dialogue using Anthropic API."""
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    
    hook = random.choice(DIALOGUE_HOOKS)
    hook2 = random.choice(DIALOGUE_HOOKS)
    if not topic:
        topic = random.choice(CONVERSATION_TOPICS) 
    
    prompt = f"""
    Create a natural, engaging dialogue in Vietnamese between Mira and Michael.
    
    Character information:
    - Mira: {MIRA["description"]}
    - Michael: {MICHAEL["description"]}
    - They are interested in each other but are too shy to confess their feelings.
    
    The dialogue should:
    1. Be 4-5 exchanges long (each character speaks 2-3 times)
    2. Be entirely in Vietnamese
    3. Be about the topic: {topic}
    4. Have a hook like {hook} or {hook2}
    5. End unresolved to encourage viewers to check the comments section for more
    6. Be natural and conversational and not too intellectual. Avoid adverbs unless absolutely necessary.
    7. Avoid greetings and start with hooks
    8. Avoid this positive conversation ending that doesn't sound natural. Conversations should be with some tension and unresolved unless they are humorous.
    9. Speakers can have short responses and long responses. Dialogue doesn't always need to be the same length.
    10. Please make these dialogues as viral as possible. Employ strangeness, romantic tension, indirect/ambiguous flirtation, interesting facts, ambiguity, controversial topics/events, recent controversies, recent memes, and/or other viral elements.
    
    Format the dialogue as follows:
    Mira: [Vietnamese dialogue]
    Michael: [Vietnamese dialogue]
    
    After creating the dialogue, please:
    1. Choose a topic word or phrase from the dialogue that appears at least 3 times. DO NOT CHOOSE chúng ta.
    2. Choose two common Vietnamese words that aren't pronouns that appear in the dialogue at least 2 times. DO NOT CHOOSE chúng ta.
    3. If this cannot be done, regenerate the dialogue.
    
    Then provide:
    TOPIC_WORD: [the chosen topic word/phrase] - [English translation]
    COMMON_WORD_1: [first common word] - [English translation]
    COMMON_WORD_2: [second common word] - [English translation]
    
    Finally, provide an English translation of the dialogue, but leave the topic word/phrase and the two common words untranslated (in Vietnamese).
    
    Format the English translation as:
    Mira: [English dialogue with Vietnamese words left untranslated]
    Michael: [English dialogue with Vietnamese words left untranslated]
    """
    
    # If a specific topic word is provided, modify the prompt
    if topic_word:
        prompt += f"\nIMPORTANT: Use '{topic_word}' as the topic word/phrase that appears at least 3 times in the dialogue."
    
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=3000,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
    )
    
    return response.content[0].text

def parse_dialogue_response(response_text):
    """Parse the dialogue response into a structured format."""
    # Initialize the data structure
    dialogue_data = {
        "id": str(uuid.uuid4())[:8],
        "timestamp": int(time.time()),
        "vietnamese_dialogue": [],
        "english_dialogue": [],
        "topic_word": "",
        "topic_word_translation": "",
        "common_words": []
    }
    
    # Split the response into sections
    sections = response_text.split("TOPIC_WORD:")
    
    if len(sections) < 2:
        print("Error: Response format is not as expected.")
        return None
    
    # Extract Vietnamese dialogue from the first section
    vietnamese_section = sections[0].strip()
    lines = vietnamese_section.split('\n')
    
    # Process Vietnamese dialogue
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if ":" in line:
            parts = line.split(":", 1)
            speaker = parts[0].strip()
            if speaker in ["Mira", "Michael"]:
                dialogue = parts[1].strip()
                dialogue_data["vietnamese_dialogue"].append({
                    "speaker": speaker,
                    "text": dialogue
                })
    
    # Process the rest of the response
    rest_of_response = "TOPIC_WORD:" + sections[1]
    
    # Extract topic word and common words
    topic_word_match = re.search(r'TOPIC_WORD:\s*([^-]+)-\s*([^\n]+)', rest_of_response)
    if topic_word_match:
        dialogue_data["topic_word"] = topic_word_match.group(1).strip()
        dialogue_data["topic_word_translation"] = topic_word_match.group(2).strip()
    
    common_word1_match = re.search(r'COMMON_WORD_1:\s*([^-]+)-\s*([^\n]+)', rest_of_response)
    if common_word1_match:
        dialogue_data["common_words"].append({
            "word": common_word1_match.group(1).strip(),
            "translation": common_word1_match.group(2).strip()
        })
    
    common_word2_match = re.search(r'COMMON_WORD_2:\s*([^-]+)-\s*([^\n]+)', rest_of_response)
    if common_word2_match:
        dialogue_data["common_words"].append({
            "word": common_word2_match.group(1).strip(),
            "translation": common_word2_match.group(2).strip()
        })
    
    # Extract English dialogue
    # Find where the English dialogue starts
    english_start = None
    for pattern in ["Mira:", "Michael:"]:
        match = re.search(f'(?m)^{pattern}', rest_of_response)
        if match and (english_start is None or match.start() < english_start):
            english_start = match.start()
    
    if english_start is not None:
        english_section = rest_of_response[english_start:]
        english_lines = english_section.split('\n')
        
        current_speaker = None
        current_text = ""
        
        for line in english_lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith("Mira:") or line.startswith("Michael:"):
                # Save previous speaker's text if any
                if current_speaker and current_text:
                    dialogue_data["english_dialogue"].append({
                        "speaker": current_speaker,
                        "text": current_text.strip()
                    })
                    current_text = ""
                
                # Start new speaker
                parts = line.split(":", 1)
                current_speaker = parts[0].strip()
                if len(parts) > 1:
                    current_text = parts[1].strip()
            else:
                # Continue previous speaker's text
                current_text += " " + line
        
        # Add the last speaker's text
        if current_speaker and current_text:
            dialogue_data["english_dialogue"].append({
                "speaker": current_speaker,
                "text": current_text.strip()
            })
    
    return dialogue_data

def save_dialogue_data(dialogue_data, output_file=None):
    """Save the dialogue data to a file."""
    if output_file is None:
        # Create a safe filename from the topic word
        safe_topic = re.sub(r'[^\w\-_]', '_', dialogue_data["topic_word"])
        output_file = f"data/dialogues/{safe_topic}_{dialogue_data['id']}.json"
    
    # Ensure the directory exists
    utils.ensure_directories_exist()
    
    # Clean up any potential issues with text fields
    for dialogue_list in ["vietnamese_dialogue", "english_dialogue"]:
        for i, exchange in enumerate(dialogue_data[dialogue_list]):
            if "text" in exchange:
                # Replace any problematic characters or line breaks
                text = exchange["text"]
                text = text.replace("\r", " ").replace("\n", " ")
                # Normalize whitespace
                text = re.sub(r'\s+', ' ', text).strip()
                dialogue_data[dialogue_list][i]["text"] = text
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dialogue_data, f, ensure_ascii=False, indent=2)
    
    return output_file

def generate_dialogue(topic=None, topic_word=None, provider="anthropic"):
    """Generate a dialogue using the specified provider."""
    if provider == "openai":
        response_text = generate_dialogue_with_openai(topic, topic_word)
    else:
        response_text = generate_dialogue_with_anthropic(topic, topic_word)
    
    dialogue_data = parse_dialogue_response(response_text)
    
    if dialogue_data:
        output_file = save_dialogue_data(dialogue_data)
        return dialogue_data, output_file
    else:
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Generate dialogues for language learning content')
    parser.add_argument('--topic', type=str, help='Topic for the conversation')
    parser.add_argument('--topic_word', type=str, help='Specific topic word/phrase to use in the dialogue')
    parser.add_argument('--provider', type=str, default=config.DEFAULT_PROVIDER, 
                        choices=['openai', 'anthropic'],
                        help='LLM provider to use')
    
    args = parser.parse_args()
    
    utils.ensure_directories_exist()
    
    print("Generating dialogue...")
    if args.topic:
        print(f"Topic: {args.topic}")
    if args.topic_word:
        print(f"Topic word/phrase: {args.topic_word}")
    
    dialogue_data, output_file = generate_dialogue(args.topic, args.topic_word, args.provider)
    
    if dialogue_data:
        print(f"\nGenerated dialogue saved to: {output_file}")
        print(f"\nTopic word: {dialogue_data['topic_word']} - {dialogue_data['topic_word_translation']}")
        print("Common words:")
        for word in dialogue_data["common_words"]:
            print(f"- {word['word']} - {word['translation']}")
        
        print("\nVietnamese Dialogue:")
        for exchange in dialogue_data["vietnamese_dialogue"]:
            print(f"{exchange['speaker']}: {exchange['text']}")
            print()
        
        print("\nEnglish Dialogue (with untranslated Vietnamese words):")
        for exchange in dialogue_data["english_dialogue"]:
            print(f"{exchange['speaker']}: {exchange['text']}")
            print()
    else:
        print("Failed to generate dialogue. Please try again.")

if __name__ == "__main__":
    main() 