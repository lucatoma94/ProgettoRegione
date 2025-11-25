import json
import re
from dataclasses import dataclass, asdict
from getpass import getpass
from pathlib import Path
from typing import Dict, List, Optional


CRM_PATH = Path("crm.json")

USERNAME = "admin"
PASSWORD = "changeme"


@dataclass
class IdentityData:
    nome: Optional[str] = None
    cognome: Optional[str] = None
    numero_documento: Optional[str] = None
    ente_rilascio: Optional[str] = None
    data_nascita: Optional[str] = None
    comune_nascita: Optional[str] = None
    provincia: Optional[str] = None
    sesso: Optional[str] = None
    data_rilascio: Optional[str] = None
    scadenza: Optional[str] = None
    indirizzo_residenza: Optional[str] = None


@dataclass
class HealthCardData:
    codice_fiscale: Optional[str] = None


@dataclass
class CVData:
    nome: Optional[str] = None
    cognome: Optional[str] = None
    indirizzo_domicilio: Optional[str] = None
    indirizzo_residenza: Optional[str] = None
    data_titolo_studio: Optional[str] = None
    titolo_studio: Optional[str] = None
    situazione_occupazionale: Optional[str] = None
    contiene_trattamento_dati: bool = False
    contiene_firma: bool = False
    contiene_data: bool = False
    alerts: List[str] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


@dataclass
class PersonRecord:
    project_name: str
    identity: IdentityData
    health_card: HealthCardData
    curriculum: CVData

    def to_dict(self):
        return {
            "project_name": self.project_name,
            "identity": asdict(self.identity),
            "health_card": asdict(self.health_card),
            "curriculum": asdict(self.curriculum),
        }


def read_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(errors="ignore")


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def extract_first(text: str, pattern: str) -> Optional[str]:
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def extract_identity(path: Path) -> IdentityData:
    raw = read_text(path)
    data = IdentityData()

    mappings = {
        "nome": r"nome\s*[:\-]\s*([A-ZÀ-Ù'`\-]+)",
        "cognome": r"cognome\s*[:\-]\s*([A-ZÀ-Ù'`\-]+)",
        "numero_documento": r"(carta d'identità|passaporto|documento)\s*n\.?\s*([A-Z0-9]+)",
        "ente_rilascio": r"ente\s+di\s+rilascio\s*[:\-]\s*([A-Z\s']+)",
        "data_nascita": r"nato\s*(?:a\s*)?.*?il\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})",
        "comune_nascita": r"nato\s*a\s*([A-Z'\s]+)",
        "provincia": r"provincia\s*[:\-]\s*([A-Z]{2})",
        "sesso": r"sesso\s*[:\-]\s*([MF])",
        "data_rilascio": r"rilasciat[oa]\s*il\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})",
        "scadenza": r"scadenza\s*[:\-]\s*([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})",
        "indirizzo_residenza": r"residenza\s*[:\-]\s*([A-Z0-9'\s,.-]+)",
    }

    for field, pattern in mappings.items():
        value = extract_first(raw, pattern)
        if field == "numero_documento" and value:
            # pattern returns entire match; prefer last group when available
            parts = re.search(pattern, raw, flags=re.IGNORECASE | re.MULTILINE)
            value = parts.group(parts.lastindex) if parts and parts.lastindex else value
        setattr(data, field, value)

    return data


def extract_health_card(path: Path) -> HealthCardData:
    raw = read_text(path)
    codice = extract_first(raw, r"codice\s+fiscale\s*[:\-]?\s*([A-Z0-9]{16})")
    if not codice:
        codice = extract_first(raw, r"([A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z])")
    return HealthCardData(codice_fiscale=codice)


def detect_date(text: str) -> Optional[str]:
    match = re.search(r"([0-9]{1,2}[\/-][0-9]{1,2}[\/-][0-9]{2,4})", text)
    if match:
        return match.group(1)
    return None


