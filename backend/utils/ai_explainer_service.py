import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
import httpx


HF_API_KEY = os.getenv("HF_API_KEY")
HF_MODEL = os.getenv("HF_MODEL")
HF_TIMEOUT = float(os.getenv("HF_TIMEOUT", "12.0"))
HF_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Modelli di fallback (se quello principale è in coda o temporaneamente non disponibile)
HF_FALLBACK_MODELS = [

]

# Helpers di formattazione e compattazione per prompt/output
def _fmt(v, unit: Optional[str] = None):
    if v is None:
        return "n/d"
    try:
        if isinstance(v, float):
            s = f"{v:.2f}".rstrip("0").rstrip(".")
        else:
            s = str(v)
        return f"{s}{unit}" if unit else s
    except Exception:
        return "n/d"

def _stringify_memberships(memberships: Dict[str, Any]) -> str:
    if not isinstance(memberships, dict):
        return "n/d"
    lines = []
    for group in ["soil", "rain", "ratio", "temp", "et0"]:
        g = memberships.get(group) or {}
        if not isinstance(g, dict) or not g:
            continue
        top2 = sorted(g.items(), key=lambda kv: kv[1], reverse=True)[:2]
        entries = ", ".join([f"{k}={float(v):.2f}" for k, v in top2 if isinstance(v, (int, float))])
        if entries:
            lines.append(f"{group}: {entries}")
    return "; ".join(lines) if lines else "n/d"

def _stringify_rules(rules: Any) -> str:
    if not isinstance(rules, list):
        return "n/d"
    out = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        rid = r.get("id", "?")
        act = r.get("action", "?")
        w = r.get("weight", 0.0)
        because = r.get("because", "")
        try:
            out.append(f"{rid}→{act} (w={float(w):.2f}): {because}")
        except Exception:
            out.append(f"{rid}→{act}: {because}")
    return " | ".join(out) if out else "n/d"

# Spiegazione deterministica (fallback)
def _fallback_text(*, plant: Dict[str, Any], agg: Dict[str, Any], decision: Dict[str, Any], now: datetime) -> str:
    meta_wx = agg.get("weather") or {}
    prof = agg.get("profile") or {}
    fuzzy = (decision or {}).get("tech") or {}

    action = decision.get("recommendation", "—")
    reason = decision.get("reason", "—")
    next_date = decision.get("nextDate")
    conf = decision.get("confidence")

    kc = prof.get("kcStage")
    stage = prof.get("stageNorm")
    et0 = meta_wx.get("et0")
    rain = meta_wx.get("rainNext24h") if meta_wx.get("rainNext24h") is not None else meta_wx.get("precipDaily")
    soil = meta_wx.get("soilMoisture0to7cm") if meta_wx.get("soilMoisture0to7cm") is not None else meta_wx.get("soilMoistureApprox")

    # ETc ~ ET0 * Kc
    etc = None
    if isinstance(et0, (int, float)) and isinstance(kc, (int, float)):
        etc = et0 * kc

    memberships = _stringify_memberships(fuzzy.get("memberships") or {})
    rules = _stringify_rules(fuzzy.get("rules") or {})

    # Prossimo controllo
    nd = "n/d"
    try:
        if isinstance(next_date, str):
            dt = datetime.fromisoformat(next_date.replace("Z", ""))
        elif isinstance(next_date, datetime):
            dt = next_date
        else:
            dt = None
        if dt:
            nd = dt.strftime("%d %b, %H:%M")
    except Exception:
        pass

    line_action = {
        "irrigate_today": "Irriga oggi",
        "irrigate_tomorrow": "Irriga domani",
        "skip": "Non irrigare"
    }.get(action, action or "—")

    parts = [
        f"Consiglio: {line_action}.",
        f"Motivo: {reason}.",
        f"Dati: ET0={_fmt(et0, ' mm/g')}, Kc={_fmt(kc)} (stadio={stage or 'n/d'})"
        + (f", ETc≈{_fmt(etc, ' mm/g')}" if etc is not None else "")
        + f", Pioggia 24h={_fmt(rain, ' mm')}, Suolo={_fmt(soil, '%')}.",
        f"Fuzzy: {memberships}.",
        f"Regole: {rules}.",
        f"Confidenza: {_fmt(conf)}. Prossimo controllo: {nd}."
    ]
    return "\n".join(parts)


