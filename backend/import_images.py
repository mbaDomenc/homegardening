import os
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image
from io import BytesIO


# Aggiungi la root del progetto al path per importare i moduli
sys.path.append(str(Path(__file__).parent.parent))


from config import settings
from database import db
from utils.images import save_image_bytes


# Collection MongoDB 
images_collection = db["immagini_piante"] 


def extract_metadata_from_path(filepath: Path) -> dict:
    """
    Estrae metadati dalla struttura del path.
    Esempio: dataset/plant_type/location/filename.jpg
    """
    parts = filepath.parts
    
    metadata = {
        "plant_type": None,
        "location": None,
        "notes": None
    }
    
    
    if len(parts) >= 2:
        metadata["plant_type"] = parts[-2]  
    
    
    if len(parts) >= 3:
        metadata["location"] = parts[-2]  
        metadata["plant_type"] = parts[-3]
    
    return metadata


def import_image(image_path: Path) -> dict:
    """
    Importa una singola immagine:
    1. Legge il file
    2. Estrae metadati
    3. Salva con save_image_bytes (crea full + thumbnail)
    4. Salva documento su MongoDB
    """
    print(f"Processando: {image_path.name}")
    
    # STEP 1: Leggi file
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
        print(f"   ✓ File letto: {len(image_data)} bytes")
    except Exception as e:
        print(f"Errore lettura file {image_path}: {e}")
        return None
    
    # STEP 2: Estrai metadati dal path/nome
    path_metadata = extract_metadata_from_path(image_path)
    print(f"   ✓ Path metadata: plant_type={path_metadata['plant_type']}, location={path_metadata['location']}")
    
    # STEP 3: Estrai metadati immagine
    try:
        img = Image.open(BytesIO(image_data))
        image_metadata = {
            "filesizebytes": len(image_data),  
            "filesizemb": round(len(image_data) / (1024 * 1024), 2),  
            "imagewidth": img.width,  
            "imageheight": img.height,  
            "format": img.format or "UNKNOWN",
            "mode": img.mode,
            "originalfilename": image_path.name  
        }
        img.close()
        print(f"   ✓ Immagine: {img.width}x{img.height}, formato: {image_metadata['format']}")
    except Exception as e:
        print(f"Impossibile estrarre metadati immagine: {e}")
        image_metadata = {
            "filesizebytes": len(image_data),
            "filesizemb": round(len(image_data) / (1024 * 1024), 2),
            "imagewidth": 0,
            "imageheight": 0,
            "format": "UNKNOWN",
            "mode": "UNKNOWN",
            "originalfilename": image_path.name,
            "error": str(e)
        }
    
    # STEP 4: Salva immagine (full + thumbnail)
    date_subdir = datetime.utcnow().strftime("%Y%m%d")
    subdir = f"plant_images/{date_subdir}"
    
    try:
        saved_paths = save_image_bytes(
            data=image_data,
            subdir=subdir,
            base_name=None,      
            max_side=1280,       
            thumb_side=384,      
            webp_quality=82      
        )
        print(f"   ✓ Salvata: {saved_paths['url']}")
    except Exception as e:
        print(f"Errore salvataggio: {e}")
        import traceback
        traceback.print_exc() 
        return None
    
    # STEP 5: Crea documento MongoDB 
    image_doc = {
        "filename": os.path.basename(saved_paths["abs"]),
        "originalfilename": image_path.name,  
        "filepathfull": saved_paths["abs"],  
        "filepaththumb": saved_paths["absThumb"],  
        "urlfull": saved_paths["url"],  
        "urlthumb": saved_paths["thumbUrl"],  
        "relpathfull": saved_paths["rel"],  
        "relpaththumb": saved_paths["relThumb"],  
        "planttype": path_metadata["plant_type"],  
        "location": path_metadata["location"],
        "sensorid": None,  
        "uploadtimestamp": datetime.utcnow(),  
        "processed": False,
        "cnnresults": None,  
        "notes": path_metadata["notes"],
        "tags": [],
        "metadata": image_metadata,
        "importsource": str(image_path)  
    }
    
    # STEP 6: Salva su MongoDB
    try:
        result = images_collection.insert_one(image_doc)
        image_id = str(result.inserted_id)
        print(f"   ✓ MongoDB ID: {image_id}")
        return image_doc
    except Exception as e:
        print(f" Errore MongoDB: {e}")
        import traceback
        traceback.print_exc()
        # Rollback: elimina file fisici
        try:
            os.remove(saved_paths["abs"])
            os.remove(saved_paths["absThumb"])
            print(f"   ✓ Rollback: file eliminati")
        except:
            pass
        return None


