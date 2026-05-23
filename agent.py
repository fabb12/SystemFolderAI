"""
agent.py — Loop ReAct con conferma interattiva
"""

import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

from fileai.registry import registry

console = Console()


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


# Limiti runtime — alzati per supportare operazioni lunghe (organizzazione di
# cartelle con centinaia di file) senza che l'agente si blocchi a metà task.
MAX_STEPS      = _env_int("FILEAI_MAX_STEPS", 60, minimum=5)
MAX_TOOL_CHARS = _env_int("FILEAI_MAX_TOOL_CHARS", 24000, minimum=1000)

SYSTEM_PROMPT = """Sei FileAI, un assistente specializzato nell'organizzazione intelligente di file e cartelle.

TOOL DISPONIBILI:

Analisi (usa PRIMA di agire):
  scansione_intelligente     → tipo REALE di ogni file (magic bytes), estensioni sbagliate, corrotti
  analizza_cartella          → statistiche per estensione e dimensione
  analisi_semantica          → legge il CONTENUTO di un documento e capisce di cosa tratta
  analisi_semantica_cartella → analisi semantica di tutti i documenti in una cartella
  trova_duplicati            → file duplicati per nome o contenuto (MD5)
  controlla_salute_cartella  → file temporanei, vuoti, vecchi, grandi, nascosti

Navigazione:
  lista_cartella    → elenca file
  cerca_file        → cerca per nome/estensione/contenuto
  leggi_file        → leggi contenuto testo
  identifica_file   → tipo reale di un singolo file
  info_sistema      → info OS

Azioni (richiedono conferma):
  crea_cartella         → crea cartella
  sposta_per_estensione → sposta tutti i file di un'estensione (USA QUESTO, non wildcard)
  sposta_file           → sposta UN file singolo (percorso ESATTO, NO wildcard *.ext)
  rinomina_file         → rinomina
  copia_file            → copia
  elimina_file          → elimina (richiede conferma=true)

Archivi e backup:
  comprime_zip      → comprime file o cartella in archivio .zip
  estrai_archivio   → estrae .zip / .tar / .tar.gz / .tgz
  crea_backup       → backup datato di una cartella (zip o copia)

PROCEDURA per organizzare:
1. scansione_intelligente → vedi tipo reale
2. (opzionale) analisi_semantica_cartella → capisci il contenuto
3. (opzionale) trova_duplicati → identifica sprechi
4. Proponi il piano con percorsi esatti e scrivi "Procedo con il piano?"
5. Dopo conferma → esegui con sposta_per_estensione / sposta_file

REGOLE:
- NON usare wildcard (*.pdf) nei percorsi — usa sposta_per_estensione
- sposta_file vuole percorso ESATTO di un singolo file
- Rispondi in italiano
"""

# ── Segnali di attesa conferma ────────────────────────────────────

_SEGNALI_CONFERMA = [
    "sei d'accordo", "vuoi procedere", "procedo", "posso procedere",
    "confermi", "conferma", "vuoi che", "fammi sapere", "devo procedere",
    "vuoi modificare", "prima di procedere", "aspetto conferma",
    "fase 1", "fase 2", "passo 1", "passo 2",
    "proposta di azione", "piano di", "struttura sarebbe",
    "procedo con il piano",
]

_OPS_MODIFICANTI = {
    "crea_cartella", "sposta_file", "sposta_per_estensione",
    "copia_file", "rinomina_file", "elimina_file",
    "comprime_zip", "estrai_archivio", "crea_backup",
}

_OPS_SCRITTURA = {
    "crea_cartella", "rinomina_file", "elimina_file",
    "sposta_file", "copia_file", "sposta_per_estensione",
    "comprime_zip", "estrai_archivio", "crea_backup",
}


# ── UI helpers ────────────────────────────────────────────────────

