"""
cli.py — Comandi CLI e entry point
"""

import sys
import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fileai.config import (
    parse_modello, modello_da_args, get_default_modello,
    set_default_modello, CLAUDE_MODELS,
)
from fileai.backends import crea_backend
from fileai.agent import run_agente

console = Console()


# ── Helpers UI ────────────────────────────────────────────────────

def _header(titolo: str, dettagli: str = "") -> None:
    console.print()
    console.print(Panel(
        f"[bold]{titolo}[/bold]" + (f"\n[dim]{dettagli}[/dim]" if dettagli else ""),
        border_style="cyan",
        expand=False,
    ))
    console.print()


def _risultato(titolo: str, testo: str) -> None:
    console.print()
    console.print(Panel(testo, title=f"[green]✅ {titolo}[/green]", border_style="green"))


def _stampa_modelli_ollama() -> None:
    try:
        import ollama as _ollama
        modelli = _ollama.list().get("models", [])
        if not modelli:
            console.print("[yellow]Nessun modello Ollama installato.[/yellow]")
            console.print("[dim]Installa con: ollama pull llama3.1[/dim]")
            return
        t = Table(title="Modelli Ollama disponibili")
        t.add_column("Spec (-m)",   style="cyan",  no_wrap=True)
        t.add_column("Nome",        style="white")
        t.add_column("Dimensione",  style="dim",   justify="right")
        for m in modelli:
            nome = m.get("name") or m.get("model", "?")
            size = m.get("size", 0)
            gb   = f"{size / 1e9:.1f} GB" if size else "?"
            t.add_row(f"ollama:{nome}", nome, gb)
        console.print(t)
    except ImportError:
        console.print("[red]ollama non installato[/red]")
    except Exception as e:
        console.print(f"[yellow]Impossibile listare modelli: {e}[/yellow]")
        console.print("[dim]Assicurati che 'ollama serve' sia in esecuzione[/dim]")


def _stampa_modelli_claude() -> None:
    t = Table(title="Modelli Claude disponibili")
    t.add_column("Spec (-m)",   style="cyan",  no_wrap=True)
    t.add_column("Nome",        style="white")
    t.add_column("Note",        style="dim")
    rows = [
        ("claude",        CLAUDE_MODELS["default"], "default"),
        ("claude:sonnet", CLAUDE_MODELS["sonnet"],  "veloce, consigliato"),
        ("claude:opus",   CLAUDE_MODELS["opus"],    "più potente"),
        ("claude:haiku",  CLAUDE_MODELS["haiku"],   "leggero"),
    ]
    for spec, nome, note in rows:
        t.add_row(spec, nome, note)
    console.print(t)


# ── Comandi ───────────────────────────────────────────────────────

def cmd_modelli(args, _backend) -> None:
    console.print()
    _stampa_modelli_ollama()
    console.print()
    _stampa_modelli_claude()
    console.print()
    default = get_default_modello()
    console.print(f"[dim]Default attuale: [bold]{default}[/bold]  "
                  f"(cambia con: fileai default <modello>)[/dim]")


def cmd_default(args, _backend) -> None:
    spec = args.spec
    bt, mn = parse_modello(spec)
    set_default_modello(spec)
    console.print(f"[green]✅ Default impostato: [bold]{spec}[/bold][/green]")
    console.print(f"[dim]   backend={bt}, model={mn}[/dim]")


