# CLAUDE.md — Contesto progetto FileAI

> Documento per Claude Code: leggi questo file all'inizio di ogni sessione.
> Evita di riesplorare la struttura ogni volta — è già descritta qui.

## Cos'è FileAI

Applicazione Python (CLI + GUI PyQt6) che usa un agente AI (Ollama locale,
LM Studio o Claude API) per organizzare, cercare e gestire file e cartelle
tramite linguaggio naturale. L'agente segue un loop ReAct con conferma
interattiva delle azioni distruttive.

## Struttura del repository

Tutti i file Python sono al **root** del repo, ma il codice li importa
come se fossero un package `fileai.*`. Un loader virtuale
(`gui/_bootstrap.py`) costruisce in `sys.modules` il package `fileai`
mappandoli a runtime. NON serve `pip install -e .`.

```
SystemFolderAI/
├── CLAUDE.md              ← questo file
├── README.md
├── requirements.txt       ← dipendenze pip
├── fileai.spec            ← PyInstaller spec per build standalone
├── .claude/
│   └── settings.json      ← permission allowlist Claude Code
├── assets/
│   └── icon.svg           ← logo dell'app (fonte per .ico/.icns)
├── fileai_run.py          ← entry point CLI: python fileai_run.py ...
├── fileai_gui.py          ← entry point GUI: python fileai_gui.py
│
├── config.py              → fileai.config         (parsing modello, persistenza)
├── registry.py            → fileai.registry       (Tool Registry, pattern Plugin)
├── agent.py               → fileai.agent          (loop ReAct + conferma)
├── cli.py                 → fileai.cli            (argparse + comandi)
│
├── base.py                → fileai.backends.base       (interfaccia astratta)
├── ollama.py              → fileai.backends.ollama     (Ollama locale)
├── claude.py              → fileai.backends.claude     (Claude API)
├── lmstudio.py            → fileai.backends.lmstudio   (LM Studio, API OpenAI)
│
├── filesystem.py          → fileai.tools.filesystem    (move/copy/list/search)
├── analysis.py            → fileai.tools.analysis      (magic bytes, statistiche)
├── semantic.py            → fileai.tools.semantic      (analisi LLM contenuto)
├── health.py              → fileai.tools.health        (duplicati, salute)
├── compression.py         → fileai.tools.compression   (zip/backup/estrazione)
│
└── gui/
    ├── _bootstrap.py      ← monta il package virtuale fileai
    ├── main_window.py     ← MainWindow PyQt6 (sidebar, chat, input)
    ├── worker.py          ← QThread che esegue run_agente
    ├── settings_dialog.py ← dialog impostazioni multi-tab
    ├── icons.py           ← icone SVG inline (Feather-like) + logo app
    └── styles.py          ← QSS dark mode (palette Tokyo Night)
```

## Concetti chiave

### Tool Registry (`registry.py`)
Pattern Plugin. Ogni tool è una funzione decorata con `@registry.tool(...)`.
Aggiungere un nuovo tool = creare la funzione e decorarla. Non serve
modificare nessun altro file: i tool sono registrati all'import e il loro
schema JSON viene passato al modello.

### Loop ReAct (`agent.py::run_agente`)
1. invio messaggi al backend
2. se il modello chiama tool → eseguo, mostro risultato, rimando
3. se il modello scrive un piano che chiede conferma → stop, attendo
   risposta utente, poi riprendo
4. se il modello risponde senza tool → fine
Limiti runtime: `MAX_STEPS` (env `FILEAI_MAX_STEPS`, default 60),
`MAX_TOOL_CHARS` (env `FILEAI_MAX_TOOL_CHARS`, default 24000).

### Backend astratto (`base.py`)
Ogni backend espone solo `chat(messages) → (testo, tool_calls, raw_msg)`.
I formati specifici (OpenAI, Anthropic) sono normalizzati internamente.

