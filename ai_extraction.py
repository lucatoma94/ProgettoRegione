import json
import os
from typing import Dict

from openai import OpenAI, OpenAIError


def extract_fields_with_ai(testo_cv: str, testo_doc_identita: str, testo_tessera: str) -> Dict:
    client = None
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)

    prompt = f"""
Sei un assistente che estrae dati da tre testi. Restituisci SOLO un JSON valido senza testo aggiuntivo con i seguenti campi:

Dal DOCUMENTO DI IDENTITÀ:
- nome
- cognome
- numero_documento
- ente_rilascio
- data_nascita (YYYY-MM-DD)
- comune_nascita
- provincia_nascita
- sesso
- data_rilascio (YYYY-MM-DD)
- data_scadenza (YYYY-MM-DD)
- indirizzo_residenza

Dalla TESSERA SANITARIA:
- codice_fiscale

Dal CV:
- nome
- cognome
- indirizzo_domicilio
- indirizzo_residenza
- titolo_studio_piu_recente:
    - titolo
    - data_conseguimento (YYYY-MM-DD)
- situazione_occupazionale
- privacy_clause_present (boolean)
- firma_presente (boolean)
- data_cv (YYYY-MM-DD)

Inserisci stringhe vuote o valori false se non trovi informazioni. Non inventare dati. Esempio di output:
{"nome": "Mario", "cognome": "Rossi", ...}

Testo CV:
{testo_cv}

Testo documento identità:
{testo_doc_identita}

Testo tessera sanitaria:
{testo_tessera}
"""

    default_response = {
        "nome": "",
        "cognome": "",
        "numero_documento": "",
        "ente_rilascio": "",
        "data_nascita": "",
        "comune_nascita": "",
        "provincia_nascita": "",
        "sesso": "",
        "data_rilascio": "",
        "data_scadenza": "",
        "indirizzo_residenza": "",
        "codice_fiscale": "",
        "indirizzo_domicilio": "",
        "titolo_studio_piu_recente": {"titolo": "", "data_conseguimento": ""},
        "situazione_occupazionale": "",
        "privacy_clause_present": False,
        "firma_presente": False,
        "data_cv": "",
    }

    if not client:
        return default_response

    try:
        completion = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=prompt,
            temperature=0,
            max_output_tokens=500,
            response_format={"type": "json_object"},
        )
        content = completion.output[0].content[0].text
        data = json.loads(content)
        # Ensure nested object exists
        if "titolo_studio_piu_recente" not in data:
            data["titolo_studio_piu_recente"] = {"titolo": "", "data_conseguimento": ""}
        return {**default_response, **data}
    except (OpenAIError, json.JSONDecodeError, KeyError):
        return default_response