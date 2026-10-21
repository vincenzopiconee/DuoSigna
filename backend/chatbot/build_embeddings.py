""" Run it only if modify the dictionary with the instructions """


# To run it:        uvicorn build_embeddings:app --reload


import json
import re
from sentence_transformers import SentenceTransformer
import numpy as np
import os
from pypdf import PdfReader
import ollama
from fastapi import FastAPI, UploadFile, File, HTTPException
import shutil

app = FastAPI(title="ASL Dictionary API - Local Ollama")

# Global variables
PDF_NAME = 'ASL_dict.pdf'
TXT_NAME = 'asl_general_knowledge.txt'
DICT_JSON = 'signs.json'
NN_DICT_JSON = 'NN_signs.json'
MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
OLLAMA_MODEL = "llama3.2" 
OUTPUT_FILE = 'embeddings.npy'
NN_OUTPUT_FILE = 'NN_embeddings.npy'
OUTPUT_FILE_GENERAL = 'embeddings_general.npy'
TO_FILTER_DICT = "to_filter_signs.json"
CHUNK_PATH = 'chunks_mapping.json'

#_____________________________________________________________

# --- Function to clean a dictionary with instructions generated from a pdf file ---
def filter_asl_dictionary(input_file=TO_FILTER_DICT, output_file=DICT_JSON):
    print(f"Loading file: {input_file}...")
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return

    filtered_data = {}
    eliminated_count = 0

    # Grammatical and theoretical terms to exclude
    grammar_terms = [
        'grammar', 'verb', 'adverb', 'classifiers', 'classifier', 
        'shifting', 'gazing', 'space', 'tense', 'pronoun', 'plural', 'sign language'
    ]

    # "Physical" words required to consider the row a valid ASL instruction
    physical_keywords = [
        'hold', 'move', 'point', 'touch', 'make', 'extend', 'palm', 'finger', 'hand', 'arm', 'head', 'shake', 'nod', 
        'draw', 'mimic', 'rub', 'place', 'bend', 'clench', 'curl', 'tap', 'wave', 'smile', 'look', 'tilt', 'raise', 
        'spread', 'circle', 'motion', 'shape', 'squeeze', 'sweep', 'slide', 'wiggle', 'bounce', 'jump', 'run', 'walk',
        'flick', 'press', 'turn', 'cross', 'pull', 'push', 'twirl', 'shrug'
    ]

    # Typical phrases for meta-descriptions or text comments useless for movements
    exclude_keywords = [
        'not explicitly described', 'same sign', 'same as', 'used to', 'refers to', 'derived from', 'translated as', 
        'can be used', 'not necessary', 'a new sign', 'a compound', 'the rules', 'words or phrases', 'is an example', 
        'is not initialized', 'no explicit description', 'implied to be', 'a highly controversial', 'established in',
        'means', 'often signed by itself', 'make a remark', 'ask a question', 'describe the topic', 
        'signal the start', 'determine which', 'use all ten', 'also used for', 'exception relating to', 'the correct nonmanual signals are',
        'indicate the future time', 'establishes the tense', 'point right', 'point left', 'answer the question',
        'implied context', 'various hand shapes', 'nonmanual signals', 'simply repeating', 'the same manner',
        'a sign used', 'the phrase', 'same handshape', 'a number of ways', 'there is no difference'
    ]

    for key, value in data.items():
        keep = True
        
        # Discard if key or value is empty or null
        if not key or not value or not isinstance(key, str) or not isinstance(value, str):
            keep = False
        else:
            val_lower = value.lower()
            key_lower = key.lower()
            
            # --- RULE A: Key length and complexity ---
            # Remove empty or overly long/complex keys (a sign is usually 1-3 words, not a sentence).
            # Also remove keys containing punctuation typical of questions or descriptive sentences.
            if not value.strip() or len(key.split()) > 3 or "?" in key or "," in key or ":" in key or "." in key:
                keep = False
                
            # --- RULE B: Remove pronouns in phrase contexts ---
            # E.g.: "YOU GO-TO" or "she-HELP-him"
            words = re.findall(r'\b\w+\b', key_lower)
            if any(w in ['me', 'you', 'he', 'she', 'it', 'they', 'we'] for w in words) and len(words) > 1:
                keep = False
                
            # Specific words to drop if present in the key
            if "sweep" in key_lower or "point" in key_lower:
                keep = False
                
            # --- RULE C: Remove grammatical terms ---
            if any(gt in key_lower for gt in grammar_terms):
                keep = False
                
            # --- RULE D: Check Definition Content ---
            # Discard if it contains meta-description phrases
            if any(ex in val_lower for ex in exclude_keywords):
                keep = False
            # Discard if it DOES NOT contain at least one word describing a physical action
            elif not any(pk in val_lower for pk in physical_keywords):
                keep = False

        # Add to filtered dictionary or increment eliminated count
        if keep:
            filtered_data[key.lower().strip()] = value
        else:
            eliminated_count += 1

    # Save the new file in alphabetical order
    print("Filtering completed!")
    print(f"Signs eliminated: {eliminated_count}")
    print(f"Signs kept: {len(filtered_data)}")
    
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(filtered_data, f, indent=4, ensure_ascii=False, sort_keys=True)
        print(f"New dictionary saved in: {output_file}")
        return filtered_data
    
    except Exception as e:
        print(f"Error during saving: {e}")
        return {}

