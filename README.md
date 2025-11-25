# ProgettoRegione

Script CLI per raccogliere e validare i documenti di una persona (CV, documento di identità e tessera sanitaria) e salvarli in un CRM minimale per progetto.

## Requisiti

- Python 3.10+

## Utilizzo

1. Posiziona i file di testo dei documenti in locale (CV, documento di identità, tessera sanitaria).
2. Avvia lo script:

   ```bash
   python app.py
   ```

3. Esegui il login con le credenziali predefinite:

   - **Username:** `admin`
   - **Password:** `changeme`

4. Inserisci il nome del progetto e i percorsi ai tre file.

## Estrazioni e controlli

- Dal documento di identità vengono estratti: nome, cognome, numero documento, ente di rilascio, data e comune di nascita, provincia, sesso, date di rilascio/scadenza, indirizzo di residenza.
- Dalla tessera sanitaria viene estratto il codice fiscale.
- Dal CV vengono estratti: nome, cognome, domicilio, residenza, titolo e data dell'ultimo titolo di studio, situazione occupazionale. Lo script verifica inoltre la presenza di trattamento dati personali, firma e data.

Eventuali mancanze nel CV vengono mostrate come avvisi. I dati vengono salvati in `crm.json` all'interno del progetto indicato, permettendo di aggregare più persone per progetto.
