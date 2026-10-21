import os
import warnings

# 1. Nasconde il saluto fastidioso di Pygame ("Hello from the pygame community")
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

# 2. Nasconde le barre di caricamento di Kokoro/HuggingFace (opzionale ma consigliato)
os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = "1"

# 3. Silenzia gli avvisi di PyTorch e Scikit-Learn
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from security import hash_password, verify_password, create_access_token
from typing import Optional
from typing import List
from pydantic import BaseModel
import jwt
from security import SECRET_KEY, ALGORITHM
import quiz  
from sqlalchemy.orm import Session
from fastapi import Depends
from chatbot import bot_core as bot
from chatbot import vision_core_l1
import traceback
import tensorflow as tf
import pygame 

from chatbot import vision_core
import json
import numpy as np
from ollama import Client
from fastapi.staticfiles import StaticFiles

from fastapi.responses import StreamingResponse
from pydantic import BaseModel


# --- AGGIORNAMENTO PERCORSI ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ora i file sono dentro la sottocartella 'chatbot'
CHATBOT_DIR = os.path.join(BASE_DIR, 'chatbot')

AUDIO_FILE_PATH = os.path.join(CHATBOT_DIR, 'audio_instructions.wav')

# Dictionary for letters
JSON_PATH = os.path.join(CHATBOT_DIR, 'letters_signs.json')
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    LETTERS_DICTIONARY = json.load(f)

# Dictionary for NN signs
JSON_PATH = os.path.join(CHATBOT_DIR, 'NN_signs.json')
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    NN_DICTIONARY = json.load(f)

# Caricamento del Modello di Riconoscimento Segni (TensorFlow)
ZIP_PATH = os.path.join(CHATBOT_DIR, 'asl_pure_tf_blackbox.zip')
EXTRACT_DIR = os.path.join(CHATBOT_DIR, '_savedmodel_extracted')
SIGN_MAP_PATH = os.path.join(CHATBOT_DIR, 'sign_to_prediction_index_map.json')

LABELS = vision_core.load_labels(SIGN_MAP_PATH)
infer_sign = vision_core.load_savedmodel(ZIP_PATH, EXTRACT_DIR)


# Crea le tabelle nel database all'avvio
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configurazione CORS per accettare richieste dai tunnel pubblici
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permette l'accesso a qualsiasi frontend (incluso il tunnel di VS Code)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sostituisci BASE_DIR se gif_output si trova da un'altra parte, 
# ma se è nella root del backend questo andrà bene:
app.mount("/gif_output", StaticFiles(directory=os.path.join(BASE_DIR, "gif_output")), name="gif_output")



# 1. Configurazione Client Ollama
# Usa l'IP del computer che fa girare Llama (o 'http://localhost:11434')
client = Client(host='http://127.0.0.1:11434')





# --- CONFIGURAZIONE CORS ---
# Diciamo al backend di accettare le chiamate provenienti dal tuo Frontend Nuxt
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Il tuo frontend Nuxt
        "http://127.0.0.1:3000",   # Frontend Nuxt tramite IP
        "http://localhost:8000",   # Swagger docs (localhost)
        "http://127.0.0.1:8000",   # Swagger docs (IP)
    ],    allow_credentials=True,
    allow_methods=["*"], # Permette POST, GET, OPTIONS, ecc.
    allow_headers=["*"], # Permette l'invio dei Token e altri header
)