### Bootstrap GUI (`gui/_bootstrap.py`)
Idempotente. Costruisce `fileai`, `fileai.backends`, `fileai.tools` come
package virtuali e li popola con i moduli root. Necessario solo per il
ramo GUI; la CLI usa `fileai_run.py` che assume gli stessi import.

### Shadow di `ollama.py`
Il file `ollama.py` ha lo stesso nome del package PyPI. `_load_real_ollama()`
risolve il conflitto cercando il pacchetto reale in `sys.path` saltando la
cartella corrente.

## Configurazione

Due file persistenti:
- `~/.fileai.json` — modello CLI default (`get_default_modello`)
- `~/.fileai_gui.json` — preferenze GUI (modello, host, api key, font, ecc.)

Variabili d'ambiente:
- `OLLAMA_HOST`, `LMSTUDIO_HOST`, `ANTHROPIC_API_KEY`
- `OLLAMA_NUM_CTX` (default 32768)
- `CLAUDE_MAX_TOKENS` (default 8192)
- `LMSTUDIO_MAX_TOKENS` (default 8192)
- `FILEAI_MAX_TOOL_CHARS` (default 24000)
- `FILEAI_MAX_STEPS` (default 60)

## Convenzioni codice

- Italiano per UI, log, docstring, messaggi utente.
- Identifier in italiano dove i nomi sono "di dominio" (`sposta_file`,
  `cartella`, `domanda`) — l'agente li vede così, lascia stare.
- Tool: ogni eccezione interna deve essere catturata e ritornata come
  stringa che inizia con `ERRORE:` (l'agente legge la stringa).
- Backend: NON usare `sys.exit()` nei costruttori — solleva eccezioni
  con messaggio chiaro; la GUI le mostra in un dialog.
- Output tool grossi: tronca via `_limita_output` in `agent.py`.

## Comandi rapidi

```bash
python fileai_gui.py                      # GUI
python fileai_run.py chat                 # CLI chat
python fileai_run.py organizza ~/Downloads
python fileai_run.py modelli              # lista modelli installati
```

## Quando aggiungi un tool

1. Crea il file `<nome>.py` al root (NON dentro una sottocartella).
2. Decora la funzione con `@registry.tool(...)`.
3. Aggiungi la mappatura in `gui/_bootstrap.py` → `_TOOL_MODULES`.
4. Aggiungi un'eventuale azione rapida in `gui/main_window.py` →
   `QUICK_ACTIONS` se ha senso un bottone dedicato.

## Quando aggiungi un backend

1. Crea il file `<nome>.py` al root con una classe che eredita da
   `BaseBackend` e implementa `chat()`.
2. Aggiungi in `gui/_bootstrap.py` → `_BACKEND_MODULES`.
3. Aggiungi il branch in `crea_backend` (sempre in `_bootstrap.py`).
4. Aggiungi il parsing in `config.py::parse_modello`.

## Build standalone (PyInstaller)

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller fileai.spec --noconfirm
```

Lo `.spec` include i file root come **data files** (sono caricati via
`importlib.spec_from_file_location` da `gui/_bootstrap.py`, non come moduli
classici). `_bootstrap` deduce `repo_root` da `__file__`: nell'app frozen,
`Path(gui/_bootstrap.py).parent.parent` punta a `sys._MEIPASS` dove
PyInstaller estrae i datas — il loader funziona out-of-the-box.

Per l'icona dell'eseguibile, generare `assets/icon.ico` (Windows) o
`assets/icon.icns` (macOS) da `assets/icon.svg` con un tool a scelta
(es. `cairosvg` + `Pillow`).

## Convenzioni icone GUI

Tutte le icone in `gui/icons.py` sono **SVG inline minimali**
(stroke 1.8px, viewBox 24×24, no fill, line-cap rotondo). Renderizzate via
`QSvgRenderer` su `QPixmap` e cachate. `currentColor` viene sostituito al
render con il colore del tema. Nessun asset esterno → portabilità totale.
