from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime

# MODELLO BASE: campi comuni dell'utente
class UserBase(BaseModel):
    # Nome obbligatorio, minimo 1 carattere
    nome: str = Field(..., min_length=1)

    # Cognome obbligatorio
    cognome: str = Field(..., min_length=1)

    # Email obbligatoria, con validazione formato
    email: EmailStr

    # Username obbligatorio, minimo 6 caratteri
    username: str = Field(..., min_length=6)

    # Ruolo con valori ammessi "cliente" o "admin", default cliente
    ruolo: str = Field(default="cliente", pattern="^(cliente|admin)$")

    # Utente attivo o meno (default True)
    attivo: bool = True

    # Data di nascita obbligatoria
    dataNascita: date

    # Sesso opzionale, ma se presente deve essere M, F o Altro
    sesso: Optional[str] = Field(None, pattern="^(M|F|Altro)$")

    location: Optional[str] = None

    # Nuovi
    avatarUrl: Optional[str] = None
    avatarThumbUrl: Optional[str] = None

# MODELLO CREAZIONE UTENTE: aggiunge la password
class UserCreate(UserBase):
    # Password obbligatoria, minimo 8 caratteri
    password: str = Field(..., min_length=8)


# MODELLO UTENTE PUBBLICO: cosa restituiamo al frontend
class UserPublic(UserBase):
    id: str  # ID dell'utente (in stringa perché Mongo usa ObjectId)
    dataRegistrazione: datetime

# MODELLO LOGIN: solo email e password
class UserLogin(BaseModel):
    email: EmailStr
    password: str