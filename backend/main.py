# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from config import settings
from database import db
from controllers.interventionsController import ensure_interventions_indexes
from routers import interventionsRouter
from routers import trefleRouter
from routers import weatherRouter
from routers import pipelineRouter

#2 RICHE AGGIUNTE PER LA CREAZIONE DEL SIMULATORE DEI DATI PROVENIENTI DAI SENSORI
from routers import sensorRouter
from routers import imageRouter


uploads_dir = Path(settings.UPLOAD_DIR)
uploads_dir.mkdir(parents=True, exist_ok=True)

from routers import userRouter, plantsRouter

app = FastAPI(
    title="Home Gardening API",
    description="API backend per il progetto Home Gardening",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static: serve le immagini salvate in UPLOAD_DIR ----
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# ---- Router ----
app.include_router(userRouter.router, prefix="/api/utenti", tags=["utenti"])
app.include_router(plantsRouter.router)  # già con prefix="/api/piante" nel file
app.include_router(interventionsRouter.router)

app.include_router(trefleRouter.router)

app.include_router(weatherRouter.router)

#RIGHE AGGIUNTE PER EFFETTUARE LA CHIAMATA AL ROUTER DI IMMAGINI E SENSORI
app.include_router(sensorRouter.router)
app.include_router(imageRouter.router)
app.include_router(pipelineRouter.router)


# Health
@app.get("/health")
def health():
    return {"status": "ok"}

# ---- Startup: crea indici Mongo una sola volta ----
@app.on_event("startup")
def init_indexes():
    # === UTENTI ===
    try:
        db["utenti"].create_index("email", unique=True, name="uniq_email")
        db["utenti"].create_index("username", unique=True, name="uniq_username")
    except Exception as e:
        print("[WARN] user indexes:", e)

    #PIANTE
    try:
        # Ordinamento più usato: piante di un utente per createdAt desc
        db["piante"].create_index(
            [("userId", 1), ("createdAt", -1)],
            name="idx_user_createdAt"
        )

        # Ricerca piante per nome all'interno dello stesso utente (non unico)
        db["piante"].create_index(
            [("userId", 1), ("name", 1)],
            name="idx_user_name"
        )

        # Facoltativo: filtro per specie per utente
        db["piante"].create_index(
            [("userId", 1), ("species", 1)],
            name="idx_user_species"
        )
    except Exception as e:
        print("[WARN] plants indexes:", e)

    # INTERVENTI
    try:
        # Crea gli indici per la collezione interventi (controller dedicato)
        ensure_interventions_indexes()
    except Exception as e:
        print("[WARN] interventions indexes:", e)