def cmd_chat(args, backend) -> None:
    spec_corrente = modello_da_args(args)
    _backend_ref  = [backend]

    console.print(Panel(
        f"[bold cyan]FileAI[/bold cyan] — Gestione intelligente di file e cartelle\n"
        f"[dim]Modello: [bold]{spec_corrente}[/bold]  |  'help' per comandi  |  'esci' per uscire[/dim]",
        border_style="cyan",
    ))

    while True:
        try:
            domanda = console.input("\n[bold cyan]Tu:[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Arrivederci![/dim]")
            break

        if not domanda:
            continue

        match domanda.lower():
            case "esci" | "exit" | "quit":
                console.print("[dim]Arrivederci![/dim]")
                break

            case "help":
                t = Table(show_header=False, box=None, padding=(0, 2))
                t.add_row("[cyan]modello <spec>[/cyan]", "Cambia modello per questa sessione")
                t.add_row("[cyan]modelli[/cyan]",         "Lista modelli disponibili")
                t.add_row("[cyan]modello attuale[/cyan]", "Mostra modello corrente")
                t.add_row("[cyan]esci[/cyan]",            "Esci")
                console.print(t)

            case "modelli":
                _stampa_modelli_ollama()
                _stampa_modelli_claude()

            case "modello attuale":
                console.print(f"[dim]Modello: [bold]{spec_corrente}[/bold][/dim]")

            case _ if domanda.lower().startswith("modello "):
                nuova_spec = domanda[8:].strip()
                try:
                    _backend_ref[0] = crea_backend(nuova_spec)
                    spec_corrente   = nuova_spec
                    console.print(f"[green]✅ Modello: {nuova_spec}[/green]")
                except Exception as e:
                    console.print(f"[red]Errore: {e}[/red]")

            case _:
                console.print()
                # chat libera: sola lettura, nessuna operazione di modifica
                risposta = run_agente(domanda, _backend_ref[0], solo_lettura=True)
                console.print()
                console.print(Panel(risposta, title="[green]✅ Risposta[/green]", border_style="green"))


def cmd_organizza(args, backend) -> None:
    _header(
        "📁 Organizzazione cartella",
        f"Percorso: {Path(args.cartella).expanduser().resolve()}"
    )
    risposta = run_agente(
        f"Analizza la cartella '{args.cartella}': usa prima scansione_intelligente, "
        f"poi proponi un piano di organizzazione con sottocartelle per tipo, "
        f"aspetta conferma e poi esegui. Riassumi alla fine.",
        backend,
    )
    _risultato("Organizzazione completata", risposta)


def cmd_cerca(args, backend) -> None:
    _header("🔎 Ricerca file", f"'{args.testo}' in {Path(args.cartella).expanduser().resolve()}")
    risposta = run_agente(
        f"Cerca '{args.testo}' nella cartella '{args.cartella}'. "
        f"Mostra percorsi completi, dimensioni e date.",
        backend,
    )
    _risultato("Risultati ricerca", risposta)


def cmd_crea(args, backend) -> None:
    _header("📁 Creazione struttura", f"{args.struttura} → {Path(args.dove).expanduser().resolve()}")
    risposta = run_agente(
        f"Crea questa struttura di cartelle in '{args.dove}': {args.struttura}. "
        f"Interpreta e crea tutte le cartelle necessarie. Elenca cosa hai creato.",
        backend,
    )
    _risultato("Struttura creata", risposta)


def cmd_info(args, backend) -> None:
    _header("📊 Analisi cartella", f"Percorso: {Path(args.cartella).expanduser().resolve()}")
    risposta = run_agente(
        f"Analisi completa della cartella '{args.cartella}': "
        f"usa analizza_cartella, scansione_intelligente, controlla_salute_cartella, trova_duplicati. "
        f"Fornisci un rapporto completo con suggerimenti.",
        backend,
    )
    _risultato("Analisi completata", risposta)


def cmd_chiedi(args, backend) -> None:
    _header("⚡ Esecuzione comando", args.comando)
    risposta = run_agente(args.comando, backend)
    _risultato("Completato", risposta)


def cmd_annulla(args, backend) -> None:
    _header("↩️  Annullamento operazioni (rollback)", f"Ultime {args.quante} operazioni")
    risposta = run_agente(
        f"Mostra prima la cronologia con mostra_cronologia, poi annulla le ultime "
        f"{args.quante} operazioni con annulla_ultima_operazione (quante={args.quante}) "
        f"e riepiloga cosa è stato ripristinato.",
        backend,
    )
    _risultato("Rollback completato", risposta)


def cmd_cronologia(args, backend) -> None:
    _header("📜 Cronologia operazioni", f"Ultime {args.quante}")
    risposta = run_agente(
        f"Mostra la cronologia delle ultime {args.quante} operazioni con "
        f"mostra_cronologia (quante={args.quante}).",
        backend,
        solo_lettura=True,
    )
    _risultato("Cronologia", risposta)


# ── Argparse ──────────────────────────────────────────────────────

