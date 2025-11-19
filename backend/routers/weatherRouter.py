# backend/routes/weather_router.py
from fastapi import APIRouter, Query
from controllers.weather_controller import get_weather_by_city

router = APIRouter(prefix="/api", tags=["weather"])

@router.get("/weather")
async def weather(city: str = Query(..., description="Es: Bari, IT")):
    return await get_weather_by_city(city)