from fastapi import HTTPException, Response, Request
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt, JWTError
from pymongo.collection import Collection
from bson import ObjectId
from utils.images import save_image_bytes
from database import db
from config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_MINUTES

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

users_collection: Collection = db["utenti"]
refresh_tokens_collection: Collection = db["refresh_tokens"]
interventions_collection = db["interventi"]
plants_collection = db["piante"]


# Serializer pubblico utente
def serialize_user_public(doc: dict) -> dict:
    if not doc:
        return None
    return {
        "id": str(doc.get("_id")),
        "username": doc.get("username"),
        "email": doc.get("email"),
        "ruolo": doc.get("ruolo", "cliente"),
        "nome": doc.get("nome"),
        "cognome": doc.get("cognome"),
        "location": doc.get("location"),
        "plantCount": doc.get("plantCount", 0),
        "interventionsToday": doc.get("interventionsToday", 0),
        "avatarUrl": doc.get("avatarUrl"),
        "avatarThumbUrl": doc.get("avatarThumbUrl"),
        # altri campi se vuoi:
        # "sesso": doc.get("sesso"),
        # "dataNascita": doc.get("dataNascita"),
        # "attivo": doc.get("attivo"),
        # "dataRegistrazione": doc.get("dataRegistrazione"),
    }


# UTILS PASSWORD

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# UTILS JWT
def create_access_token(data: dict, expires_delta: int = JWT_EXPIRATION_MINUTES):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(data: dict, days: int = 7):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


# REGISTER

def register_user(user: dict):
    if users_collection.find_one({"email": user["email"]}):
        raise HTTPException(status_code=403, detail="Email già in uso.")
    if users_collection.find_one({"username": user["username"]}):
        raise HTTPException(status_code=403, detail="Username già in uso.")

    hashed_pw = hash_password(user["password"])

    new_user = {
        "nome": user["nome"],
        "cognome": user["cognome"],
        "email": user["email"],
        "username": user["username"],
        "password": hashed_pw,
        "dataNascita": user["dataNascita"],
        "sesso": user.get("sesso"),
        "location": user.get("location"),
        "ruolo": "cliente",
        "attivo": True,
        "dataRegistrazione": datetime.utcnow(),
        # inizializza avatar a None
        "avatarUrl": None,
        "avatarThumbUrl": None,
        "avatarRelPath": None,
        "avatarRelThumbPath": None,
    }

    res = users_collection.insert_one(new_user)
    new_user["_id"] = res.inserted_id

    # ritorna anche l'utente pubblico
    return {
        "message": "Utente registrato con successo!",
        "utente": serialize_user_public(new_user)
    }

# LOGIN
def login_user(response: Response, credentials: dict):
    # accetta sia email che username
    identifier = credentials.get("email") or credentials.get("username")
    if not identifier:
        raise HTTPException(status_code=400, detail="Email o username mancante")

    user = users_collection.find_one({
        "$or": [
            {"email": identifier},
            {"username": identifier}
        ]
    })
    if not user:
        raise HTTPException(status_code=401, detail="Utente non trovato.")

    if not verify_password(credentials["password"], user["password"]):
        raise HTTPException(status_code=401, detail="Credenziali errate.")

    access_token = create_access_token({"id": str(user["_id"]), "ruolo": user["ruolo"]})
    refresh_token = create_refresh_token({"id": str(user["_id"]), "ruolo": user["ruolo"]})

    refresh_tokens_collection.insert_one({
        "token": refresh_token,
        "userId": str(user["_id"]),
        "createdAt": datetime.utcnow()
    })

    response.set_cookie(
        key="jwt",
        value=refresh_token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=7 * 24 * 60 * 60
    )

    # includi avatar nella risposta
    return {
        "message": "Login effettuato con successo!",
        "accessToken": access_token,
        "utente": serialize_user_public(user)

    }

# REFRESH TOKEN
def refresh_access_token(request: Request):
    refresh_token = request.cookies.get("jwt")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token mancante.")

    token_in_db = refresh_tokens_collection.find_one({"token": refresh_token})
    if not token_in_db:
        raise HTTPException(status_code=403, detail="Refresh token non valido.")

    try:
        payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        new_access_token = create_access_token({
            "id": payload["id"],
            "ruolo": payload["ruolo"]
        })
        return {"accessToken": new_access_token}
    except JWTError:
        raise HTTPException(status_code=403, detail="Refresh token scaduto o non valido.")


# LOGOUT
def logout_user(response: Response, request: Request):
    refresh_token = request.cookies.get("jwt")
    if refresh_token:
        refresh_tokens_collection.delete_one({"token": refresh_token})
        response.delete_cookie("jwt")
    return {"message": "Logout effettuato con successo!"}


# ME (dati utente corrente)
def get_me(user_id: str) -> dict:
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")

    # Conta piante registrate
    plant_count = plants_collection.count_documents({"userId": ObjectId(user_id)})

    # Conta irrigazioni fatte oggi
    today = datetime.utcnow().date()
    start = datetime.combine(today, datetime.min.time())
    end = datetime.combine(today, datetime.max.time())

    irrigations_today = interventions_collection.count_documents({
        "userId": ObjectId(user_id),
        "type": "irrigazione",
        "status": "done",
        "executedAt": {"$gte": start, "$lte": end}
    })

    # Aggiungi questi dati al documento utente
    user["plantCount"] = plant_count
    user["interventionsToday"] = irrigations_today

    return {"utente": serialize_user_public(user)}

def set_user_avatar(user_id: str, data: bytes) -> dict:
    """
    Salva l'immagine profilo dell'utente e aggiorna il documento utente con gli URL.
    """
    saved = save_image_bytes(
        data=data,
        subdir=f"avatars/{user_id}"
    )
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {
            "avatarUrl": saved["url"],
            "avatarThumbUrl": saved["thumbUrl"],
            "updatedAt": datetime.utcnow()
        }}
    )
    return saved