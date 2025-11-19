import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId

from config import settings
from controllers.interventionsController import interventions_collection
from database import db
from models.plantModel import PlantCreate, PlantUpdate, serialize_plant
from utils.images import save_image_bytes

try:
    from utils.trefle_service import fetch_plant_by_id, derive_defaults_from_trefle_data
    TREFLE_AVAILABLE = True
except Exception:
    # Se il modulo non esiste o manca il token, continuiamo senza rompere nulla.
    TREFLE_AVAILABLE = False

plants_collection = db["piante"]



# Helper interni
def _oid(val: str) -> ObjectId:
    return ObjectId(val)

def _parse_iso(dt):
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt
    try:
        return datetime.fromisoformat(str(dt).replace("Z", "+00:00"))
    except Exception:
        return None

def _safe_int(v, default=None):
    try:
        return int(v)
    except Exception:
        return default

def _apply_trefle_enrichment(base_doc: Dict[str, Any], trefle_id: Optional[int]) -> Dict[str, Any]:
    """
    Integra i campi dal plant Trefle (se disponibile) dentro `base_doc`.
    Precedenza: i valori esplicitamente presenti in base_doc NON vengono sovrascritti
    (approccio "client override first"). I valori mancanti vengono completati da Trefle.
    """
    if not TREFLE_AVAILABLE or not trefle_id:
        return base_doc

    snapshot = None
    try:
        snapshot = fetch_plant_by_id(int(trefle_id))
    except Exception:
        snapshot = None

    if not snapshot:
        return base_doc  # non posso arricchire, continuo come prima

    # Estrai info primarie dall'API
    trefle_scientific = None
    trefle_common = None
    trefle_slug = None

    try:
        trefle_scientific = snapshot.get("scientific_name") or snapshot.get("scientificName")
        trefle_common = snapshot.get("common_name") or snapshot.get("commonName")
        trefle_slug = snapshot.get("slug")
    except Exception:
        pass

    # Deriviamo i defaults da snapshot (es water/sunlight/soil)
    derived = {}
    try:
        derived = derive_defaults_from_trefle_data(snapshot) or {}
    except Exception:
        derived = {}

    # Applica i campi Trefle solo se non già settati nel base_doc
    if base_doc.get("species") is None and trefle_scientific:
        base_doc["species"] = trefle_scientific

    if base_doc.get("wateringIntervalDays") is None and derived.get("wateringIntervalDays") is not None:
        base_doc["wateringIntervalDays"] = derived.get("wateringIntervalDays")

    if base_doc.get("sunlight") is None and derived.get("sunlight") is not None:
        base_doc["sunlight"] = derived.get("sunlight")

    if base_doc.get("soil") is None and derived.get("soil") is not None:
        base_doc["soil"] = derived.get("soil")
    # Salviamo nel doc anche i riferimenti Trefle (link + snapshot)
    base_doc["trefleId"] = int(trefle_id)
    if trefle_slug and base_doc.get("trefleSlug") is None:
        base_doc["trefleSlug"] = trefle_slug
    if trefle_scientific and base_doc.get("trefleScientificName") is None:
        base_doc["trefleScientificName"] = trefle_scientific
    if trefle_common and base_doc.get("trefleCommonName") is None:
        base_doc["trefleCommonName"] = trefle_common

    # Conserviamo uno snapshot, utile per debug e future elaborazioni
    if base_doc.get("trefleData") is None:
        base_doc["trefleData"] = snapshot

    return base_doc


# CRUD piante
def list_plants(user_id: str) -> List[dict]:
    cursor = plants_collection.find({"userId": _oid(user_id)}).sort("createdAt", -1)
    return [serialize_plant(doc) for doc in cursor]


def get_plant(user_id: str, plant_id: str) -> Optional[dict]:
    doc = plants_collection.find_one({"_id": _oid(plant_id), "userId": _oid(user_id)})
    return serialize_plant(doc)


