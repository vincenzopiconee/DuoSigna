""" This file contains the core of the bot, connected to PostgreSQL """

from sentence_transformers import SentenceTransformer
import models
import json
import os
import numpy as np
import io
from yt_dlp import YoutubeDL

# Vocal requirements
from kokoro import KPipeline
import soundfile as sf

# Helper files
from . import NLP_tools as NLP 
from . import config



# MUST BE THE SAME of build_embeddings.py
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
LLM_MODEL = "llama3.2"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CHUNK_PATH = os.path.join(CURRENT_DIR, "chunks_mapping.json")

SETTINGS = config.read_settings(CURRENT_DIR, 'settings.json')

# Initialize pipeline for Kokoro ('a' stands for american)
pipeline = KPipeline(lang_code='a', repo_id='hexgrad/Kokoro-82M')

AUDIO_FILE = os.path.join(CURRENT_DIR, "audio_instructions.wav")

#__________________________________________________________________________________
# --- LOAD DICTIONARIES ---

# Dictionary for letters
JSON_PATH = os.path.join(CURRENT_DIR, 'letters_signs.json')
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    LETTERS_DICTIONARY = json.load(f)

# Dictionary for NN signs
JSON_PATH = os.path.join(CURRENT_DIR, 'NN_signs.json')
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    NN_DICTIONARY = json.load(f)

# Dictionary for other words
JSON_PATH = os.path.join(CURRENT_DIR, 'signs.json')
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    ASL_DICTIONARY = json.load(f)

#__________________________________________________________________________________

# Caricamento Embeddings dizionario e generali
embeddings_path = os.path.join(CURRENT_DIR, 'embeddings.npy')
if os.path.exists(embeddings_path):
    DICTIONARY_EMBEDDINGS = np.load(embeddings_path)
else:
    raise FileNotFoundError(f"File {embeddings_path} non trovato!")

NN_embeddings_path = os.path.join(CURRENT_DIR, 'NN_embeddings.npy')
if os.path.exists(NN_embeddings_path):
    NN_EMBEDDINGS = np.load(NN_embeddings_path)
else:
    raise FileNotFoundError(f"File {NN_embeddings_path} non trovato!")

chunks_embeddings_path = os.path.join(CURRENT_DIR, 'embeddings_general.npy')
if os.path.exists(chunks_embeddings_path):
    CHUNKS_EMBEDDINGS = np.load(chunks_embeddings_path)
else:
    raise FileNotFoundError(f"File {chunks_embeddings_path} non trovato!")

#__________________________________________________________________________________

# --- Function to get intent and target word ---
def get_intent_and_word(client, clean_input):
    """
    Classify the intent by asking Llama 3.2
    """
    # Definte the task 
    complete_prompt = f"""Task: Classify the user's intent and extract the target word.
    Reply ONLY with the exact format: TYPE | TARGET
    - TYPE: write "translation" if the user wants to learn a sign, or "general" if it's a general question.
    - TARGET: the exact word the user wants to learn in English (or "null" if general).
    Do NOT use any special character like underscore or asterisks.

    Examples:
    User: "How do I sign "apple"?"
    Result: translation | apple

    User: "Show me the sign for running"
    Result: translation | running

    User: "What's the sign for speaking?"
    Result: translation | speaking

    User: "How can I do pizza?"
    Result: translation | pizza

    User: "Can you teach me "beautiful" in sign language?"
    Result: translation | beautiful

    User: "What is sign language?"
    Result: general | null

    User: "How many signs are there in ASL?"
    Result: general | null

    User: "What can you do?"
    Result: general | null

    User: "How do I sign 'quickly'?"
    Result: translation | quickly

    Now classify the following:
    User: "{clean_input}"
    Result:"""

    # Clean call to Ollama
    response = client.chat(model=LLM_MODEL, messages=[
        {'role': 'user', 'content': complete_prompt}
    ])
    
    intent_word = response['message']['content'].strip()

    # Unpack the output in intent and target
    try:
        intent, target = [x.strip() for x in intent_word.split("|")]
    except ValueError:
        intent, target = "general", "null"

    intent = intent.lower()
    target = target.lower()

    return intent, target

#__________________________________________________________________________________