# Schemi Pydantic (uguali a prima)
class UserCreate(BaseModel):
    nome: str
    email: str
    password: str
    avatar_url: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class AvatarUpdate(BaseModel):
    avatar_url: str

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Controlla se esiste già
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_pwd = hash_password(user.password)
    
    new_user = models.User(
        nome=user.nome,
        email=user.email,
        hashed_password=hashed_pwd,
        avatar_url=user.avatar_url
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully on Postgres!"}

@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Wrong credentials")
    
    # MODIFICA QUI: Creiamo il token usando l'ID univoco e immutabile dell'utente!
    token = create_access_token({"sub": str(db_user.id)})
    
    return {"access_token": token, "token_type": "bearer"}

# Funzione per recuperare l'utente dal token (Middleware manuale)
# Funzione per recuperare l'utente dal token
async def get_current_user(token: str, db: Session):
    try:
        # Decodifichiamo il token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub_val = payload.get("sub")
        
        if sub_val is None:
            return None
            
        sub_str = str(sub_val)
        
        # Se è un vecchio token che usava la mail, cerchiamo per mail
        if "@" in sub_str:
            return db.query(models.User).filter(models.User.email == sub_str).first()
        # Se è un nuovo token (best practice), cerchiamo per ID immutabile
        else:
            return db.query(models.User).filter(models.User.id == int(sub_str)).first()
            
    except Exception:
        return None

@app.put("/update-avatar")
async def update_avatar(
    request: AvatarUpdate, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    # Aggiorna l'URL nel database
    user.avatar_url = request.avatar_url
    db.commit()
    
    return {"message": "Avatar updated successfully!", "avatar_url": user.avatar_url}

@app.get("/me")
# Aggiungiamo Header(None) per dire a FastAPI di cercare negli "Headers" nascosti
async def get_me(db: Session = Depends(get_db), authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Token missing in headers")
    
    # Rimuoviamo la parola 'Bearer ' se presente
    token = authorization.replace("Bearer ", "")
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Token not valid")
        
    return {
        "nome": user.nome,
        "email": user.email,
        "score": user.score,
        "avatar_url": user.avatar_url,
        "has_completed_onboarding": user.has_completed_onboarding
    }

@app.post("/complete-onboarding")
async def complete_onboarding(db: Session = Depends(get_db), authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # Aggiorna il database
    user.has_completed_onboarding = True
    db.commit()
    
    return {"message": "Onboarding saved successfully!"}

# --- ROTTA DI LOGOUT ---
@app.post("/logout")
async def logout():
    # Poiché usiamo i JWT, il vero logout avviene sul frontend cancellando il token.
    # Questa rotta serve solo per rispondere "OK" a NuxtAuth e non dargli l'errore 404.
    return {"message": "Logout successfully completed on the server"}

class ChatRequest(BaseModel):
    question: str 
    chat_id: Optional[int] = None # Se è None, è una nuova chat

@app.post("/chat")
async def chat_with_bot(
    request: ChatRequest, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None) # Proteggiamo la rotta!
):
    # 1. Recuperiamo l'utente dal token (usa la funzione che avevamo creato per /me)
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    # 2. Logica: è una nuova chat o una continuazione?
    if request.chat_id is None:
        # Crea una nuova sessione nel DB per questo utente
        new_session = models.ChatSession(user_id=user.id)
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        chat_id = new_session.id
        
        # Chiama il bot per una nuova chat
        risposta_bot = bot.chat(client, request.question, db, user.id, chat_id, is_new_chat=True)
    
    else:
        chat_id = request.chat_id
        risposta_bot = bot.chat(client, request.question, db, user.id, chat_id, is_new_chat=False)
        
        # Recupera il vecchio titolo dalla chat id, controllando che esista e sia associata a quell'user 
        chat_session = db.query(models.ChatSession).filter(
            models.ChatSession.id == chat_id,
            models.ChatSession.user_id == user.id
        ).first()

        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat not found or not authorized")
        
        risposta_bot["title"] = chat_session.title

    return risposta_bot

class SignRecognitionRequest(BaseModel):
    # Ci aspettiamo una lista di frame. Ogni frame è una matrice 543x3.
    frames: list 
    target_word: str

@app.post("/recognize-sign")
async def recognize_sign(
    request: SignRecognitionRequest, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    # 1. Recupero dell'utente (necessario per salvare i progressi)
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    try:
        # Applichiamo la matematica ai dati grezzi in arrivo dalla webcam
        processed_data = vision_core.preprocess_sequence(request.frames)
        
        # Chiediamo a TensorFlow di fare la predizione
        logits = infer_sign(processed_data)
        
        # Estraiamo la parola più probabile
        probs = tf.nn.softmax(logits).numpy()
        top_idx = int(np.argmax(probs))
        top_p = float(probs[top_idx])
        
        predicted_word = LABELS[top_idx] if len(LABELS) > 0 else f"#{top_idx}"

        # --- MODIFICA: La parola è corretta e da salvare SOLO se >= 65% ---
        is_correct = (predicted_word.lower() == request.target_word.lower() and top_p >= 0.65)

        # 2. SALVATAGGIO DELLA PAROLA NEL DATABASE SE CORRETTA E CON ALTA CONFIDENZA
        if is_correct:
            existing_word = db.query(models.LearnedSign).filter(
                models.LearnedSign.user_id == user.id,
                models.LearnedSign.word == request.target_word.lower()
            ).first()
            
            if not existing_word:
                new_word = models.LearnedSign(
                    user_id=user.id, 
                    word=request.target_word.lower(), 
                    instructions="Unlocked with accuracy >= 65%"
                )
                db.add(new_word)
                db.commit()

        return {
            "predicted_word": predicted_word,
            "confidence": top_p,
            "is_correct": is_correct
        }
        
    except Exception as e:
        traceback.print_exc() 
        raise HTTPException(status_code=500, detail=f"Error during visual analysis: {str(e)}")
    

@app.post("/recognize-letter")
async def recognize_letter(
    request: SignRecognitionRequest, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    """Rotta dedicata esclusivamente al Livello 1 (Lettere e Feedback Geometrico)"""
    
    # --- MODIFICA: Aggiunto collegamento Utente e Database per salvare le lettere ---
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    try:
        # Otteniamo il risultato base dal motore geometrico
        result = vision_core_l1.evaluate_letter(request.frames, request.target_word)
        
        # --- MODIFICA: Sovrascriviamo is_correct per forzare la regola dell'65% ---
        is_correct_65 = (result["predicted_word"].lower() == request.target_word.lower() and result["confidence"] >= 0.65)
        result["is_correct"] = is_correct_65

        # Salviamo la lettera nel Database solo se ha superato l'65%
        if is_correct_65:
            existing_word = db.query(models.LearnedSign).filter(
                models.LearnedSign.user_id == user.id,
                models.LearnedSign.word == request.target_word.lower()
            ).first()
            
            if not existing_word:
                new_word = models.LearnedSign(
                    user_id=user.id, 
                    word=request.target_word.lower(), 
                    instructions="Unlocked with accuracy >= 65%"
                )
                db.add(new_word)
                db.commit()

        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error analyzing Level 1: {str(e)}")
    
# ==========================================
# ROTTA PER L'AUDIO
# ==========================================

class AudioRequest(BaseModel):
    text: str


# Funzione helper per riprodurre audio
@app.post("/synthesize-audio")
async def synthesize_audio_track(
    request: AudioRequest, 
    authorization: str = Header(None)
):
    # Protezione della rotta opzionale
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authorized")

    try:
        # Genera il buffer audio dalla nostra nuova funzione in bot_core
        audio_buffer = bot.generate_audio_stream(request.text)
        
        if not audio_buffer:
             raise HTTPException(status_code=500, detail="Error generating audio")

        # Restituisce lo stream al frontend specificando che è un file audio
        return StreamingResponse(audio_buffer, media_type="audio/wav")
        
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Internal Error TTS")
    


# ==========================================
# ROTTE PER LA CRONOLOGIA DELLE CHAT
# ==========================================

# 1. Recupera la lista di tutte le chat dell'utente
@app.get("/chats")
async def get_user_chats(
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # Cerca nel database tutte le chat appartenenti all'utente loggato, ordinate dalla più recente
    chats = db.query(models.ChatSession)\
              .filter(models.ChatSession.user_id == user.id)\
              .order_by(models.ChatSession.created_at.desc())\
              .all()
    
    # Formatta la risposta per il frontend
    return [
        {
            "id": str(chat.id), # Assicuriamoci che l'ID sia stringa per Vue
            "title": chat.title or "New Chat", # Fornisci un titolo di default se è vuoto
            "date": chat.created_at.strftime("%Y-%m-%d") if chat.created_at else "Today" 
        } 
        for chat in chats
    ]

# 2. Recupera i messaggi specifici di una chat (usando la funzione già presente in bot_core)
@app.get("/chat/{chat_id}")
async def get_chat_history_route(
    chat_id: int, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    # Prima controlla se la chat appartiene a questo utente per sicurezza
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.id == chat_id,
        models.ChatSession.user_id == user.id
    ).first()

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat not found or not authorized")

    # Usa la funzione get_full_chat_history che avevi già nel bot_core
    messages = bot.get_full_chat_history(db, chat_id)
    
    return {"messages": messages}


@app.delete("/chat/{chat_id}")
async def delete_chat(
    chat_id: int, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    # 1. Cerca la chat, assicurandoti che appartenga all'utente loggato
    chat_session = db.query(models.ChatSession).filter(
        models.ChatSession.id == chat_id,
        models.ChatSession.user_id == user.id
    ).first()

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat not found or not authorized")

    try:
        # 2. ELIMINA PRIMA I MESSAGGI: Evita l'errore di Foreign Key in PostgreSQL
        db.query(models.ChatMessage).filter(models.ChatMessage.session_id == chat_id).delete()
        
        # 3. ELIMINA LA SESSIONE DELLA CHAT
        db.delete(chat_session)
        db.commit()
        
        return {"message": "Chat deleted successfully!"}
        
    except Exception as e:
        db.rollback()
        print(f"Error during deletion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during deletion")


# ==========================================
# ROTTE PER IL DIZIONARIO (FRONTEND)
# ==========================================

@app.get("/api/dictionary/letters")
async def get_letters_dictionary():
    # Restituisce il JSON caricato in memoria all'avvio
    return LETTERS_DICTIONARY

@app.get("/api/dictionary/words")
async def get_words_dictionary():
    # Restituisce il JSON caricato in memoria all'avvio
    return NN_DICTIONARY

@app.get("/api/user/unlocked-signs")
async def get_unlocked_signs(
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # Cerca tutte le parole sbloccate dall'utente loggato
    learned_signs = db.query(models.LearnedSign).filter(models.LearnedSign.user_id == user.id).all()
    
    # Ritorna una semplice lista di stringhe (es: ["pizza", "hello", "sun"])
    return [sign.word for sign in learned_signs]

# ==========================================
# ROTTA PER IL QUIZ
# ==========================================

# Modello Pydantic per ricevere il punteggio del quiz terminato
class QuizResultSubmit(BaseModel):
    score: int

@app.get("/api/quiz/start")
async def start_quiz(
    categories: str = "",
    difficulty: str = "mixed",  # fallback per vecchie chiamate
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    selected_categories = categories or difficulty
    quiz_data = quiz.generate_user_quiz(db, user.id, selected_categories, NN_DICTIONARY, LETTERS_DICTIONARY)
    
    # Se il controllo dei < 3 segni fallisce, restituiamo i dettagli dell'errore anziché un generico 400
    if quiz_data.get("status") == "error":
        return quiz_data
        
    return quiz_data

@app.post("/api/quiz/submit")
async def submit_quiz(data: QuizResultSubmit, db: Session = Depends(get_db), authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # Aggiorna il punteggio totale dell'utente su Postgres
    user.score += data.score
    db.commit()
    db.refresh(user)
    
    return {
        "message": "Quiz score saved!",
        "added_score": data.score,
        "new_total_score": user.score
    }


# ==========================================
# ROTTA PER I SETTINGS
# ==========================================


# --- NUOVI SCHEMI PYDANTIC ---
class ProfileUpdate(BaseModel):
    nome: str
    email: str

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

# --- ROTTA PROFILO (Con controllo Email) ---
@app.put("/update-profile")
async def update_profile(
    request: ProfileUpdate, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    
    # 1. Controllo di sicurezza lato server: la mail contiene la @?
    if "@" not in request.email:
        raise HTTPException(status_code=400, detail="Invalid email format. Missing '@'.")
        
    # 2. Controllo che la nuova email non sia già usata da qualcun altro
    if request.email != user.email:
        existing_user = db.query(models.User).filter(models.User.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already in use")

    user.nome = request.nome
    user.email = request.email
    db.commit()
    
    return {"message": "Profile updated successfully!"}

# --- ROTTA PASSWORD (Con controllo Vecchia Password) ---
@app.put("/update-password")
async def update_password(
    request: PasswordUpdate, 
    db: Session = Depends(get_db), 
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")
        
    # 1. CONTROLLO FONDAMENTALE: Verifichiamo che la vecchia password sia corretta
    # Usa la funzione verify_password per confrontare quella inserita con l'hash nel DB
    if not verify_password(request.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Error: The old password is incorrect.")
        
    # 2. Se è corretta, aggiorniamo con il nuovo hash
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    
    return {"message": "Password updated successfully!"}


@app.delete("/delete-account")
async def delete_account(db: Session = Depends(get_db), authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else ""
    user = await get_current_user(token, db)
    
    if not user:
        raise HTTPException(status_code=401, detail="Not authorized")

    try:
        # 1. Recuperiamo tutti gli ID delle chat dell'utente
        chat_ids = [
            chat.id for chat in 
            db.query(models.ChatSession.id).filter(models.ChatSession.user_id == user.id).all()
        ]
        
        # 2. Se l'utente ha delle chat, eliminiamo tutti i MESSAGGI al loro interno
        if chat_ids:
            db.query(models.ChatMessage).filter(
                models.ChatMessage.session_id.in_(chat_ids)
            ).delete(synchronize_session=False)
        
        # 3. Ora possiamo eliminare le SESSIONI CHAT (i contenitori dei messaggi)
        db.query(models.ChatSession).filter(
            models.ChatSession.user_id == user.id
        ).delete(synchronize_session=False)
        
        # 4. Eliminiamo il DIZIONARIO PERSONALE (i segni sbloccati)
        db.query(models.LearnedSign).filter(
            models.LearnedSign.user_id == user.id
        ).delete(synchronize_session=False)
        
        # 5. Infine, eliminiamo l'UTENTE in totale sicurezza
        db.delete(user)
        db.commit()
        
        return {"message": "Account and all associated data deleted successfully"}
        
    except Exception as e:
        db.rollback()
        print(f"Error during account deletion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during account deletion")