#_____________________________________________________________

# --- Function to get a dictionary with instructions from a pdf file ---
def generate_instruction_dictionary(input_file_name, output_file_name, model_name="llama3.2", chunk_size=20):
    # Initialize the master dictionary that will hold all the chunks combined
    master_dictionary = {}

    # --- Read pdf ---
    try:
        # Initialize a reader linked with the file path
        current_path = os.getcwd()
        file_path = os.path.join(current_path, input_file_name)
        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        
        print(f"Starting to process {total_pages} pages in chunks of {chunk_size}...")

    except Exception as e:
        print(f"Error during pdf reading: {e}")
        return {} # Fallback

    # --- Process pages in chunks ---
    for i in range(0, total_pages, chunk_size):
        chunk_text_list = []
        
        # Calculate the end page of the current chunk
        end_page = min(i + chunk_size, total_pages)
        
        # Read pages for the current chunk
        for j in range(i, end_page):
            page_text = reader.pages[j].extract_text()
            if page_text:
                chunk_text_list.append(page_text)
        
        # Join in a single text block for this chunk
        extracted_text = "\n--- FOLLOWING PAGE ---\n".join(chunk_text_list)
        
        # Skip empty chunks (e.g., pages with only images)
        if not extracted_text.strip():
            continue
            
        print(f"Processing pages {i + 1} to {end_page}...")

        # --- Call the LLM to generate the dictionary for the chunk ---

        # Define prompt
        prompt = f"""You are a specialized data extractor. Your task is to analyze the provided text and extract all single words or concepts for which the corresponding American Sign Language (ASL) gesture is explicitly explained.

        Strict rules:
        1. Return EXCLUSIVELY a single valid JSON object.
        2. Use the word or concept to be signed as the KEY.
        3. Use the textual description of the body or hand movements as the VALUE.
        4. Do not add introductions, conclusions, or text outside the JSON.
        5. If there are no descriptions of ASL gestures in the text, return an empty dictionary: {{}}

        Text to analyze:
        {extracted_text}"""

        # --- Get the answer and update the master dictionary ---
        try:
            # Generate answer
            llm_response = ollama.generate(
                model=model_name,
                prompt=prompt,
                format='json'
            )

            # Cleans up any accidental spaces or line breaks at the beginning/end
            clean_string = llm_response['response'].strip()
            
            # Load the JSON chunk
            chunk_dictionary = json.loads(clean_string)
            
            # Update the master dictionary with the new signs
            master_dictionary.update(chunk_dictionary)
            
        # Fallbacks for the specific chunk
        except json.JSONDecodeError:
            print(f"Error: Ollama did not return a valid JSON for pages {i+1}-{end_page}.")
            continue # Move to the next chunk without crashing
        except Exception as e:
            print(f"Error during interaction with Ollama on pages {i+1}-{end_page}: {e}")
            continue # Move to the next chunk without crashing

    # --- Save the complete dictionary in a json file ---
    try:
        # --- First save the dictionary in a temporary json file ---
        with open(TO_FILTER_DICT, 'w', encoding='utf-8') as f:
            json.dump(master_dictionary, f, ensure_ascii=False, indent=4)
            
        # --- Filter to remove errors and save the dictionary ---
        filtered_asl_dict = filter_asl_dictionary(input_file=TO_FILTER_DICT, output_file=DICT_JSON)

        # Return the filtered dictionary
        return filtered_asl_dict

    except Exception as e:
        print(f"Error saving the json file: {e}")
        return filtered_asl_dict
    
