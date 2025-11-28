"""
Test della pipeline via API con requests.
"""

import requests
import json
from pprint import pprint


def test_pipeline_api():
    """Test 1: Richiesta valida alla pipeline"""
    
    # URL del backend
    url = "http://localhost:8000/pipeline/process"
    
    # Payload con dati sensori
    payload = {
        "sensor_data": {
            "soil_moisture": 45.0,
            "temperature": 24.5,
            "humidity": 62.0,
            "light": 15000.0,
            "rainfall": 0.0
        },
        "plant_type": "tomato"
    }
    
    print("Inviando richiesta al backend...")
    print(f"URL: {url}")
    print(f"Payload:")
    pprint(payload)
    print("\n" + "="*60 + "\n")
    
    try:
        # Effettua la richiesta POST
        response = requests.post(url, json=payload)
        
        # Stampa status code
        print(f"Status Code: {response.status_code}")
        
        # Stampa la risposta in formato JSON leggibile
        print("\nRisposta ricevuta:\n")
        response_json = response.json()
        pprint(response_json)
        
        # Estrai informazioni principali
        print("\n" + "="*60)
        print("RIEPILOGO RISPOSTA:\n")
        
        if response.status_code == 200:
            status = response_json.get("status")
            suggestion = response_json.get("suggestion", {})
            metadata = response_json.get("metadata", {})
            
            print(f"Status: {status}")
            print(f"Decidere: {suggestion.get('should_water')}")
            print(f"Quantità acqua: {suggestion.get('water_amount_liters')} L")
            print(f"Decisione: {suggestion.get('decision')}")
            print(f"Descrizione: {suggestion.get('description')}")
            print(f"Timing: {suggestion.get('timing')}")
            print(f"Priorità: {suggestion.get('priority')}")
            print(f"\n Inizio: {metadata.get('started_at')}")
            print(f"Fine: {metadata.get('completed_at')}")
            print(f"Errori: {metadata.get('errors')}")
            print(f"Warning: {metadata.get('warnings')}")
        else:
            print(f"Errore: {response_json}")
            
    except requests.exceptions.ConnectionError:
        print("Errore: Non riesco a connettermi al backend!")
        print("   Assicurati che il backend sia in esecuzione su http://localhost:8000")
    except Exception as e:
        print(f"Errore: {str(e)}")


if __name__ == "main":
    test_pipeline_api()