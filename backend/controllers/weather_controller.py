from fastapi import HTTPException
from utils.geocoding import get_coordinates_from_city
from utils.weather_service import get_weather

async def get_weather_by_city(city: str):
    coords = await get_coordinates_from_city(city)
    if not coords:
        raise HTTPException(status_code=404, detail="Località non trovata")

    meteo = get_weather(coords["lat"], coords["lng"])
    if not meteo:
        raise HTTPException(status_code=404, detail="Dati meteo non disponibili")

    return meteo