def _descrivi_tool(nome: str, argomenti: dict) -> str:
    """Frase leggibile per ogni tool call."""
    icona, verbo = registry.get_label(nome)

    if nome == "lista_cartella":
        r   = argomenti.get("ricorsivo", False)
        pat = argomenti.get("pattern", "*")
        extra = (" (ricorsivo)" if r else "") + (f" [{pat}]" if pat != "*" else "")
        return f"{icona} {verbo} {argomenti.get('percorso','?')}{extra}"

    if nome in ("analizza_cartella", "scansione_intelligente",
                "analisi_semantica_cartella", "trova_duplicati",
                "controlla_salute_cartella"):
        chiave = "cartella" if "cartella" in argomenti else "percorso"
        return f"{icona} {verbo} {argomenti.get(chiave,'?')}"

    if nome == "crea_cartella":
        return f"{icona} {verbo} {argomenti.get('percorso','?')}"

    if nome == "sposta_per_estensione":
        return (f"{icona} Sposto tutti i {argomenti.get('estensione','?')} "
                f"da {argomenti.get('cartella','?')}  →  {argomenti.get('destinazione','?')}")

    if nome in ("sposta_file", "copia_file"):
        return f"{icona} {verbo} {argomenti.get('origine','?')}  →  {argomenti.get('destinazione','?')}"

    if nome == "rinomina_file":
        return f"{icona} {verbo} {Path(argomenti.get('percorso','?')).name}  →  {argomenti.get('nuovo_nome','?')}"

    if nome == "elimina_file":
        conf   = argomenti.get("conferma", False)
        avviso = "[red](DEFINITIVO)[/red]" if conf else "[yellow](attende conferma)[/yellow]"
        return f"{icona} {verbo} {argomenti.get('percorso','?')} {avviso}"

    if nome == "cerca_file":
        filtri = [
            f"nome='{v}'" for k, v in argomenti.items()
            if k in ("nome", "estensione", "contenuto") and v
        ]
        fs = f"  [{', '.join(filtri)}]" if filtri else ""
        return f"{icona} {verbo} {argomenti.get('cartella','?')}{fs}"

    import json
    return f"{icona} {verbo} — {json.dumps(argomenti, ensure_ascii=False)[:60]}"


def _limita_output(testo: str) -> str:
    """
    Limita la dimensione del risultato di un tool prima di rimandarlo al
    modello. Output enormi (scansioni, liste, duplicati) saturano la finestra
    di contesto e causano il "reset" del modello a metà task. La UI continua
    comunque a mostrare il risultato completo via _mostra_risultato.
    """
    if len(testo) <= MAX_TOOL_CHARS:
        return testo
    omessi = len(testo) - MAX_TOOL_CHARS
    return testo[:MAX_TOOL_CHARS] + f"\n… (output troncato: {omessi} caratteri omessi)"


def _mostra_risultato(nome: str, risultato: str) -> None:
    """Stampa il risultato in modo compatto e colorato."""
    righe  = risultato.strip().splitlines()
    n      = len(righe)
    colore = "green" if risultato.startswith("✅") else "red" if risultato.startswith("ERRORE") else "dim"
    MAX    = 8 if nome in _OPS_SCRITTURA else 6

    for r in righe[:MAX]:
        console.print(f"    [{colore}]{r}[/{colore}]")
    if n > MAX:
        console.print(f"    [dim]... ({n - MAX} righe omesse)[/dim]")


# ── Conferma interattiva ──────────────────────────────────────────

def _rileva_attesa_conferma(testo: str) -> bool:
    t = testo.lower()
    return any(s in t for s in _SEGNALI_CONFERMA)


