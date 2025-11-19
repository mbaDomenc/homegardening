import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path
class Settings(BaseSettings):
    SERVER_BASE_URL: str = "http://localhost:8000"  # URL pubblico del backend
    UPLOAD_DIR: str = "uploads"                      # cartella dove salvare i file

settings = Settings()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", 5))
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}

# Carica variabili dal file .env (solo una volta in tutto il progetto)
load_dotenv()

# CONFIGURAZIONE GENERALE
PORT = int(os.getenv("PORT", 8000))  # Porta di default 8000 se non impostata

# DATABASE
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB", "homegardening")

# AUTENTICAZIONE
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", 60))