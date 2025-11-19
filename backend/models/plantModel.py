from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PlantBase(BaseModel):
    name: Optional[str] = None
    species: Optional[str] = None
    location: Optional[str] = None
    locationCountry: Optional[str] = None
    locationCountryCode: Optional[str] = None
    description: Optional[str] = None

    # derivati
    wateringIntervalDays: Optional[int] = 3
    sunlight: Optional[str] = "pieno sole"
    soil: Optional[str] = None

    lastWateredAt: Optional[datetime] = None
    stage: Optional[str] = None
    imageUrl: Optional[str] = None
    imageThumbUrl: Optional[str] = None

    # geo opzionali
    geoLat: Optional[float] = None
    geoLng: Optional[float] = None
    placeId: Optional[str] = None
    addressLocality: Optional[str] = None
    addressAdmin2: Optional[str] = None
    addressAdmin1: Optional[str] = None
    addressCountry: Optional[str] = None
    addressCountryCode: Optional[str] = None

    # Trefle link
    trefleId: Optional[int] = None
    trefleSlug: Optional[str] = None
    trefleScientificName: Optional[str] = None
    trefleCommonName: Optional[str] = None
    trefleImageUrl: Optional[str] = None  #  usato come fallback immagine

    # snapshot compatto
    trefleData: Optional[Dict[str, Any]] = None

class PlantCreate(PlantBase):
    name: str = Field(..., min_length=1)
    species: str = Field(..., min_length=1)

class PlantUpdate(PlantBase):
    # opzionale: consenti un refresh esplicito
    refreshFromTrefle: Optional[bool] = False

class PlantOut(PlantBase):
    id: str
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

def serialize_plant(doc: dict) -> dict:
    if not doc:
        return None
    return {
        "id": str(doc.get("_id")),
        "name": doc.get("name"),
        "species": doc.get("species"),
        "location": doc.get("location"),
        "locationCountry": doc.get("locationCountry"),
        "locationCountryCode": doc.get("locationCountryCode"),
        "description": doc.get("description"),
        "wateringIntervalDays": doc.get("wateringIntervalDays"),
        "sunlight": doc.get("sunlight"),
        "soil": doc.get("soil"),
        "lastWateredAt": doc.get("lastWateredAt"),
        "stage": doc.get("stage"),
        "imageUrl": doc.get("imageUrl"),
        "imageThumbUrl": doc.get("imageThumbUrl"),
        "createdAt": doc.get("createdAt"),
        "updatedAt": doc.get("updatedAt"),

        # geo
        "geoLat": doc.get("geoLat"),
        "geoLng": doc.get("geoLng"),
        "placeId": doc.get("placeId"),
        "addressLocality": doc.get("addressLocality"),
        "addressAdmin2": doc.get("addressAdmin2"),
        "addressAdmin1": doc.get("addressAdmin1"),
        "addressCountry": doc.get("addressCountry"),
        "addressCountryCode": doc.get("addressCountryCode"),

        # trefle link
        "trefleId": doc.get("trefleId"),
        "trefleSlug": doc.get("trefleSlug"),
        "trefleScientificName": doc.get("trefleScientificName"),
        "trefleCommonName": doc.get("trefleCommonName"),
        "trefleImageUrl": doc.get("trefleImageUrl"),
        "trefleData": doc.get("trefleData"),
    }