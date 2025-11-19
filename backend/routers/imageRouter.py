from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
from database import db
from controllers.imageController import ImageController
from config import settings

# Inizializza router
router = APIRouter(prefix="/api/images", tags=["images"])

# Inizializza controller con la collection MongoDB
images_collection = db["immagini_piante"]
controller = ImageController(images_collection)


@router.post("/upload", summary="Carica immagine con metadata")
async def upload_image(
    file: UploadFile = File(..., description="File immagine (JPEG, PNG, WEBP)"),
    planttype: Optional[str] = Form(None, description="Tipo di pianta (es: pomodoro, basilico)"),
    location: Optional[str] = Form(None, description="Posizione nel giardino"),
    sensorid: Optional[str] = Form(None, description="ID sensore associato"),
    notes: Optional[str] = Form(None, description="Note aggiuntive")
):
    """
    Carica un'immagine, crea thumbnail WebP e salva metadata su MongoDB.
    
    - **file**: File immagine da caricare
    - **planttype**: Tipo di pianta (opzionale)
    - **location**: Posizione nel giardino (opzionale)
    - **sensorid**: ID sensore associato (opzionale)
    - **notes**: Note aggiuntive (opzionale)
    
    Returns:
    - **imageid**: ID MongoDB del documento
    - **urls**: URL pubblici (full + thumbnail)
    - **metadata**: Informazioni sull'immagine
    """
    return await controller.upload_image(file, planttype, location, sensorid, notes)


@router.get("/list", summary="Lista immagini con filtri")
async def list_images(
    limit: int = 100,
    processed: Optional[bool] = None,
    planttype: Optional[str] = None,
    location: Optional[str] = None
):
    """
    Elenca tutte le immagini con filtri opzionali.
    
    - **limit**: Numero massimo di risultati (default: 100)
    - **processed**: Filtra per stato CNN (True/False/None)
    - **planttype**: Filtra per tipo di pianta
    - **location**: Filtra per location
    
    Returns: Lista di immagini con metadata completi da MongoDB
    """
    return controller.list_images(limit, processed, planttype, location)


@router.get("/image/{imageid}", summary="Ottieni dettagli immagine")
async def get_image_details(imageid: str):
    """
    Ottieni tutti i metadata di un'immagine specifica tramite ID MongoDB.
    
    - **imageid**: ID MongoDB dell'immagine
    
    Returns: Documento completo con tutti i metadata
    """
    return controller.get_image_details(imageid)


@router.get("/download/{date}/{filename}", summary="Scarica immagine")
async def download_image(date: str, filename: str):
    """
    Scarica il file immagine originale.
    
    - **date**: Data in formato YYYYMMDD
    - **filename**: Nome del file
    
    Returns: File immagine WebP
    """
    filepath = Path(settings.UPLOAD_DIR) / "plant_images" / date / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail=f"Immagine non trovata: {filename}")
    
    return FileResponse(
        str(filepath),
        media_type="image/webp",
        filename=filename
    )


@router.delete("/delete/{imageid}", summary="Elimina immagine")
async def delete_image(imageid: str):
    """
    Elimina un'immagine (file fisici + record MongoDB).
    
    - **imageid**: ID MongoDB dell'immagine
    
    Returns: Conferma eliminazione
    """
    return controller.delete_image(imageid)


@router.get("/stats", summary="Statistiche immagini")
async def get_image_stats():
    """
    Statistiche aggregate sulle immagini.
    
    Returns:
    - Totale immagini
    - Processate/Non processate da CNN
    - Conteggio per tipo di pianta
    - Conteggio per location
    """
    return controller.get_stats()


@router.patch("/mark-processed/{imageid}", summary="Marca immagine come processata")
async def mark_image_processed(
    imageid: str,
    cnnresults: Optional[dict] = None
):
    """
    Marca un'immagine come processata dalla CNN e salva i risultati.
    
    - **imageid**: ID MongoDB dell'immagine
    - **cnnresults**: Risultati dell'analisi CNN (JSON)
    
    Returns: Documento aggiornato
    """
    return controller.mark_image_processed(imageid, cnnresults)
