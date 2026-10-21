import jwt
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext

# Configurazione per criptare le password
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    # Questo parametro "forza" passlib a non usare l'algoritmo bcrypt problematico
    # per la fase di test, risolvendo l'errore dei 72 byte.
    bcrypt__ident="2b" 
)

# Chiave segreta per "firmare" i token (In un progetto reale andrebbe nel file .env!)
SECRET_KEY = "super_segreto_mita_2026"
ALGORITHM = "HS256"

# Funzione per criptare la password
def hash_password(password: str):
    return pwd_context.hash(password)

# Funzione per verificare se la password inserita corrisponde a quella criptata
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

# Funzione per creare il "biglietto d'ingresso" (Token JWT)
def create_access_token(data: dict):
    to_encode = data.copy()
    # Il token scade tra 2 ore
    expire = datetime.now(timezone.utc) + timedelta(hours=2)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt