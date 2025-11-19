from typing import Optional, Dict, Any, List, Tuple
from fastapi import UploadFile, HTTPException
from pymongo.collection import Collection
from pymongo import DESCENDING
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from PIL import Image
from io import BytesIO
import os

from utils.images import save_image_bytes
from config import settings


class ImageController:
    """Controller per gestire le richieste HTTP sulle immagini"""
    
    def __init__(self, collection: Collection):
        self.collection = collection
        print(f"✅ ImageController inizializzato con collection: {collection.name}")
    
    def validate_objectid(self, imageid: str) -> ObjectId:
        """Valida e converte string a ObjectId"""
        try:
            return ObjectId(imageid)
        except InvalidId:
            raise ValueError(f"ID immagine non valido: {imageid}")
    
    def extract_image_metadata(self, imagedata: bytes, originalfilename: str) -> dict:
        """Estrae metadata dall'immagine"""
        try:
            img = Image.open(BytesIO(imagedata))
            metadata = {
                "filesizebytes": len(imagedata),
                "filesizemb": round(len(imagedata) / (1024 * 1024), 2),
                "imagewidth": img.width,
                "imageheight": img.height,
                "format": img.format or "UNKNOWN",
                "mode": img.mode,
                "originalfilename": originalfilename
            }
            img.close()
            return metadata
        except Exception as e:
            return {
                "filesizebytes": len(imagedata),
                "filesizemb": round(len(imagedata) / (1024 * 1024), 2),
                "imagewidth": 0,
                "imageheight": 0,
                "format": "UNKNOWN",
                "mode": "UNKNOWN",
                "originalfilename": originalfilename,
                "error": str(e)
            }
    
    def save_image_to_filesystem(self, imagedata: bytes) -> Dict[str, str]:
        """Salva immagine su filesystem (full + thumbnail)"""
        datesubdir = datetime.utcnow().strftime("%Y%m%d")
        subdir = f"plant_images/{datesubdir}"
        
        return save_image_bytes(
            data=imagedata,
            subdir=subdir,
            basename=None,
            maxside=1280,
            thumbside=384,
            webpquality=82
        )
    
    def delete_image_files(self, filepathfull: str, filepaththumb: str) -> Tuple[List[str], List[str]]:
        """Elimina file fisici dal filesystem"""
        deleted_files = []
        errors = []
        
        for filepath in [filepathfull, filepaththumb]:
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    deleted_files.append(filepath)
                    print(f"✅ File eliminato: {filepath}")
                except Exception as e:
                    error_msg = f"Errore nell'eliminare {filepath}: {str(e)}"
                    errors.append(error_msg)
                    print(f"❌ {error_msg}")
        
        return deleted_files, errors
    
    async def upload_image(
        self,
        file: UploadFile,
        planttype: Optional[str] = None,
        location: Optional[str] = None,
        sensorid: Optional[str] = None,
        notes: Optional[str] = None
    ) -> dict:
        """Gestisce l'upload di un'immagine"""
        
        # Validazione tipo file
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail=f"Il file deve essere un'immagine. Tipo ricevuto: {file.content_type}"
            )
        
        # Leggi contenuto file
        try:
            imagedata = await file.read()
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Errore nella lettura del file: {str(e)}"
            )
        
        # Estrai metadata
        metadata = self.extract_image_metadata(imagedata, file.filename)
        
        # Salva su filesystem
        try:
            saved_paths = self.save_image_to_filesystem(imagedata)
            print(f"✅ Immagine salvata: {saved_paths['url']}")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel salvare l'immagine: {str(e)}"
            )
        
        # Crea documento MongoDB
        image_doc = {
            "filename": os.path.basename(saved_paths["abs"]),
            "originalfilename": file.filename,
            "filepathfull": saved_paths["abs"],
            "filepaththumb": saved_paths["absThumb"],
            "urlfull": saved_paths["url"],
            "urlthumb": saved_paths["thumbUrl"],
            "relpathfull": saved_paths["rel"],
            "relpaththumb": saved_paths["relThumb"],
            "planttype": planttype,
            "location": location,
            "sensorid": sensorid,
            "uploadtimestamp": datetime.utcnow(),
            "processed": False,
            "cnnresults": None,
            "notes": notes,
            "tags": [],
            "metadata": metadata
        }
        
        # Salva su MongoDB
        try:
            result = self.collection.insert_one(image_doc)
            imageid = str(result.inserted_id)
            print(f"✅ Metadata salvato su MongoDB - ID: {imageid}")
        except Exception as e:
            # Rollback: elimina file fisici
            self.delete_image_files(saved_paths["abs"], saved_paths["absThumb"])
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel salvare i metadata su MongoDB: {str(e)}"
            )
        
        return {
            "status": "success",
            "message": "Immagine caricata con successo",
            "imageid": imageid,
            "urls": {
                "full": saved_paths["url"],
                "thumbnail": saved_paths["thumbUrl"]
            },
            "paths": saved_paths,
            "metadata": metadata
        }
    
    def list_images(
        self,
        limit: int = 100,
        processed: Optional[bool] = None,
        planttype: Optional[str] = None,
        location: Optional[str] = None
    ) -> dict:
        """Ottieni lista immagini con filtri"""
        
        # Costruisci query MongoDB con filtri
        query = {}
        if processed is not None:
            query["processed"] = processed
        if planttype:
            query["planttype"] = planttype
        if location:
            query["location"] = location
        
        try:
            images = list(
                self.collection
                .find(query)
                .limit(limit)
                .sort("uploadtimestamp", DESCENDING)
            )
            
            # Converti ObjectId in string per JSON
            for img in images:
                img["id"] = str(img["_id"])
                del img["_id"]
            
            return {
                "status": "success",
                "images": images,
                "count": len(images),
                "filtersapplied": query
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel recuperare le immagini: {str(e)}"
            )
    
    def get_image_details(self, imageid: str) -> dict:
        """Ottieni dettagli di una singola immagine"""
        
        try:
            objectid = self.validate_objectid(imageid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        image = self.collection.find_one({"_id": objectid})
        
        if not image:
            raise HTTPException(
                status_code=404,
                detail=f"Immagine non trovata: {imageid}"
            )
        
        # Converti ObjectId in string
        image["id"] = str(image["_id"])
        del image["_id"]
        
        return {
            "status": "success",
            "image": image
        }
    
    def delete_image(self, imageid: str) -> dict:
        """Elimina un'immagine (file + MongoDB)"""
        
        try:
            objectid = self.validate_objectid(imageid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Recupera documento
        image = self.collection.find_one({"_id": objectid})
        
        if not image:
            raise HTTPException(
                status_code=404,
                detail=f"Immagine non trovata: {imageid}"
            )
        
        # Elimina file fisici
        deleted_files, errors = self.delete_image_files(
            image.get("filepathfull"),
            image.get("filepaththumb")
        )
        
        # Elimina da MongoDB
        try:
            self.collection.delete_one({"_id": objectid})
            print(f"✅ Record MongoDB eliminato: {imageid}")
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore nell'eliminare da MongoDB: {str(e)}"
            )
        
        return {
            "status": "success",
            "message": "Immagine eliminata con successo",
            "imageid": imageid,
            "filename": image.get("filename"),
            "deletedfiles": deleted_files,
            "errors": errors if errors else None
        }
    
    def get_stats(self) -> dict:
        """Ottieni statistiche aggregate"""
        
        try:
            # Conta totale
            total_images = self.collection.count_documents({})
            processed_images = self.collection.count_documents({"processed": True})
            unprocessed_images = self.collection.count_documents({"processed": False})
            
            # Conta per tipo di pianta
            planttypes = self.collection.distinct("planttype")
            planttype_counts = {
                pt: self.collection.count_documents({"planttype": pt})
                for pt in planttypes if pt
            }
            
            # Conta per location
            locations = self.collection.distinct("location")
            location_counts = {
                loc: self.collection.count_documents({"location": loc})
                for loc in locations if loc
            }
            
            return {
                "status": "success",
                "stats": {
                    "totalimages": total_images,
                    "processedbycnn": processed_images,
                    "unprocessed": unprocessed_images,
                    "byplanttype": planttype_counts,
                    "bylocation": location_counts
                }
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore nel calcolare le statistiche: {str(e)}"
            )
    
    def mark_image_processed(
        self,
        imageid: str,
        cnnresults: Optional[Dict[str, Any]] = None
    ) -> dict:
        """Marca un'immagine come processata dalla CNN"""
        
        try:
            objectid = self.validate_objectid(imageid)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        
        # Prepara aggiornamento
        update_data = {
            "processed": True,
            "processedtimestamp": datetime.utcnow()
        }
        
        if cnnresults:
            update_data["cnnresults"] = cnnresults
        
        # Aggiorna documento
        try:
            result = self.collection.update_one(
                {"_id": objectid},
                {"$set": update_data}
            )
            
            if result.matched_count == 0:
                raise HTTPException(
                    status_code=404,
                    detail=f"Immagine non trovata: {imageid}"
                )
            
            # Recupera documento aggiornato
            updated_image = self.collection.find_one({"_id": objectid})
            updated_image["id"] = str(updated_image["_id"])
            del updated_image["_id"]
            
            return {
                "status": "success",
                "message": "Immagine marcata come processata",
                "image": updated_image
            }
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Errore nell'aggiornare l'immagine: {str(e)}"
            )