#_____________________________________________________________

# --- Function to save the embeddings from the dictionary ---

""" Run it only if modify the dictionary with the instructions """

def generate_and_save_embeddings(json_path, model_name, output_path):
    print("Loading model...")
    model = SentenceTransformer(model_name)
    
    print(f"Loading dictionary from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        ASL_DICTIONARY = json.load(f)
    
    words = list(ASL_DICTIONARY.keys())
    
    print(f"Generating embedding for {len(words)} words (Could require time) ...")
    embeddings = model.encode(words)
    
    # Save embedding in .npy format
    np.save(output_path, embeddings)
    print(f"Embedding saved at: {output_path}")

#_____________________________________________________________

# --- Function to save the embeddings from the general info file ---

""" Run it only if modify the general informations """

def generate_and_save_embeddings_general(txt_path, model_name, output_path):
    # Load model
    print("Loading model...")
    model = SentenceTransformer(model_name)
    
    # Load informations
    print(f"Loading Q&A chunks from {txt_path}...")
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split based on numbers that introduce a question
    chunks = re.split(r'\n(?=\d+\.)', content.strip())

    # Remove intestation
    chunks = [c.strip() for c in chunks if re.match(r'^\d+\.', c.strip())]
    
    # Create embeddings
    print(f"Found {len(chunks)} Q&A chunks. Generating embeddings...")
    embeddings = model.encode(chunks)
    
    # Save embedding in .npy format
    np.save(output_path, embeddings)
    print(f"Embedding saved at: {output_path}")

    # Return possibly useful map: index -> complete_chunck
    return chunks

#_____________________________________________________________

# --- Route to generate a dictionary ---
@app.post("/generate-dictionary/")
async def create_dictionary():
    # Check correct pdf input
    if not os.path.exists(PDF_NAME):
        raise HTTPException(status_code=404, detail=f"File {PDF_NAME} not found in the folder.")

    try:

        # Call the appostie function to generate and save json    
        asl_dict = generate_instruction_dictionary(PDF_NAME, DICT_JSON, model_name=OLLAMA_MODEL, chunk_size=5)
        
        # Error management
        if not asl_dict:
            raise HTTPException(status_code=500, detail="Error in Json generation.")

        # Return answer to the client
        return {
            "message": f"Dictionary generated successfully with Ollama ({OLLAMA_MODEL})!",
            "file_saved": DICT_JSON,
            "data": asl_dict
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
            
#_____________________________________________________________

# --- Route to generate embeddings for the dictionary ---
@app.post("/generate-embeddings/")
async def create_embeddings():
    # Call my function generate_and_save_embeddings
    generate_and_save_embeddings(DICT_JSON, MODEL_NAME, OUTPUT_FILE)
    return {"message": "Embeddings generated and saved in embeddings.npy"}

#_____________________________________________________________

# --- Route to generate embeddings for the general knowledge ---
@app.post("/generate-embeddings-general/")
async def create_embeddings_general():
    # Call my function generate_and_save_embeddings
    chunks = generate_and_save_embeddings_general(TXT_NAME, MODEL_NAME, OUTPUT_FILE_GENERAL)

    output_path = CHUNK_PATH 
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"Chunks saved at: {output_path}")

    return {"message": "Embeddings generated and saved in embeddings_general.npy"}

#_____________________________________________________________

# --- Route to generate embeddings for the NN dictionary ---
@app.post("/generate-embeddings-NN/")
async def create_embeddings_NN():
    # Call my function generate_and_save_embeddings
    generate_and_save_embeddings(NN_DICT_JSON, MODEL_NAME, NN_OUTPUT_FILE)
    return {"message": "Embeddings generated and saved in NN_embeddings.npy"}

#_____________________________________________________________

# --- Route to generate a dictionary ---
@app.post("/clean-dictionary/")
async def clean_dictionary():
    # Call my function to clean the dictionary
    filter_asl_dictionary(TO_FILTER_DICT, DICT_JSON)
    return {"message": "Correctly filtered dictionary."}

#_____________________________________________________________

