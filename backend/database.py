import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Creiamo il motore di connessione
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  
    pool_recycle=3600    # <-- (Opzionale ma consigliato) Ricicla le connessioni ogni ora
)

# Creiamo una fabbrica di sessioni
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Classe base per i nostri modelli (tabelle)
Base = declarative_base()

# Funzione per ottenere il DB ad ogni chiamata API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()