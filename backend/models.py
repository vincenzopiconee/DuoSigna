from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    score = Column(Integer, default=0)
    avatar_url = Column(String, nullable=True)
    chats = relationship("ChatSession", back_populates="user")
    learned_signs = relationship("LearnedSign", back_populates="user")
    has_completed_onboarding = Column(Boolean, default=False)

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Collegato all'utente!
    title = Column(String, default="Nuova Chat")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relazioni
    user = relationship("User", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String) # 'user' o 'assistant'
    content = Column(String)

    # Campi opzionali per arricchire il messaggio con informazioni specifiche
    purpose = Column(String, nullable=True)          # 'translation' o 'general'
    target_word = Column(String, nullable=True)      
    level = Column(String, nullable=True)            # es: 'level_0', 'level_1', ecc.
    video_link_or_gif = Column(String, nullable=True)


    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")

class LearnedSign(Base):
    __tablename__ = "learned_signs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Collegato all'utente!
    word = Column(String, index=True)
    instructions = Column(String)
    learned_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="learned_signs")