# Prompt compatto
def _prepare_prompt(plant: Dict[str, Any], agg: Dict[str, Any], decision: Dict[str, Any]) -> str:
    meta_wx = agg.get("weather") or {}
    prof = agg.get("profile") or {}
    fuzzy = (decision or {}).get("tech") or {}

    return f"""
Sei un assistente agronomico. Spiega in modo chiaro e conciso perché è stato dato il consiglio di irrigazione,
usando i dati tecnici disponibili. Rispondi in ITALIANO, in massimo 6 righe, includendo numeri chiave.

[PIANTA]
- Nome: {plant.get('name') or 'n/d'}
- Specie: {plant.get('species') or 'n/d'}
- Stage: {prof.get('stageNorm') or 'n/d'}
- Kc(stadio): {prof.get('kcStage') if prof.get('kcStage') is not None else 'n/d'}
- Zr: {prof.get('zr') if prof.get('zr') is not None else 'n/d'}
- p (RAW quota): {prof.get('p') if prof.get('p') is not None else 'n/d'}
- Tessitura suolo: {prof.get('soilTexture') or 'n/d'}

[METEO/INPUT]
- Temp: { _fmt(meta_wx.get('temp'), '°C') }
- Umidità aria: { _fmt(meta_wx.get('humidity'), '%') }
- Vento: { _fmt(meta_wx.get('wind'), ' m/s') }
- Radiazione: { _fmt(meta_wx.get('solarRadiation'), ' MJ/m²·g') }
- Pioggia 24h: { _fmt(meta_wx.get('rainNext24h'), ' mm') } (oppure giorno: { _fmt(meta_wx.get('precipDaily'), ' mm') })
- ET0: { _fmt(meta_wx.get('et0'), ' mm/g') }

[DECISIONE]
- Azione: {decision.get('recommendation')}
- Motivo fuzzy: {decision.get('reason')}
- Confidenza: { _fmt(decision.get('confidence')) }
- Membership top: { _stringify_memberships(fuzzy.get('memberships') or {}) }
- Regole attive: { _stringify_rules(fuzzy.get('rules') or {}) }

[ISTRUZIONI OUTPUT]
1) Inizia con “Consiglio: …” (Irriga oggi/domani o Non irrigare).
2) Motiva con ET0, Kc, (ETc=ET0*Kc se disponibili), pioggia, suolo/umidità, regole attive.
3) Concludi con: “Prossimo controllo: <data ora>” usando {decision.get('nextDate')}.
4) Stile tecnico ma breve, adatto a una tesi triennale (spiegabile e con numeri).
""".strip()


# Chiamata OpenRouter Inference (text-gen)

def _call_hf_text_generation(model: str, prompt: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Sei un esperto agronomico e ricevi in input l’output di un sistema fuzzy che ha analizzato dati meteo, colturali e condizioni del suolo. Il tuo compito è spiegare brevemente all'utente finale il consiglio di irrigazione, evidenziando i dati principali e le regole attivate. Rispondi in ITALIANO, in stile tecnico ma comprensibile, in massimo 6 righe "},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 220
    }

    try:
        with httpx.Client(timeout=HF_TIMEOUT) as cli:
            r = cli.post(HF_API_URL, headers=headers, json=payload)
            r.raise_for_status()
            j = r.json()

        # Estrai contenuto direttamente da OpenRouter
        if isinstance(j, dict):
            content = j.get("choices", [{}])[0].get("message", {}).get("content")
            return content.strip() if content else None, j.get("usage", {}).get("total_tokens"), None

        return None, None, "Unexpected format from OpenRouter"

    except httpx.HTTPStatusError as e:
        try:
            err_body = e.response.text
        except Exception:
            err_body = str(e)
        return None, None, f"HTTP {e.response.status_code}: {err_body}"

    except Exception as e:
        return None, None, f"Exception: {repr(e)}"

# Funzione principale chiamata dal controller irrigazione AI
def explain_irrigation(*, plant: Dict[str, Any], agg: Dict[str, Any], decision: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    """
    Produce un testo esplicativo in italiano usando (se disponibile) un modello LLM su OPENROUTER.
    Se non disponibile o in errore → fallback deterministico.
    Ritorna: {text, usedLLM, model, tokens, error?}
    """
    # Nessuna chiave → fallback deterministico
    if not HF_API_KEY:
        return {
            "text": _fallback_text(plant=plant, agg=agg, decision=decision, now=now),
            "usedLLM": False,
            "model": None,
            "tokens": None,
            "error": "HF_API_KEY not set"
        }

    prompt = _prepare_prompt(plant, agg, decision)

    # 1) Prova con il modello impostato
    text, tokens, err = _call_hf_text_generation(HF_MODEL, prompt)
    if text:
        return {
            "text": text,
            "usedLLM": True,
            "model": HF_MODEL,
            "tokens": tokens,  # None con HF free
            "error": None
        }

    # 2) Prova modelli di fallback
    last_err = err
    for fm in HF_FALLBACK_MODELS:
        if fm == HF_MODEL:
            continue
        text2, tokens2, err2 = _call_hf_text_generation(fm, prompt)
        if text2:
            return {
                "text": text2,
                "usedLLM": True,
                "model": fm,
                "tokens": tokens2,
                "error": None
            }
        last_err = err2 or last_err

    # 3) Fallback deterministico finale con annotazione error
    return {
        "text": _fallback_text(plant=plant, agg=agg, decision=decision, now=now),
        "usedLLM": False,
        "model": None,
        "tokens": None,
        "error": last_err or "Unknown error"
    }