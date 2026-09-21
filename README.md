# Classifica JR

Un solo workflow, **Bot JR - Classifiche**, genera le immagini di Serie A,
Champions League, Europa League e Conference League.

## Come usarlo

1. Su GitHub apri **Actions → Bot JR - Classifiche → Run workflow**.
2. Su **Bot JR** arriva un messaggio con due pulsanti affiancati:
   **Classifica: da scegliere** e **Destinazione: Juventus Reborn**, e **Invia** sotto.
3. **Classifica** apre l'elenco delle quattro competizioni. Nessuna è preselezionata.
4. **Destinazione** permette di scegliere **Bot JR** o **Juventus Reborn**;
   Juventus Reborn è la scelta iniziale. Puoi cambiare entrambe le scelte o tornare indietro.
5. Premi **Invia**. Se manca la classifica, compare un avviso. Altrimenti il menu
   viene cancellato e il workflow prepara e invia l'immagine alla destinazione scelta.
6. La classifica aggiornata viene salvata nel repository, le run precedenti
   completate vengono eliminate e il workflow termina. Resta visibile la run corrente.

L'immagine richiede il tempo di scaricare i dati e preparare il browser. Se nessuno
preme **Invia** entro 10 minuti, il menu scade e la run termina senza inviare immagini.
Il bot ascolta i pulsanti solo durante la run: non serve un servizio sempre acceso.
È attivo un solo menu alla volta; GitHub può mantenere una run aggiuntiva in attesa.

## Configurazione

Il workflow riutilizza questi tre secret del repository:

| Secret | Uso |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token del bot che mostra il menu e invia le immagini |
| `TELEGRAM_CHAT_ID_BOT_JR` | Chat Bot JR in cui appare il menu |
| `TELEGRAM_CHAT_ID` | Destinazione Juventus Reborn |

Il bot deve poter inviare messaggi e foto alle due destinazioni e cancellare il
proprio menu su Bot JR. Le scelte sono accettate solo dal messaggio del menu nella
chat Bot JR; se è una chat condivisa, chi può usare quei pulsanti può scegliere e inviare.
Il token non deve avere un webhook o un altro servizio `getUpdates` attivo:
il workflow usa il long polling di Telegram e non rimuove webhook esistenti.
I dettagli sono descritti nelle [API Telegram](https://core.telegram.org/bots/api#getting-updates).

Il workflow richiede `contents: write` per salvare il JSON e `actions: write`
per la pulizia. La pulizia comprende le vecchie run dei quattro workflow sostituiti,
ma esclude la run corrente, quelle più recenti e quelle ancora in corso.
La pulizia viene tentata anche dopo errori o scadenza del menu.

## Verifica locale

```bash
pip install -r requirements.txt
python -m unittest discover -v
```

I test simulano le risposte Telegram e non inviano messaggi reali. Le pull request
eseguono solo questi test; menu, invio e pulizia partono esclusivamente con l'avvio manuale.
