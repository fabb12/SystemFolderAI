# FileAI — Gestore intelligente di file con AI

Applicazione **CLI + GUI** che usa un agente AI (Ollama locale, LM Studio o
Claude API) per organizzare, cercare, analizzare e gestire file e cartelle
tramite linguaggio naturale. L'agente segue un loop ReAct con conferma
interattiva delle azioni distruttive.

## Installazione

```bash
pip install -r requirements.txt    # tutte le dipendenze
ollama pull llama3.1               # o qwen2.5, mistral-nemo, ecc.
ollama serve                       # avvia il server in un terminale separato
```

## GUI (PyQt6, dark mode)

```bash
python fileai_gui.py
```

Interfaccia moderna con tema dark (Tokyo Night):

- Sidebar con azioni rapide: Chat, Organizza, Cerca, Analizza, Contenuti, **Backup**
- **Drag & drop**: trascina cartelle o file dentro la finestra per impostarli come target
- Barra modello con cambio rapido
- Conferma interattiva delle azioni distruttive
- Dialog Impostazioni multi-tab: modello, host Ollama/LM Studio, API key Claude,
  cartella default, step massimi, **limiti token** (contesto e max_tokens),
  auto-confirm, font size

Le preferenze GUI sono salvate in `~/.fileai_gui.json`.

## Tool disponibili

| Categoria | Tool |
|---|---|
| Navigazione | `lista_cartella` · `cerca_file` · `leggi_file` · `info_sistema` |
| Analisi | `analizza_cartella` · `scansione_intelligente` · `identifica_file` |
| Semantica | `analisi_semantica` · `analisi_semantica_cartella` |
| Salute | `trova_duplicati` · `controlla_salute_cartella` |
| Azioni | `crea_cartella` · `sposta_file` · `sposta_per_estensione` · `copia_file` · `rinomina_file` · `elimina_file` |
| **Archivi** | **`comprime_zip` · `estrai_archivio` · `crea_backup`** |

## Selezione del modello — sintassi `-m`

| Spec | Cosa usa |
|---|---|
| `ollama` | Ollama, llama3.1 (default) |
| `ollama:qwen2.5` | Ollama, modello specifico |
| `lmstudio` | LM Studio (primo modello caricato) |
| `lmstudio:<id>` | LM Studio, modello specifico |
| `claude` | Claude API, Sonnet |
| `claude:opus` | Claude Opus (più potente) |
| `claude:haiku` | Claude Haiku (leggero) |

## Comandi CLI

```bash
python fileai_run.py modelli                          # lista modelli disponibili
python fileai_run.py default ollama:qwen2.5           # imposta default

python fileai_run.py chat                             # chat interattiva
python fileai_run.py chat -m claude

python fileai_run.py organizza ~/Downloads
python fileai_run.py organizza ~/Downloads -m claude:opus
python fileai_run.py cerca "relazione 2024" ~/Documenti
python fileai_run.py info ~/Desktop -m ollama:llama3.1
python fileai_run.py chiedi "sposta tutti i PDF in Documenti/PDF" -m claude:sonnet
```

## Nella chat interattiva

```
Tu: modello claude:opus      → cambia modello al volo
Tu: modello attuale          → mostra il modello corrente
Tu: modelli                  → lista modelli disponibili
Tu: esci                     → esci
```

## Limiti token e contesto

Per gestire task lunghi (organizzazione di centinaia di file) senza che
l'agente si blocchi a metà, i limiti di default sono stati alzati:

| Variabile env | Default | Cosa controlla |
|---|---|---|
| `FILEAI_MAX_STEPS` | 60 | Iterazioni massime del loop ReAct |
| `FILEAI_MAX_TOOL_CHARS` | 24000 | Output massimo per chiamata tool |
| `OLLAMA_NUM_CTX` | 32768 | Finestra di contesto Ollama |
| `CLAUDE_MAX_TOKENS` | 8192 | Token massimi per risposta Claude |
| `LMSTUDIO_MAX_TOKENS` | 8192 | Token massimi per risposta LM Studio |

Tutti questi parametri sono modificabili nel dialog **Impostazioni → Avanzate**
della GUI.

## Config

- `~/.fileai.json` — modello CLI default
- `~/.fileai_gui.json` — preferenze GUI

## Build standalone (PyInstaller)

```bash
pip install pyinstaller
pyinstaller fileai.spec --noconfirm
# output: dist/FileAI/FileAI(.exe)
```

Per includere l'icona nell'eseguibile, generare `assets/icon.ico` (Windows)
o `assets/icon.icns` (macOS) a partire da `assets/icon.svg`. La GUI ha
comunque sempre la sua icona renderizzata via SVG a runtime.
