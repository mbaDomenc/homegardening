from pymongo import MongoClient, ASCENDING, errors
from config import MONGO_URI, MONGO_DB


client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=30000,  # 30 secondi
    connectTimeoutMS=30000,
    socketTimeoutMS=30000
)
db = client[MONGO_DB]


def ensure_indexes():
    """Crea gli indici necessari (unique, ttl, ecc.) sulle collezioni."""
    users = db["utenti"]
    refresh = db["refresh_tokens"]

    # Unicità su email e username
    try:
        users.create_index([("email", ASCENDING)], unique=True, name="uniq_email", background=True)
        users.create_index([("username", ASCENDING)], unique=True, name="uniq_username", background=True)
        print("Indici 'utenti' creati/ok: uniq_email, uniq_username")
    except errors.PyMongoError as e:
        print(f"Errore creazione indici utenti: {e}")

    # Unicità del refresh token
    try:
        refresh.create_index([("token", ASCENDING)], unique=True, name="uniq_refresh_token", background=True)
        print("Indice 'refresh_tokens' creato/ok: uniq_refresh_token")
    except errors.PyMongoError as e:
        print(f"Errore creazione indice refresh_tokens: {e}")

    
    try:
        refresh.create_index("createdAt", expireAfterSeconds=7 * 24 * 60 * 60, name="ttl_refresh_tokens", background=True)
        print("TTL su refresh_tokens creato/ok (7 giorni)")
    except errors.PyMongoError as e:
        print(f"Errore creazione TTL refresh_tokens: {e}")