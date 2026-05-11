# FileAI — Gestore intelligente di file con AI

Applicazione CLI che usa un agente AI (Ollama locale o Claude API) per
organizzare, cercare e gestire file e cartelle tramite linguaggio naturale.

## Installazione

```bash
pip install ollama anthropic rich
pip install PyQt6          # opzionale, solo per la GUI
ollama pull llama3.1       # o qwen2.5, mistral-nemo, ecc.
ollama serve               # avvia il server (terminale separato)
```

## GUI (PyQt6, dark mode)

```bash
python fileai_gui.py
```

Interfaccia moderna con tema dark (Tokyo Night), sidebar con azioni rapide
(Chat, Organizza, Cerca, Analizza, Crea struttura, Salute), barra modello,
conferma interattiva delle azioni e dialog Impostazioni completo
(modello, host Ollama, API key Claude, cartella default, step massimi,
auto-confirm, font size).

Le preferenze GUI sono salvate in `~/.fileai_gui.json`.

## Selezione del modello — sintassi `-m`

| Spec | Cosa usa |
|---|---|
| `ollama` | Ollama, llama3.1 (default) |
| `ollama:qwen2.5` | Ollama, modello specifico |
| `claude` | Claude API, Sonnet |
| `claude:opus` | Claude Opus (più potente) |
| `claude:haiku` | Claude Haiku (leggero) |

## Comandi

```bash
python fileai.py modelli                          # lista modelli disponibili
python fileai.py default ollama:qwen2.5           # imposta default
python fileai.py default claude:sonnet

python fileai.py chat                             # chat interattiva (default)
python fileai.py chat -m claude
python fileai.py chat -m ollama:mistral-nemo

python fileai.py organizza ~/Downloads
python fileai.py organizza ~/Downloads -m claude:opus

python fileai.py cerca "relazione 2024" ~/Documenti
python fileai.py cerca "relazione 2024" ~/Documenti -m ollama:qwen2.5

python fileai.py crea "Django: app templates static docs" ~/Progetti/miosito -m claude
python fileai.py info ~/Desktop -m ollama:llama3.1
python fileai.py chiedi "sposta tutti i PDF in Documenti/PDF" -m claude:sonnet

python fileai.py --verbose organizza ~/Downloads  # mostra ogni step
```

## Nella chat interattiva

```
Tu: modello claude:opus      → cambia modello al volo
Tu: modello attuale          → mostra il modello corrente
Tu: modelli                  → lista modelli disponibili
Tu: esci                     → esci
```

## Config (~/.fileai.json)

```json
{ "default_modello": "ollama:llama3.1" }
```