# --- Function to search the sign in the dictionary ---
def search_sign(target):
    
    # 1. RICERCA ESATTA (Priorità massima a tutti i dizionari)
    if target in LETTERS_DICTIONARY:
        return target, LETTERS_DICTIONARY[target], "level_1"
    if target in NN_DICTIONARY:
        return target, NN_DICTIONARY[target], "level_2"
    if target in ASL_DICTIONARY:
        return target, ASL_DICTIONARY[target], "level_0"

    # 2. RICERCA PER ERRORI DI BATTITURA (Typo)
    closest_word_typo = NLP.find_closest_word_typo(NN_DICTIONARY, target)
    if closest_word_typo:
        print(f"I found a typo in NN! Returning closest word: {closest_word_typo}")
        return closest_word_typo, NN_DICTIONARY[closest_word_typo], "level_2"
        
    closest_word_typo = NLP.find_closest_word_typo(ASL_DICTIONARY, target)
    if closest_word_typo:
        print(f"I found a typo in General! Returning closest word: {closest_word_typo}")
        return closest_word_typo, ASL_DICTIONARY[closest_word_typo], "level_0"

    # 3. RICERCA SEMANTICA TRAMITE AI (Embeddings) - Solo se non abbiamo trovato nulla
    closest_word_meaning_index = NLP.find_closest_word_meaning(model, NN_EMBEDDINGS, target)
    if closest_word_meaning_index:
        closest_word_meaning = list(NN_DICTIONARY.keys())[closest_word_meaning_index[0]]
        print(f"I found a semantic match in NN! Returning closest word: {closest_word_meaning}")
        return closest_word_meaning, NN_DICTIONARY[closest_word_meaning], "level_2"

    closest_word_meaning_index = NLP.find_closest_word_meaning(model, DICTIONARY_EMBEDDINGS, target)
    if closest_word_meaning_index:
        closest_word_meaning = list(ASL_DICTIONARY.keys())[closest_word_meaning_index[0]]
        print(f"I found a semantic match in General! Returning closest word: {closest_word_meaning}")
        return closest_word_meaning, ASL_DICTIONARY[closest_word_meaning], "level_0"

    # Se non trova niente
    return target, None, ""
#__________________________________________________________________________________
# =================================================================================
# NUOVE FUNZIONI DI SUPPORTO PER IL DATABASE POSTGRESQL
# =================================================================================

def save_chat_message(db_session, chat_id, role, content, purpose=None, target_word=None, level=None, video_link_or_gif=None):
    """Salva un singolo messaggio nel database con metadati opzionali"""
    new_msg = models.ChatMessage(
        session_id=chat_id,
        role=role,
        content=content,
        purpose=purpose,
        target_word=target_word,
        level=level,
        video_link_or_gif=video_link_or_gif
    )
    db_session.add(new_msg)
    db_session.commit()

def get_chat_history(db_session, chat_id):
    """Recupera la cronologia formattata per Ollama"""
    messages = db_session.query(models.ChatMessage).filter(models.ChatMessage.session_id == chat_id).order_by(models.ChatMessage.created_at).all()
    # Formatta come si aspetta l'AI: [{'role': 'user', 'content': '...'}, ...]
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def get_full_chat_history(db_session, chat_id):
    """Recupera la cronologia completa con tutti i media per il Frontend"""
    messages = db_session.query(models.ChatMessage).filter(models.ChatMessage.session_id == chat_id).order_by(models.ChatMessage.created_at).all()
    
    return [{
        "role": msg.role, 
        "content": msg.content,
        "purpose": msg.purpose,
        "target_word": msg.target_word,
        "level": msg.level,
        "video_link_or_gif": msg.video_link_or_gif
    } for msg in messages]


def save_learned_word(db_session, user_id, word, instructions):
    """Salva la parola imparata solo se non esiste già per questo utente"""
    existing_word = db_session.query(models.LearnedSign).filter(
        models.LearnedSign.user_id == user_id,
        models.LearnedSign.word == word
    ).first()
    
    if not existing_word:
        new_word = models.LearnedSign(user_id=user_id, word=word, instructions=instructions)
        db_session.add(new_word)
        db_session.commit()

#__________________________________________________________________________________

