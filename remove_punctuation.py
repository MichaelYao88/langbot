import json
import os
import re
import glob

def remove_punctuation_from_dialogue(json_file):
    """
    Remove punctuation from the 'text' field in dialogue JSON files
    while preserving the rest of the structure and any HTML-like tags.
    
    Args:
        json_file: Path to the dialogue JSON file
    """
    # Load the JSON file
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check if this is a dialogue file with the expected structure
    if 'dialogue' not in data:
        print(f"Warning: {json_file} does not contain a 'dialogue' field. Skipping.")
        return False
    
    # Process each dialogue entry
    modified = False
    for entry in data['dialogue']:
        if 'text' in entry:
            # Store the original text
            original_text = entry['text']
            
            # First, identify and protect Vietnamese tags
            # Find all Vietnamese tag pairs and their content
            vietnamese_tags = re.findall(r'<vietnamese>([^<]+)</vietnamese>', original_text)
            text_with_placeholders = original_text
            
            # Replace each Vietnamese tag pair with a special token
            viet_tag_map = {}
            for i, viet_content in enumerate(vietnamese_tags):
                placeholder = f"__VIET_TAG_{i}__"
                viet_tag_map[placeholder] = f"<vietnamese>{viet_content}</vietnamese>"
                text_with_placeholders = text_with_placeholders.replace(
                    f"<vietnamese>{viet_content}</vietnamese>", 
                    placeholder
                )
            
            # Also preserve other HTML-like tags
            other_tags = re.findall(r'<[^>]+>', text_with_placeholders)
            for i, tag in enumerate(other_tags):
                placeholder = f"__HTML_TAG_{i}__"
                viet_tag_map[placeholder] = tag
                text_with_placeholders = text_with_placeholders.replace(tag, placeholder)
            
            # Also preserve parenthetical expressions like (vietnamese)
            parenthetical_expressions = re.findall(r'\([^)]+\)', text_with_placeholders)
            for i, expr in enumerate(parenthetical_expressions):
                placeholder = f"__PAREN_{i}__"
                viet_tag_map[placeholder] = expr
                text_with_placeholders = text_with_placeholders.replace(expr, placeholder)
            
            # Now remove punctuation but preserve spaces
            cleaned_text = re.sub(r'[.,!?;:"\[\]\{\}]', '', text_with_placeholders)
            
            # Restore the tags and parenthetical expressions
            for placeholder, content in viet_tag_map.items():
                cleaned_text = cleaned_text.replace(placeholder, content)
            
            # Update the text field if changes were made
            if cleaned_text != original_text:
                entry['text'] = cleaned_text
                modified = True
    
    # Save the modified JSON if changes were made
    if modified:
        output_file = json_file.replace('.json', '_no_punctuation.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Processed {json_file} -> {output_file}")
        return True
    else:
        print(f"No punctuation found in {json_file}")
        return False

def main():
    # Find all dialogue JSON files in the data/audio directory
    dialogue_files = glob.glob('data/audio/dialogue_*.json')
    
    # Filter out any files that already have '_no_punctuation' in their name
    dialogue_files = [f for f in dialogue_files if '_no_punctuation' not in f]
    
    if not dialogue_files:
        print("No dialogue JSON files found in data/audio directory.")
        return
    
    print(f"Found {len(dialogue_files)} dialogue JSON files to process.")
    
    # Process each file
    processed_count = 0
    for file_path in dialogue_files:
        if remove_punctuation_from_dialogue(file_path):
            processed_count += 1
    
    print(f"Completed processing {processed_count} files.")

if __name__ == "__main__":
    main() 