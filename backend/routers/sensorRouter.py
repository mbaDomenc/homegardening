
from fastapi import APIRouter, Query
from controllers.sensor_controller import (
    save_sensor_data,
    get_sensor_history,
    get_latest_readings,
    get_sensor_stats
)
from models.sensorModel import SensorReading, SensorReadingResponse
from typing import Optional, List

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("/data", response_model=SensorReadingResponse, summary="Invia dati da sensore")
async def receive_sensor_data(reading: SensorReading):
    """
    Endpoint per ricevere e salvare dati dai sensori (reali o simulati)
    """
    return await save_sensor_data(reading)


@router.get("/history", summary="Storico letture sensori")
async def get_history(
    sensor_id: Optional[str] = Query(None, description="ID specifico del sensore"),
    sensor_type: Optional[str] = Query(None, description="Tipo di sensore"),
    location: Optional[str] = Query(None, description="Posizione"),
    hours: int = Query(24, description="Ultime N ore", ge=1, le=720),
    limit: int = Query(1000, description="Max record", ge=1, le=10000)
) -> List[dict]:
    """Recupera lo storico delle letture con filtri opzionali"""
    return await get_sensor_history(sensor_id, sensor_type, location, hours, limit)


@router.get("/latest", summary="Ultime letture per ogni tipo di sensore")
async def get_latest(
    location: Optional[str] = Query(None, description="Filtra per posizione")
) -> dict:
    """Ritorna l'ultima lettura disponibile per ogni tipo di sensore"""
    return await get_latest_readings(location)


@router.get("/stats/{sensor_id}", summary="Statistiche per un sensore")
async def get_stats(
    sensor_id: str,
    hours: int = Query(24, description="Periodo in ore", ge=1, le=720)
) -> dict:
    """Calcola statistiche aggregate (media, min, max, count)"""
    return await get_sensor_stats(sensor_id, hours)