# --- RAG to refine prompt ---
def refine_prompt(purpose, target_word, chat_history, clean_input, model):

    # Define a common instruction to remove formatting
    no_markdown_instruction = "Do not use markdown formatting, asterisks, or bold text. Plain text only."

    # Insert it at the chat beginning of the chat history
    if chat_history and chat_history[0]["role"] == "system":
        if no_markdown_instruction not in chat_history[0]["content"]:
            chat_history[0]["content"] += no_markdown_instruction

    # --- Refine prompt for translation case (using RAG) ---
    if purpose == 'translation':
        # See if it is present
        found_target_word, instructions, level = search_sign(target_word)
        
        # We found the word! Add context to the prompt        
        if instructions and target_word == found_target_word:
            injection = f"""\nDo not use markdown formatting, asterisks, or bold text. Plain text only.
                        \nThe user wants to translate '{target_word}'.
                        Here are the instructions to perform the sign: '{instructions}'. 
                        Provide the instructions clearly. """
            chat_history[-1]["content"] += injection 
        
        # Word not found but found a typo or a similar meaning word
        elif instructions and target_word != found_target_word:

            injection = f"""\nDo not use markdown formatting, asterisks, or bold text. Plain text only.
                            \nThe user wants to translate '{target_word}', but it is not in the dictionary. 
                            Apologize and offer as alternative '{found_target_word}'. 
                            Here the instructions to perform the sign: '{instructions}'.
                            Provide the instructions clearly. """
            chat_history[-1]["content"] += injection

        # Word not found, neither a typo or a similar meaning word
        else:
            injection = f"""\nDo not use markdown formatting, asterisks, or bold text. Plain text only.
                            \nThe user wants to translate '{target_word}', but it is not in the dictionary. 
                            Apologize and tell the user you are a prototype that cannot answer everything yet. """
            chat_history[-1]["content"] += injection

        return chat_history, instructions, level, found_target_word


    # --- Refine prompt for general question case (using RAG) ---
    elif purpose == 'general':
        with open(CHUNK_PATH, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        # Retrieve most correlated informations
        context = NLP.find_closest_chunks(model, CHUNKS_EMBEDDINGS, clean_input, chunks)

        if context:
            injection = f"""Do not use markdown formatting, asterisks, or bold text. Plain text only.
                            You are a helpful ASL (American Sign Language) assistant.
                            Use the following knowledge base excerpts to answer the user's question accurately.

                            Relevant information:
                            {context}

                            User question: "{clean_input}"
                            Answer:"""
            chat_history[-1]["content"] += injection
        else:
            injection = f"""Do not use markdown formatting, asterisks, or bold text. Plain text only.
                            You are a helpful ASL (American Sign Language) assistant.
                            Answer the following question about ASL as best as you can.

                            User question: "{clean_input}"
                            Answer:"""
            chat_history[-1]["content"] += injection

    level = ""

    return chat_history, None, level, None

#__________________________________________________________________________________

# --- Function to generate a link for a target word ---
def generate_yt_link(target_word):
    """ Function to create a link to a youtube video explaining how to perform a target sign """

    # Create query for the target word
    query = "how can I perform " + target_word + "in ASL language"

    ydl_opts = {
        "quiet": True,
        "extract_flat": True
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch1:{query}", download=False)

    video = info["entries"][0]

    # Generate url for the first result
    video_url = f"https://www.youtube.com/watch?v={video['id']}"

    # Return url
    return video_url

#__________________________________________________________________________________

# --- Function to generate audio trace ---
def generate_audio_trace(instructions):
    # Generate the audio: af_heart --> female voice, am_fenrir --> male voice
    generator = pipeline(
        instructions,
        voice='af_heart',
        speed=1.0,
        split_pattern=r'\n+'
    )

    # Merge various audio chunks
    complete_audio = []

    for i, (graphemes, phonemes, audio) in enumerate(generator):
        complete_audio.append(audio)

    # Concatenate chunks and save file
    try:
        final_audio = np.concatenate(complete_audio)
        sf.write(AUDIO_FILE, final_audio, 24000) # 24 kHz is the std sample rate
    except ValueError as e:
        print(e)




#streaming audio
def generate_audio_stream(text):
    """ Script that generates audio and returns it as a stream of bytes in memory """
    generator = pipeline(
        text,
        voice='af_heart',
        speed=1.0,
        split_pattern=r'\n+'
    )

    complete_audio = []
    for i, (graphemes, phonemes, audio) in enumerate(generator):
        complete_audio.append(audio)

    if not complete_audio:
        return None

    final_audio = np.concatenate(complete_audio)
    
    # Scriviamo l'audio in un buffer di memoria invece che su disco
    buffer = io.BytesIO()
    sf.write(buffer, final_audio, 24000, format='WAV')
    buffer.seek(0) # Riporta il cursore all'inizio del file virtuale
    
    return buffer
#__________________________________________________________________________________

# --- Function to start a chat ---
def chat(client, user_input, db_session, user_id, chat_id, is_new_chat):
    """ Function to chat with the bot. Manages new and alredy existent chats """
    
    # --- PROMPT PROCESSING ---

    # System prompt loading
    system_prompt = SETTINGS.get("system_prompt", "You are an ASL tutor.")
    chat_history = [{"role": "system", "content": system_prompt}]

    # Retrieve history if it is an existent chat
    if not is_new_chat:
        saved_messages = get_chat_history(db_session, chat_id)
        chat_history.extend(saved_messages)

    # Save new user message to database
    save_chat_message(db_session, chat_id, "user", user_input)
    chat_history.append({"role": "user", "content": user_input})

    # Analyze the input to get the intent
    #clean_input = NLP.process(user_input)
    clean_input = user_input.strip()
    purpose, target_word = get_intent_and_word(client, clean_input)

    # Refine the prompt using RAG
    chat_history, instructions, level, final_target_word = refine_prompt(purpose, target_word, chat_history, clean_input, model)

    # --- ANSWER GENERATION ---

    # Call Ollama
    response = client.chat(model=LLM_MODEL, messages=chat_history)
    answer = response['message']['content']


    # --- VIDEO or GIF PROPOSE ---
    
    # Translation video/gif management
    if purpose == 'translation':
        # Create link if not present
        if level == "level_0":
            video_link_or_gif = generate_yt_link(final_target_word)

        # Retrieve gif if present
        elif level == "level_1" or level == "level_2": 
            video_link_or_gif = f"gif_output/{final_target_word}.gif"
            
        # AGGIUNTO: Fallback se la parola non è stata trovata (level è vuoto)
        else:
            video_link_or_gif = None

    # Fallback per domande generali             
    else:
        video_link_or_gif = None



    # Save bot answer to database
    # --- MODIFICA: Usiamo la parola alternativa suggerita (se esiste) al posto di quella originale
    actual_target = final_target_word if purpose == 'translation' and final_target_word else target_word

    # Save bot answer to database
    save_chat_message(db_session, chat_id, "assistant", answer, purpose, actual_target, level, video_link_or_gif)
    chat_history.append({"role": "assistant", "content": answer})

    
    # --- TITLE GENERATION ---

    if is_new_chat:
        # Generate the title (short summary or word to learn)
        title = update_title(client, chat_id, db_session, purpose, final_target_word, chat_history)
    else:
        # Fallback
        title = None 

    # --- AUDIO TRACE GENERATION ---

    # Save the audio trace if we have instructions to reproduce
    #if purpose == 'translation':
        #generate_audio_trace(instructions)
        #generate_audio_trace(answer)

    # Return data to the front end 
    return {
        "chat_id": chat_id,
        "answer": answer,
        "purpose": purpose,
        "target_word": actual_target,
        "updated_history": chat_history,
        "title": title,
        "video_link_or_gif": video_link_or_gif,
        "level": level
    }

#__________________________________________________________________________________

# --- Function to give a title to a chat and save it in the database ---
def update_title(client, chat_id, db_session, purpose, target_word, chat_history):
      
    # If purpose is translation use a standard "Learning _word_"
    if purpose == 'translation':
        title = f"Learning: {target_word.upper()}"

    # If general question do a summary
    else:
        # Retrieve chat messages from database --> if we want to update dinamically the title
        # chat_history = db_session.query(models.ChatMessage).filter(models.ChatMessage.session_id == chat_id).order_by(models.ChatMessage.created_at).all()
   
        # Transform the conversation in a long string
        chat_couples = []
        for msg in chat_history:
            chat_couples.append(f"{msg['role']}: {msg['content']}")
        
        chat_text = "\n".join(chat_couples)

        # Eventually consider just the first 4000 chars
        #if len(chat_text) > 4000:
        #    chat_text = chat_text[-4000:]

        # Call summarizer
        title = NLP.summarize(client, chat_text)

    # Update in PostgreSQL
    session_record = db_session.query(models.ChatSession).filter(models.ChatSession.id == chat_id).first()
    if session_record:
        session_record.title = title
        db_session.commit()
        
    return title