def create_plant(user_id: str, data: PlantCreate) -> dict:
    """
    Crea una pianta. Comportamento:
    - Se sono presenti campi di Trefle (trefleId), arricchisce i dati mancanti con snapshot Trefle.
    - Se il client passa wateringIntervalDays/sunlight/soil espliciti, questi prevalgono.
    - lastWateredAt è gestito SOLO dagli interventi (non accettiamo dal client).
    """
    now = datetime.utcnow()

    # Costruiamo un "base_doc" con i soli campi previsti.
    base_doc = {
        "userId": _oid(user_id),
        "name": data.name,
        "species": data.species,
        "location": data.location,
        "description": data.description,

        # Questi valori possono arrivare dal client o Trefle (default None qui, poi arricchisco)
        "wateringIntervalDays": getattr(data, "wateringIntervalDays", None),
        "sunlight": getattr(data, "sunlight", None),
        "soil": getattr(data, "soil", None),

        "lastWateredAt": None,  # non accettiamo input dal client
        "stage": data.stage,
        "imageUrl": data.imageUrl,
        "imageThumbUrl": getattr(data, "imageThumbUrl", None),

        # Campi geo
        "geoLat": getattr(data, "geoLat", None),
        "geoLng": getattr(data, "geoLng", None),
        "placeId": getattr(data, "placeId", None),
        "addressLocality": getattr(data, "addressLocality", None),
        "addressAdmin2": getattr(data, "addressAdmin2", None),
        "addressAdmin1": getattr(data, "addressAdmin1", None),
        "addressCountry": getattr(data, "addressCountry", None),
        "addressCountryCode": getattr(data, "addressCountryCode", None),

        # Link Trefle opzionali
        "trefleId": getattr(data, "trefleId", None),
        "trefleSlug": getattr(data, "trefleSlug", None),
        "trefleScientificName": getattr(data, "trefleScientificName", None),
        "trefleCommonName": getattr(data, "trefleCommonName", None),
        "trefleData": getattr(data, "trefleData", None),
        "trefleImageUrl": getattr(data, "trefleImageUrl", None) ,

        "createdAt": now,
        "updatedAt": now,
    }

    # Se ho un trefleId → enrich dei campi mancanti
    trefle_id = base_doc.get("trefleId")
    base_doc = _apply_trefle_enrichment(base_doc, trefle_id)

    # Se dopo l'enrich ancora mancano defaults, assegna fallback
    if base_doc.get("wateringIntervalDays") is None:
        base_doc["wateringIntervalDays"] = 3
    if base_doc.get("sunlight") is None:
        base_doc["sunlight"] = "pieno sole"
    # soil può rimanere None

    res = plants_collection.insert_one(base_doc)
    base_doc["_id"] = res.inserted_id
    return serialize_plant(base_doc)


def update_plant(user_id: str, plant_id: str, data: PlantUpdate) -> Optional[dict]:
    """
    Aggiorna campi anagrafici della pianta.
    - Non permette di aggiornare direttamente lastWateredAt (gestito dagli interventi).
    - Se arriva un trefleId (nuovo o diverso), arricchisce i campi mancanti partendo da Trefle.
    - Se il client passa wateringIntervalDays/sunlight/soil, questi prevalgono (override).
    """
    # Recupero doc esistente: ci serve per capire differenze su trefleId e per mantenere invariati i campi non aggiornati
    existing = plants_collection.find_one({"_id": _oid(plant_id), "userId": _oid(user_id)})
    if not existing:
        return None

    update_fields = {}

    # Campi aggiornabili normalmente
    for field in [
        "name", "species", "location", "description",
        "stage", "imageUrl", "imageThumbUrl",
        # campi geografici
        "geoLat", "geoLng", "placeId",
        "addressLocality", "addressAdmin2", "addressAdmin1",
        "addressCountry", "addressCountryCode",
        # Trefle link
        "trefleId", "trefleSlug", "trefleScientificName", "trefleCommonName",
    ]:
        val = getattr(data, field, None)
        if val is not None:
            update_fields[field] = val

    # Se non vengono passati, NON li tocco (restano quelli esistenti o già arricchiti).
    if getattr(data, "wateringIntervalDays", None) is not None:
        update_fields["wateringIntervalDays"] = _safe_int(data.wateringIntervalDays, existing.get("wateringIntervalDays", 3))
    if getattr(data, "sunlight", None) is not None:
        update_fields["sunlight"] = data.sunlight
    if getattr(data, "soil", None) is not None:
        update_fields["soil"] = data.soil


    # Se è stato passato un nuovo trefleId, o se esiste nel payload ma non era in existing → re-enrich
    new_trefle_id = getattr(data, "trefleId", None)
    need_enrich = False
    if new_trefle_id is not None:
        if existing.get("trefleId") != new_trefle_id:
            need_enrich = True

    # Se serve, applica enrichment Trefle SOLO per i campi mancanti (client override first)
    if need_enrich:
        # Costruiamo un doc "provvisorio" = existing + update_fields (prima di salvare)
        provisional = {**existing, **update_fields}
        provisional = _apply_trefle_enrichment(provisional, new_trefle_id)

        # Ora prendiamo le parti "enriched" che ci interessano e le mettiamo negli update_fields
        # ma SOLO se non erano state esplicitamente passate dal client.
        if "wateringIntervalDays" not in update_fields and provisional.get("wateringIntervalDays") is not None:
            update_fields["wateringIntervalDays"] = provisional.get("wateringIntervalDays")
        if "sunlight" not in update_fields and provisional.get("sunlight") is not None:
            update_fields["sunlight"] = provisional.get("sunlight")
        if "soil" not in update_fields and provisional.get("soil") is not None:
            update_fields["soil"] = provisional.get("soil")

        # Aggiorna anche i campi trefle link e snapshot (se presenti da enrichment)
        for k in ["trefleSlug", "trefleScientificName", "trefleCommonName", "trefleData", "trefleId", "trefleImageUrl"]:
            if provisional.get(k) is not None:
                update_fields[k] = provisional.get(k)

    # Fallback finali se necessari
    if "wateringIntervalDays" not in update_fields:
        update_fields["wateringIntervalDays"] = existing.get("wateringIntervalDays", 3) or 3
    if "sunlight" not in update_fields:
        update_fields["sunlight"] = existing.get("sunlight", "pieno sole") or "pieno sole"
    # soil può restare None

    update_fields["updatedAt"] = datetime.utcnow()

    plants_collection.update_one(
        {"_id": _oid(plant_id), "userId": _oid(user_id)},
        {"$set": update_fields}
    )
    doc = plants_collection.find_one({"_id": _oid(plant_id), "userId": _oid(user_id)})
    return serialize_plant(doc)


