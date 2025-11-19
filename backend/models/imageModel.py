from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom type per ObjectId MongoDB"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ImageMetadata(BaseModel):
    """Metadata tecnici dell'immagine"""
    file_size_bytes: int
    file_size_mb: float
    image_width: int
    image_height: int
    format: str
    mode: str
    original_filename: str
    error: Optional[str] = None


class CNNResults(BaseModel):
    """Risultati analisi CNN"""
    disease_detected: Optional[str] = None
    confidence: Optional[float] = None
    recommendations: Optional[List[str]] = []
    processed_at: Optional[datetime] = None
    model_version: Optional[str] = None


class ImageBase(BaseModel):
    """Schema base per creazione immagine"""
    plant_type: Optional[str] = None
    location: Optional[str] = None
    sensor_id: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = []


class ImageCreate(ImageBase):
    """Schema per creazione immagine (richiesta upload)"""
    pass


class ImageInDB(ImageBase):
    """Schema completo immagine salvata su MongoDB"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    filename: str
    original_filename: str
    filepath_full: str
    filepath_thumb: str
    url_full: str
    url_thumb: str
    rel_path_full: str
    rel_path_thumb: str
    upload_timestamp: datetime
    processed: bool = False
    processed_timestamp: Optional[datetime] = None
    cnn_results: Optional[CNNResults] = None
    metadata: ImageMetadata

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class ImageResponse(ImageBase):
    """Schema per risposta API"""
    id: str = Field(alias="_id")
    filename: str
    original_filename: str
    url_full: str
    url_thumb: str
    upload_timestamp: datetime
    processed: bool
    processed_timestamp: Optional[datetime] = None
    cnn_results: Optional[CNNResults] = None
    metadata: ImageMetadata

    class Config:
        populate_by_name = True


class ImageUpdateProcessed(BaseModel):
    """Schema per aggiornamento stato processato"""
    processed: bool = True
    cnn_results: Optional[CNNResults] = None


class ImageListResponse(BaseModel):
    """Schema per lista immagini"""
    status: str = "success"
    images: List[ImageResponse]
    count: int
    filters_applied: Dict[str, Any]


class ImageStatsResponse(BaseModel):
    """Schema per statistiche"""
    status: str = "success"
    stats: Dict[str, Any]


class ImageUploadResponse(BaseModel):
    """Schema per risposta upload"""
    status: str = "success"
    message: str
    image_id: str
    urls: Dict[str, str]
    paths: Dict[str, str]
    metadata: ImageMetadata