def _add_modello(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "-m", "--modello",
        metavar="SPEC",
        default=None,
        help="Modello (es: ollama:llama3.1, claude, claude:opus). Default: config salvata.",
    )


def main() -> None:
    # assicura che tutti i tool siano registrati
    import fileai.tools  # noqa: F401

    parser = argparse.ArgumentParser(
        prog="fileai",
        description="Gestione intelligente di file e cartelle con AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SINTASSI MODELLO (-m):
  ollama                 Ollama default (llama3.1)
  ollama:qwen2.5         Ollama modello specifico
  claude                 Claude Sonnet (default)
  claude:opus            Claude Opus

ESEMPI:
  fileai modelli
  fileai default ollama:qwen2.5
  fileai chat
  fileai chat -m claude:opus
  fileai organizza ~/Downloads -m claude
  fileai cerca "relazione" ~/Documenti -m ollama:llama3.1
  fileai crea "Django: app templates static docs" ~/Progetti/miosito
  fileai info ~/Desktop -m claude
  fileai chiedi "trova tutti i PDF più grandi di 10MB in ~/Documenti"
        """,
    )
    sub = parser.add_subparsers(dest="cmd", metavar="COMANDO")
    sub.required = True

    # modelli
    p = sub.add_parser("modelli", help="Lista tutti i modelli disponibili")
    p.set_defaults(func=cmd_modelli)

    # default
    p = sub.add_parser("default", help="Imposta il modello di default")
    p.add_argument("spec", help="Es: ollama:llama3.1  o  claude:sonnet")
    p.set_defaults(func=cmd_default)

    # chat
    p = sub.add_parser("chat", help="Modalità interattiva")
    _add_modello(p)
    p.set_defaults(func=cmd_chat)

    # organizza
    p = sub.add_parser("organizza", help="Organizza una cartella per tipo di file")
    p.add_argument("cartella")
    _add_modello(p)
    p.set_defaults(func=cmd_organizza)

    # cerca
    p = sub.add_parser("cerca", help="Cerca file per nome o contenuto")
    p.add_argument("testo")
    p.add_argument("cartella")
    _add_modello(p)
    p.set_defaults(func=cmd_cerca)

    # crea
    p = sub.add_parser("crea", help="Crea struttura cartelle da descrizione")
    p.add_argument("struttura", help="Descrizione es: 'Django: app templates static'")
    p.add_argument("dove",      help="Cartella padre")
    _add_modello(p)
    p.set_defaults(func=cmd_crea)

    # info
    p = sub.add_parser("info", help="Analisi completa di una cartella")
    p.add_argument("cartella")
    _add_modello(p)
    p.set_defaults(func=cmd_info)

    # chiedi
    p = sub.add_parser("chiedi", help="Operazione in linguaggio naturale")
    p.add_argument("comando", nargs="+")
    _add_modello(p)
    p.set_defaults(func=cmd_chiedi)

    # annulla
    p = sub.add_parser("annulla", help="Rollback: annulla le ultime operazioni eseguite")
    p.add_argument("quante", nargs="?", type=int, default=1,
                   help="Quante operazioni annullare (default: 1)")
    _add_modello(p)
    p.set_defaults(func=cmd_annulla)

    # cronologia
    p = sub.add_parser("cronologia", help="Mostra le ultime operazioni eseguite")
    p.add_argument("quante", nargs="?", type=int, default=10,
                   help="Quante voci mostrare (default: 10)")
    _add_modello(p)
    p.set_defaults(func=cmd_cronologia)

    args = parser.parse_args()

    # comandi senza backend
    if args.cmd in ("modelli", "default"):
        args.func(args, None)
        return

    # normalizza args.comando per cmd_chiedi
    if args.cmd == "chiedi":
        args.comando = " ".join(args.comando)

    # crea backend
    spec = modello_da_args(args)
    try:
        backend = crea_backend(spec)
        console.print(f"[dim]🤖 {backend}[/dim]")
    except Exception as e:
        console.print(Panel(
            f"[red]Impossibile inizializzare il modello '{spec}'[/red]\n\n{e}",
            border_style="red",
        ))
        sys.exit(1)

    args.func(args, backend)


if __name__ == "__main__":
    main()