def extract_cv(path: Path) -> CVData:
    raw = read_text(path)
    normalized = normalize(raw)

    cv = CVData()
    cv.nome = extract_first(raw, r"nome\s*[:\-]\s*([A-Za-zÀ-ÿ'`\-]+)")
    cv.cognome = extract_first(raw, r"cognome\s*[:\-]\s*([A-Za-zÀ-ÿ'`\-]+)")
    cv.indirizzo_domicilio = extract_first(raw, r"domicilio\s*[:\-]\s*([^\n]+)")
    cv.indirizzo_residenza = extract_first(raw, r"residenza\s*[:\-]\s*([^\n]+)")
    cv.titolo_studio = extract_first(raw, r"titolo\s+di\s+studio\s*[:\-]\s*([^\n]+)")
    cv.data_titolo_studio = extract_first(raw, r"titolo\s+di\s+studio.*?(\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4})")
    cv.situazione_occupazionale = extract_first(raw, r"(?:occupazione|situazione\s+occupazionale)\s*[:\-]\s*([^\n]+)")

    cv.contiene_trattamento_dati = "trattamento dei dati personali" in normalized or "privacy" in normalized
    cv.contiene_firma = bool(re.search(r"firma|signed", normalized))
    cv.contiene_data = detect_date(normalized) is not None

    required_fields: Dict[str, Optional[str]] = {
        "indirizzo di domicilio": cv.indirizzo_domicilio,
        "indirizzo di residenza": cv.indirizzo_residenza,
        "titolo di studio più recente": cv.titolo_studio,
        "data del titolo di studio": cv.data_titolo_studio,
        "situazione occupazionale": cv.situazione_occupazionale,
        "nome": cv.nome,
        "cognome": cv.cognome,
    }

    for label, value in required_fields.items():
        if not value:
            cv.alerts.append(f"Campo mancante nel CV: {label}.")

    if not cv.contiene_trattamento_dati:
        cv.alerts.append("Nel CV manca il riferimento al trattamento dei dati personali.")
    if not cv.contiene_firma:
        cv.alerts.append("Il CV non risulta firmato.")
    if not cv.contiene_data:
        cv.alerts.append("Il CV non contiene una data.")

    return cv


def login() -> bool:
    print("== Login ==")
    username = input("Username: ")
    password = getpass("Password: ")
    if username == USERNAME and password == PASSWORD:
        print("Autenticazione riuscita.\n")
        return True
    print("Credenziali non valide.\n")
    return False


def save_to_crm(record: PersonRecord) -> None:
    crm_data = {"projects": []}
    if CRM_PATH.exists():
        try:
            crm_data = json.loads(CRM_PATH.read_text())
        except json.JSONDecodeError:
            pass

    project = next((p for p in crm_data["projects"] if p.get("name") == record.project_name), None)
    if not project:
        project = {"name": record.project_name, "people": []}
        crm_data["projects"].append(project)

    project["people"].append(record.to_dict())
    CRM_PATH.write_text(json.dumps(crm_data, indent=2, ensure_ascii=False))
    print(f"Dati salvati nel CRM sotto il progetto '{record.project_name}'.")


def summarize(record: PersonRecord) -> None:
    print("\n== Riepilogo dati estratti ==")
    print("Documento d'identità:")
    for field, value in asdict(record.identity).items():
        print(f"  - {field.replace('_', ' ').capitalize()}: {value or 'Non trovato'}")

    print("\nTessera sanitaria:")
    print(f"  - Codice fiscale: {record.health_card.codice_fiscale or 'Non trovato'}")

    print("\nCV:")
    for field, value in asdict(record.curriculum).items():
        if field == "alerts":
            continue
        print(f"  - {field.replace('_', ' ').capitalize()}: {value if value is not None else 'Non trovato'}")

    if record.curriculum.alerts:
        print("\n⚠️  Avvisi CV:")
        for alert in record.curriculum.alerts:
            print(f"  - {alert}")
    else:
        print("\nCV conforme ai requisiti minimi.")


def prompt_file_path(prompt: str) -> Path:
    path_str = input(prompt).strip()
    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Il file {path} non esiste.")
    return path


def main() -> None:
    if not login():
        return

    project_name = input("Nome del progetto: ").strip()
    if not project_name:
        print("È necessario indicare il nome del progetto.")
        return

    try:
        cv_path = prompt_file_path("Percorso al CV: ")
        id_path = prompt_file_path("Percorso al documento di identità: ")
        card_path = prompt_file_path("Percorso alla tessera sanitaria: ")
    except FileNotFoundError as exc:
        print(exc)
        return

    identity = extract_identity(id_path)
    health_card = extract_health_card(card_path)
    cv = extract_cv(cv_path)

    record = PersonRecord(
        project_name=project_name,
        identity=identity,
        health_card=health_card,
        curriculum=cv,
    )

    summarize(record)
    save_to_crm(record)


if __name__ == "__main__":
    main()
