# Controllo Documenti e CRM

Applicazione web FastAPI per caricare CV, documenti di identità e tessere sanitarie, eseguire OCR, estrarre dati tramite modello OpenAI e salvare i risultati in un piccolo CRM basato su SQLite.

## Requisiti
- Python 3.10+
- Tesseract OCR installato nel sistema (eseguibile `tesseract` disponibile nel PATH)
- Poppler/cairo consigliato per OCR di PDF complessi (pdfplumber/pytesseract)
- Chiave OpenAI opzionale in variabile d'ambiente `OPENAI_API_KEY`

## Installazione
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Avvio server
```bash
uvicorn main:app --reload
```
L'applicazione sarà disponibile su `http://127.0.0.1:8000`.

## Credenziali di default
- Username: `admin`
- Password: `admin123`

È possibile sovrascrivere tramite variabili d'ambiente `ADMIN_USERNAME` e `ADMIN_PASSWORD`. La chiave di sessione può essere modificata con `SESSION_SECRET`.

## Flusso utente
1. **Login** con le credenziali sopra.
2. **Selezione/creazione progetto**: inserire il nome progetto. Se non esiste viene creato.
3. **Caricamento documenti**: caricare CV, documento di identità e tessera sanitaria (PDF o immagini) e premere "Esegui controllo".
4. L'app salva i file in `./uploads`, esegue OCR, chiama `extract_fields_with_ai` per estrarre i dati richiesti, verifica la completezza del CV e mostra eventuali alert.
5. I dati vengono salvati come nuova persona collegata al progetto corrente. È possibile consultare la lista progetti, le persone del progetto e il dettaglio di ciascuna persona.

## Note su OpenAI
La funzione `extract_fields_with_ai` prepara un prompt strutturato e utilizza la API Response. Se `OPENAI_API_KEY` non è presente, restituisce un set vuoto di campi per permettere il test senza chiamate esterne.
