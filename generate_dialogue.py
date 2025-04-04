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
    "stupid joke",
    "you're not mira! something is off",
    "I have the feeling reality is not what it seems",
    "deja vu. We've been here before.",
    "we're in danger. They are watching. Act normal."
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
    - They are interested in each other but are too shy to confess their feelings.
    
    The dialogue should:
    1. Be 3-5 exchanges long (each character speaks 2-3 times). each response is 1-3 sentences.
    2. Be entirely in Vietnamese
    3. Be about the topic: {topic}
    4. Have a hook like {hook} or {hook2}
    5. End unresolved to encourage viewers to check the comments section for more
    6. Be natural and conversational and not too intellectual. Avoid adverbs unless absolutely necessary.
    7. Avoid greetings and start with hooks
    8. Avoid this positive conversation ending that doesn't sound natural. Conversations should be with some tension and unresolved unless they are humorous.
    9. Speakers should have short responses sometimes. Dialogue doesn't always need to be the same length.
    10. Employ strangeness, romantic tension, indirect/ambiguous flirtation, interesting facts, ambiguity, controversial topics/events, recent controversies, recent memes, and/or other viral elements.
    11. Randomly decide who starts the conversation.
    12. End it in a way that loops to the start or ends with a question.

    Format the dialogue as follows:
    Mira: [Vietnamese dialogue]
    Michael: [Vietnamese dialogue]
    
    After creating the dialogue, please:
    1. Choose a topic word or phrase from the dialogue that appears at least 3 times. DO NOT CHOOSE chúng ta. {topic_word}
    2. Choose five common Vietnamese words that aren't pronouns that appear in the dialogue twice or more. Try to choose one of each a verb, adjective, adverb, part-of-speech, and 
    noun. This is imperative.
    
    Then provide:
    TOPIC_WORD: [the chosen topic word/phrase] - [English translation]
    COMMON_WORD_1: [first common word] - [English translation]
    COMMON_WORD_2: [second common word] - [English translation]
    COMMON_WORD_3: [third common word] - [English translation]
    COMMON_WORD_4: [fourth common word] - [English translation]
    COMMON_WORD_5: [fifth common word] - [English translation]
    
    If there are not 5 common words, create another dialogue.

    Finally, provide an English translation of the dialogue, but leave the topic word/phrase and ALL FIVE common words untranslated (in Vietnamese). Make sure to use ALL FIVE common words in their Vietnamese form in the English translation.
    
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
    
    if not topic_word:
        topic_word=""
    else:
        topic_word=f'1. "Actually the topic word is {topic_word}. Please make sure this is in the conversation three times."'
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
    1. Be 3-5 exchanges long (each character speaks 2-3 times). each response is 1-3 sentences.
    2. Be entirely in Vietnamese
    3. Be about the topic: {topic}
    4. Have a hook like {hook} or {hook2}
    5. End unresolved to encourage viewers to check the comments section for more
    6. Be natural and conversational and not too intellectual. Avoid adverbs unless absolutely necessary.
    7. Avoid greetings and start with hooks
    8. Avoid this positive conversation ending that doesn't sound natural. Conversations should be with some tension and unresolved unless they are humorous.
    9. Speakers should have short responses sometimes. Dialogue doesn't always need to be the same length.
    10. Employ strangeness, romantic tension, indirect/ambiguous flirtation, interesting facts, ambiguity, controversial topics/events, recent controversies, recent memes, and/or other viral elements.
    12. End it in a way that loops to the start or ends with a question.

    Format the dialogue as follows:
    Mira: [Vietnamese dialogue]
    Michael: [Vietnamese dialogue]
    
    After creating the dialogue, please:
    1. Choose a topic word or phrase from the dialogue that appears at least 3 times. DO NOT CHOOSE chúng ta. {topic_word}
    2. Choose five common Vietnamese words that aren't pronouns that appear in the dialogue, try to make them appear twice or more. Try to choose one of each a verb, adjective, adverb, part-of-speech, and 
    noun. This is imperative.
    
    Then provide:
    TOPIC_WORD: [the chosen topic word/phrase] - [English translation]
    COMMON_WORD_1: [first common word] - [English translation]
    COMMON_WORD_2: [second common word] - [English translation]
    COMMON_WORD_3: [third common word] - [English translation]
    COMMON_WORD_4: [fourth common word] - [English translation]
    COMMON_WORD_5: [fifth common word] - [English translation]
    
    If there are not 5 common words, create another dialogue.

    Finally, provide an English translation of the dialogue, but leave the topic word/phrase and ALL FIVE common words untranslated (in Vietnamese). Make sure to use ALL FIVE common words in their Vietnamese form in the English translation.
    
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
    
    # Extract all five common words
    for i in range(1, 6):
        word_match = re.search(f'COMMON_WORD_{i}:\s*([^-]+)-\s*([^\n]+)', rest_of_response)
        if word_match:
            dialogue_data["common_words"].append({
                "word": word_match.group(1).strip(),
                "translation": word_match.group(2).strip()
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
    try:
        if provider == "openai":
            response_text = generate_dialogue_with_openai(topic, topic_word)
        else:
            response_text = generate_dialogue_with_anthropic(topic, topic_word)
        
        dialogue_data = parse_dialogue_response(response_text)
        
        if dialogue_data:
            output_file = save_dialogue_data(dialogue_data)
            return dialogue_data, output_file
        else:
            print("Failed to parse dialogue response.")
            return None, None
    except Exception as e:
        print(f"Error generating dialogue: {str(e)}")
        return None, None

def main():
    parser = argparse.ArgumentParser(description='Generate dialogues for language learning content')
    parser.add_argument('--topic', type=str, help='Topic for the conversation (if not specified, a random topic will be chosen for each dialogue)')
    parser.add_argument('--topic_word', type=str, help='Specific topic word/phrase to use in the dialogue')
    parser.add_argument('--provider', type=str, default=config.DEFAULT_PROVIDER, 
                        choices=['openai', 'anthropic'],
                        help='LLM provider to use')
    parser.add_argument('--count', type=int, default=1,
                        help='Number of dialogues to generate')
    parser.add_argument('--delay', type=int, default=2,
                        help='Delay in seconds between API calls when generating multiple dialogues')
    parser.add_argument('--random_topics', action='store_true',
                        help='Use a different random topic for each dialogue (ignores --topic)')
    parser.add_argument('--continue_on_error', action='store_true',
                        help='Continue generating dialogues even if some fail')
    
    args = parser.parse_args()
    
    utils.ensure_directories_exist()
    
    print(f"Generating {args.count} dialogue(s)...")
    if args.topic and not args.random_topics:
        print(f"Topic: {args.topic}")
    elif args.random_topics:
        print("Using random topics for each dialogue")
    if args.topic_word:
        print(f"Topic word/phrase: {args.topic_word}")
    
    generated_files = []
    failed_count = 0
    
    for i in range(args.count):
        if args.count > 1:
            print(f"\n--- Generating dialogue {i+1}/{args.count} ---")
        
        # Use a random topic for each dialogue if specified
        current_topic = None
        if args.random_topics:
            current_topic = random.choice(CONVERSATION_TOPICS)
            print(f"Selected random topic: {current_topic}")
        else:
            current_topic = args.topic
        
        try:
            dialogue_data, output_file = generate_dialogue(current_topic, args.topic_word, args.provider)
            
            if dialogue_data:
                generated_files.append(output_file)
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
                failed_count += 1
                print(f"Failed to generate dialogue {i+1}.")
                if not args.continue_on_error and args.count > 1:
                    user_input = input("Continue generating dialogues? (y/n): ")
                    if user_input.lower() != 'y':
                        print("Stopping dialogue generation.")
                        break
        except Exception as e:
            failed_count += 1
            print(f"Error generating dialogue {i+1}: {str(e)}")
            if not args.continue_on_error and args.count > 1:
                user_input = input("Continue generating dialogues? (y/n): ")
                if user_input.lower() != 'y':
                    print("Stopping dialogue generation.")
                    break
        
        # Add delay between API calls to avoid rate limiting, but only if there are more dialogues to generate
        if i < args.count - 1 and args.count > 1 and args.delay > 0:
            print(f"Waiting {args.delay} seconds before generating the next dialogue...")
            time.sleep(args.delay)
    
    if args.count > 1:
        print(f"\nGenerated {len(generated_files)} dialogue(s), failed {failed_count}:")
        for file in generated_files:
            print(f"- {file}")

if __name__ == "__main__":
    main() 