import httpx
from typing import Optional, Dict

async def get_coordinates_from_city(city: str) -> Optional[Dict[str, float]]:
    """
    Usa Nominatim (OpenStreetMap) per convertire 'Bari, IT' → lat/lng
    """
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city, "format": "json", "limit": 1}
        headers = {"User-Agent": "HomeGardeningApp"}

        async with httpx.AsyncClient(timeout=6.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            if not data:
                return None

            lat = float(data[0]["lat"])
            lng = float(data[0]["lon"])
            return {"lat": lat, "lng": lng}
    except Exception:
        return None