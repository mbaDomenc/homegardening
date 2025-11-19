from typing import Optional, Dict, Any
from pyfao56.tools.tables import FAO56Tables

"""
Estrae parametri agronomici per una pianta in base alla specie e stadio:
- kcStage: coefficiente colturale FAO56 (tabella 12)
- zr: profondità radici (fallback statico)
- p: frazione di deplezione (fallback statico)
- soilTexture: tipo di suolo indicativo
"""

# Fallback se pyfao56 non trova la specie
DEFAULTS_BY_CATEGORY = {
    "erbacea":  {"kc": {"initial": 0.7, "mid": 1.05, "late": 0.9},  "zr": 0.25, "p": 0.45, "soilTexture": "limoso"},
    "ortivo":   {"kc": {"initial": 0.7, "mid": 1.1,  "late": 0.95}, "zr": 0.30, "p": 0.45, "soilTexture": "limoso"},
    "arbustiva":{"kc": {"initial": 0.5, "mid": 0.9,  "late": 0.8},  "zr": 0.50, "p": 0.5,  "soilTexture": "argilloso"},
}

# Carica la tabella FAO (tabella 12) e aggiungi colonna in lowercase per confronto
FAO = FAO56Tables()
TABLE_KC = FAO.table12.copy()
TABLE_KC["CropLower"] = TABLE_KC["Crop"].str.lower()

def normalize_stage(stage: Optional[str]) -> str:
    s = (stage or "").strip().lower()
    if s in ("iniziale", "initial", "semina", "trapianto"): return "initial"
    if s in ("medio", "mid", "crescita", "fioritura"): return "mid"
    if s in ("finale", "late", "maturazione", "raccolta"): return "late"
    return "mid"

def get_profile(species: Optional[str], category: Optional[str], stage: Optional[str]) -> Dict[str, Any]:
    stg = normalize_stage(stage)
    crop_name = (species or "").strip().lower()
    default_cat = (category or "erbacea").lower()
    base = DEFAULTS_BY_CATEGORY.get(default_cat, DEFAULTS_BY_CATEGORY["erbacea"])

    # Cerca nella tabella FAO56
    row = TABLE_KC[TABLE_KC["CropLower"] == crop_name]

    if not row.empty:
        try:
            kc = {
                "initial": float(row["Kcmini"].values[0]),
                "mid":     float(row["Kcmmid"].values[0]),
                "late":    float(row["Kcmend"].values[0]),
            }
            kcStage = kc.get(stg, kc["mid"])
            return {
                "kcStage": round(kcStage, 2),
                "zr": round(base["zr"], 2),
                "p": round(base["p"], 2),
                "soilTexture": base["soilTexture"],
                "stageNorm": stg,
                "categoryUsed": crop_name
            }
        except Exception:
            pass  # fallback se valori non parsabili

    # Fallback default
    kcStage = base["kc"].get(stg, base["kc"]["mid"])
    return {
        "kcStage": round(kcStage, 2),
        "zr": round(base["zr"], 2),
        "p": round(base["p"], 2),
        "soilTexture": base["soilTexture"],
        "stageNorm": stg,
        "categoryUsed": default_cat
    }