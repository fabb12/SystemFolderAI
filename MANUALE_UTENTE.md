# FileAI — Manuale d'uso

**FileAI** è un'applicazione che usa un agente AI (Ollama locale, LM Studio o
Claude API) per organizzare, cercare, analizzare e gestire file e cartelle
tramite linguaggio naturale.

Questo manuale accompagna la versione **eseguibile** (generata con PyInstaller):
non serve installare Python né alcuna libreria. Basta avviare il programma.

---

## 1. Avvio

### Windows
Fai doppio clic su **`FileAI.exe`** (dentro la cartella del programma).

### Linux / macOS
Da terminale, dentro la cartella del programma:

```bash
./FileAI
```

Al primo avvio si apre la GUI (tema scuro). Le preferenze vengono salvate in
`~/.fileai_gui.json` (cartella utente).

---

## 2. Scegliere il "cervello" (modello AI)

FileAI non ragiona da solo: si appoggia a un modello AI. Puoi usare:

| Backend | Cosa serve | Quando usarlo |
|---|---|---|
| **Ollama** (locale) | [Ollama](https://ollama.com) installato e in esecuzione (`ollama serve`) e almeno un modello scaricato (`ollama pull llama3.1`) | Gratis, privato, gira sul tuo PC |
| **LM Studio** (locale) | LM Studio con un modello caricato e server API attivo | Alternativa locale con interfaccia grafica |
| **Claude** (cloud) | Una API key Anthropic (`ANTHROPIC_API_KEY`) | Massima qualità, richiede connessione e credito |

La scelta del modello si fa dalla **barra modello** in alto nella GUI oppure
dal dialog **Impostazioni**.

### Sintassi del modello

| Spec | Cosa usa |
|---|---|
| `ollama` | Ollama, llama3.1 (default) |
| `ollama:qwen2.5` | Ollama, modello specifico |
| `lmstudio` | LM Studio (primo modello caricato) |
| `lmstudio:<id>` | LM Studio, modello specifico |
| `claude` | Claude API, Sonnet |
| `claude:opus` | Claude Opus (più potente) |
| `claude:haiku` | Claude Haiku (leggero e veloce) |

---

## 3. La GUI in breve

- **Sidebar** con azioni rapide: Chat, Organizza, Cerca, Analizza, Contenuti, Backup.
- **Drag & drop**: trascina una cartella o un file dentro la finestra per
  impostarla come destinazione/target dell'operazione.
- **Barra modello**: cambia modello al volo.
- **Conferma interattiva**: prima di ogni azione distruttiva (sposta, elimina,
  rinomina…) l'agente mostra un piano e attende il tuo OK.
- **Impostazioni** (multi-tab): modello, host Ollama/LM Studio, API key Claude,
  cartella di default, numero massimo di passi, limiti di token, conferma
  automatica, dimensione del font.

### Esempi di richieste in linguaggio naturale

```
Organizza la cartella Download per tipo di file
Trova tutti i PDF che parlano della relazione 2024
Sposta le foto del 2023 in una cartella Foto/2023
Trova i file duplicati nella cartella Documenti
Crea un backup zip della cartella Progetti
```

---

## 4. Le funzioni (tool) disponibili

| Categoria | Cosa fa |
|---|---|
| **Navigazione** | elenca cartelle, cerca file, legge file, info di sistema |
| **Analisi** | analizza una cartella, scansione intelligente, identifica i file (magic bytes) |
| **Semantica** | analizza il *contenuto* dei file con l'AI (anche PDF) |
| **Salute** | trova duplicati, controlla la salute di una cartella |
| **Azioni** | crea cartella, sposta, sposta per estensione, copia, rinomina, elimina |
| **Archivi** | comprimi in zip, estrai archivi, crea backup |
| **Visione** | analisi di immagini (con modelli che supportano la visione) |

---

## 5. Impostazioni avanzate (limiti)

Per gestire operazioni lunghe (centinaia di file) senza che l'agente si fermi a
metà, puoi regolare questi limiti dal dialog **Impostazioni → Avanzate**:

| Parametro | Default | Cosa controlla |
|---|---|---|
| Passi massimi | 60 | Iterazioni massime del loop dell'agente |
| Output massimo per tool | 24000 | Caratteri massimi per ogni risultato |
| Contesto Ollama | 32768 | Finestra di contesto del modello locale |
| Max token Claude | 8192 | Token massimi per risposta Claude |
| Max token LM Studio | 8192 | Token massimi per risposta LM Studio |

---

## 6. Risoluzione problemi

**"Impossibile contattare Ollama" / nessun modello disponibile**
→ Assicurati che Ollama sia avviato (`ollama serve`) e che tu abbia scaricato
almeno un modello (`ollama pull llama3.1`).

**Claude non risponde / errore di autenticazione**
→ Verifica la API key nelle Impostazioni o nella variabile d'ambiente
`ANTHROPIC_API_KEY`. Serve connessione a Internet e credito attivo sull'account.

**LM Studio non risponde**
→ Apri LM Studio, carica un modello e attiva il *Local Server* (API OpenAI).

**Le mie preferenze sono sparite**
→ Le preferenze sono nel file `~/.fileai_gui.json`. Se lo elimini, FileAI
riparte con le impostazioni di default.

**L'azione non viene eseguita**
→ Le azioni distruttive richiedono conferma esplicita. Controlla il piano
mostrato dall'agente e conferma, oppure attiva la conferma automatica nelle
Impostazioni (con cautela).

---

## 7. Privacy

- Con **Ollama** o **LM Studio** tutto resta sul tuo computer: nessun file
  lascia il PC.
- Con **Claude** i contenuti analizzati vengono inviati ai server Anthropic per
  l'elaborazione. Usa il backend locale se tratti dati sensibili.

---

*FileAI — gestore intelligente di file con AI.*