def import_images_from_directory(source_dir: str, extensions: list = None):
    """
    Importa tutte le immagini da una directory (ricorsivamente)
    
    Args:
        source_dir: Percorso della cartella con le immagini
        extensions: Lista estensioni (default: jpg, jpeg, png, webp)
    """
    if extensions is None:
        extensions = ['.jpg', '.jpeg', '.png', '.webp', '.JPG', '.JPEG', '.PNG', '.WEBP']
    
    source_path = Path(source_dir)
    
    # Verifica esistenza cartella
    if not source_path.exists():
        print(f"\n ERRORE: Cartella non trovata!")
        print(f"   Path: {source_dir}")
        print(f"\n Verifica che il percorso sia corretto")
        return
    
    if not source_path.is_dir():
        print(f"\n ERRORE: Il path non è una directory!")
        print(f"   Path: {source_dir}")
        return
    
    # Trova tutte le immagini
    print(f"\n Ricerca immagini in corso...")
    image_files = []
    for ext in extensions:
        found = list(source_path.rglob(f"*{ext}"))
        if found:
            print(f"   ✓ Trovate {len(found)} immagini {ext}")
        image_files.extend(found)
    
    print(f"\n{'='*60}")
    print(f" Cartella sorgente: {source_dir}")
    print(f"  Immagini trovate: {len(image_files)}")
    print(f"{'='*60}\n")
    
    if len(image_files) == 0:
        print(" Nessuna immagine trovata!")
        print("\n Verifica che:")
        print("   1. Il percorso contenga immagini")
        print("   2. Le immagini abbiano estensioni: .jpg, .jpeg, .png, .webp")
        return
    
    # Chiedi conferma per grandi importazioni
    if len(image_files) > 100:
        print(f"  Stai per importare {len(image_files)} immagini!")
        confirm = input("Vuoi procedere? (s/n): ").strip().lower()
        if confirm not in ['s', 'si', 'y', 'yes']:
            print(" Importazione annullata")
            return
    
    # Importa ogni immagine
    success_count = 0
    error_count = 0
    
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n{'─'*60}")
        print(f"[{idx}/{len(image_files)}]")
        result = import_image(image_path)
        
        if result:
            success_count += 1
        else:
            error_count += 1
    
    # Riepilogo finale
    print(f"\n{'='*60}")
    print(f"{'IMPORTAZIONE COMPLETATA' if error_count == 0 else 'IMPORTAZIONE COMPLETATA CON ERRORI'}")
    print(f"{'='*60}")
    print(f"   ✓ Successi: {success_count}")
    print(f"   ✗ Errori: {error_count}")
    print(f"Totale: {len(image_files)}")
    if len(image_files) > 0:
        print(f"Success rate: {round(success_count/len(image_files)*100, 1)}%")
    print(f"{'='*60}\n")


def clear_database():
    """
    ATTENZIONE: Elimina tutti i record di immagini da MongoDB
    Usare solo per test!
    """
    print("\n ATTENZIONE: Stai per eliminare TUTTE le immagini dal database!")
    print(f"   Collection: {images_collection.name}")
    confirm = input("\nDigita 'CONFIRM' per procedere: ")
    
    if confirm == "CONFIRM":
        result = images_collection.delete_many({})
        print(f"Eliminati {result.deleted_count} documenti")
    else:
        print("Operazione annullata")


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════╗
║          IMPORT IMMAGINI - DATABASE LOADER                ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    #DEFAULT PATH
    DEFAULT_PATH = "/Users/maure/Desktop/PROGETTO MONGIELLO /PlantVillage"
    
    print("Opzioni:")
    print(f"1. Importa immagini da:{DEFAULT_PATH}")
    print("2. Importa da percorso personalizzato")
    print("3. Pulisci database (ELIMINA TUTTO)")
    print("4. Esci")
    
    choice = input("\n👉 Scegli opzione (1-4): ").strip()
    
    if choice == "1":
        # Verifica che il path esista
        if not Path(DEFAULT_PATH).exists():
            print(f"\n ERRORE: Il path non esiste!")
            print(f"   Path: {DEFAULT_PATH}")
            print(f"\n Suggerimento: Usa l'opzione 2 per inserire il path corretto")
        else:
            import_images_from_directory(DEFAULT_PATH)
    
    elif choice == "2":
        source_dir = input("\n Inserisci il percorso della cartella: ").strip()
        
        if not source_dir:
            print("Percorso non valido!")
        else:
            import_images_from_directory(source_dir)
    
    elif choice == "3":
        clear_database()
    
    elif choice == "4":
        print("Uscita...")
    
    else:
        print("Opzione non valida!")