def delete_plant(user_id: str, plant_id: str) -> bool:
    res = plants_collection.delete_one({"_id": _oid(plant_id), "userId": _oid(user_id)})
    if res.deleted_count == 1:
        #elimina tutti gli interventi di quella pianta
        interventions_collection.delete_many({"plantId": _oid(plant_id), "userId": _oid(user_id)})
        return True
    return False


# Immagini
def save_plant_image(user_id: str, plant_id: str, file_bytes: bytes) -> Optional[dict]:
    plant = plants_collection.find_one({"_id": _oid(plant_id), "userId": _oid(user_id)})
    if not plant:
        return None  # il router genererà 404

    saved = save_image_bytes(
        data=file_bytes,
        subdir=f"plants/{user_id}/{plant_id}"
    )

    # rimozione img precedenti (se ne avessi qualcuna)
    old_rel = plant.get("imageRelPath")
    old_rel_thumb = plant.get("imageRelThumbPath")

    def remove_rel(rel_path: Optional[str]):
        if not rel_path:
            return
        base = settings.UPLOAD_DIR.rstrip("/").rstrip("\\")
        rel_norm = rel_path.replace("uploads/", "")  # "uploads/plants/... -> plants/..."
        abs_path = os.path.join(base, rel_norm)
        try:
            if os.path.exists(abs_path):
                os.remove(abs_path)
        except Exception:
            pass

    remove_rel(old_rel)
    remove_rel(old_rel_thumb)

    # aggiorna DB con i nuovi path
    plants_collection.update_one(
        {"_id": _oid(plant_id)},
        {"$set": {
            "imageUrl": saved["url"],
            "imageThumbUrl": saved["thumbUrl"],
            "imageRelPath": saved["rel"],
            "imageRelThumbPath": saved["relThumb"],
            "updatedAt": datetime.utcnow()
        }}
    )

    return {"imageUrl": saved["url"], "imageThumbUrl": saved["thumbUrl"]}


def remove_plant_image(user_id: str, plant_id: str) -> Optional[dict]:
    """
    Rimuove i riferimenti all'immagine dalla pianta (non elimina i file dal disco).
    """
    res = plants_collection.update_one(
        {"_id": _oid(plant_id), "userId": _oid(user_id)},
        {"$unset": {
            "imageUrl": "",
            "imageThumbUrl": "",
            "imageRelPath": "",
            "imageRelThumbPath": ""
        },
         "$set": {"updatedAt": datetime.utcnow()}
        }
    )
    if res.matched_count == 0:
        return None
    doc = plants_collection.find_one({"_id": _oid(plant_id)})
    return serialize_plant(doc)