def _chiedi_conferma_utente(testo_agente: str) -> str | None:
    """
    Mostra il piano e chiede all'utente.
    Ritorna la risposta utente oppure None se annulla.
    """
    console.print()
    console.print(Panel(
        testo_agente,
        title="[yellow]⏸  L'agente aspetta una tua risposta[/yellow]",
        border_style="yellow",
    ))
    console.print()
    console.print("  [green]s / sì / ok / procedi[/green]  → prosegui")
    console.print("  [yellow]<testo libero>[/yellow]          → modifica il piano")
    console.print("  [red]n / no / annulla[/red]        → annulla")
    console.print()

    try:
        risposta = console.input("[bold yellow]Tu:[/bold yellow] ").strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not risposta or risposta.lower() in ("n", "no", "annulla", "stop", "esci"):
        console.print("[dim]Operazione annullata.[/dim]")
        return None

    if risposta.lower() in ("s", "sì", "si", "ok", "yes", "y", "procedi", "vai", "continua"):
        return "Sì, procedi con il piano che hai proposto."

    return risposta


# ── Loop ReAct ────────────────────────────────────────────────────

def run_agente(domanda: str, backend) -> str:
    """
    Loop ReAct trasparente con conferma interattiva.

    - Mostra ragionamento, tool calls e risultati in tempo reale.
    - Quando l'agente propone un piano aspetta la risposta dell'utente
      invece di uscire.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": domanda},
    ]
    step         = 0
    ops_eseguite = 0

    console.rule("[dim]avvio agente[/dim]")

    while True:
        step += 1
        console.print(f"\n[dim bold]┌─ Step {step} {'─'*40}[/dim bold]")

        # chiamata al modello
        console.print("[dim]│  ⏳ Elaborazione...[/dim]", end="\r")
        testo, tool_calls, raw_msg = backend.chat(messages)
        console.print("[dim]│                    [/dim]", end="\r")

        if testo and testo.strip():
            console.print("[dim]│[/dim]")
            preview = testo.strip()[:300]
            dots    = "..." if len(testo.strip()) > 300 else ""
            console.print(f"[dim]│  💭 [italic]{preview}{dots}[/italic][/dim]")

        # nessun tool → risposta finale o attesa conferma
        if not tool_calls:
            console.print("[dim]│[/dim]")

            if testo and _rileva_attesa_conferma(testo):
                console.print("[dim]└─ in attesa di conferma utente[/dim]")
                console.rule()
                risposta = _chiedi_conferma_utente(testo)

                if risposta is None:
                    return "Operazione annullata dall'utente."

                messages.append({"role": "assistant", "content": testo})
                messages.append({"role": "user",      "content": risposta})
                console.rule("[dim]ripresa agente[/dim]")
                continue

            console.print(f"[dim]└─ completato in {step} step, {ops_eseguite} operazioni[/dim]")
            console.rule()
            return testo.strip()

        # esegui tool calls — il messaggio assistant deve sempre contenere
        # sia il testo che i tool_calls, e avere role=assistant (per i backend
        # che ricostruiscono lo storico, es. Anthropic).
        messages.append({
            "role":       "assistant",
            "content":    testo or "",
            "tool_calls": tool_calls,
        })

        for idx, tc in enumerate(tool_calls):
            nome      = tc["function"]["name"]
            argomenti = tc["function"].get("arguments", {})

            # id stabile e univoco, condiviso fra il messaggio assistant e il
            # risultato del tool: i backend OpenAI-compatibili (LM Studio)
            # rifiutano la cronologia se gli id non combaciano.
            if not tc.get("id"):
                tc["id"] = f"call_{step}_{idx}"

            console.print("[dim]│[/dim]")
            console.print(f"[dim]│[/dim]  {_descrivi_tool(nome, argomenti)}")

            risultato = registry.esegui(nome, argomenti)

            if nome in _OPS_MODIFICANTI:
                ops_eseguite += 1

            _mostra_risultato(nome, risultato)

            messages.append({
                "role":        "tool",
                "content":     _limita_output(risultato),
                "tool_use_id": tc["id"],
            })

        if step >= MAX_STEPS:
            console.print(f"\n[yellow]⚠️  Limite {MAX_STEPS} step raggiunto[/yellow]")
            console.print("[dim]Aumenta con FILEAI_MAX_STEPS o nelle Impostazioni.[/dim]")
            break

    console.rule()
    return testo.strip()
