"""
backends/base.py — Interfaccia astratta per i backend AI

Ogni backend implementa un solo metodo: chat().
Questo garantisce che agent.py non dipenda da Ollama o Claude direttamente.

Tutti i backend ereditano anche un contatore cumulativo `uso_totale` che
viene aggiornato dentro `chat()` dopo ogni risposta del modello. L'agente
lo legge a fine task per stampare token consumati e costo stimato.
"""

from abc import ABC, abstractmethod


class BaseBackend(ABC):
    """
    Contratto che ogni backend deve rispettare.

    chat() riceve la lista completa di messaggi e ritorna sempre la stessa
    tripla (testo, tool_calls, raw_msg), indipendentemente dal provider.

    Le sottoclassi DEVONO chiamare `super().__init__()` per inizializzare
    il contatore token, e DEVONO aggiornare `uso_totale` dentro `chat()`
    quando il provider espone i conteggi (Claude, LM Studio, Ollama li
    forniscono tutti).
    """

    # identificativo del backend ("claude", "ollama", "lmstudio") usato
    # da pricing.formatta_riepilogo_uso per decidere se calcolare il costo
    kind: str = "sconosciuto"

    def __init__(self) -> None:
        self.uso_totale: dict[str, int] = {
            "input":       0,
            "output":      0,
            "cache_write": 0,
            "cache_read":  0,
            "chiamate":    0,
        }

    @property
    def model_name(self) -> str:
        return getattr(self, "model", "") or ""

    def aggiorna_uso(
        self,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_write: int = 0,
        cache_read: int = 0,
    ) -> None:
        """Aggiorna il contatore cumulativo dopo una chiamata al modello."""
        self.uso_totale["input"]       += max(0, int(input_tokens or 0))
        self.uso_totale["output"]      += max(0, int(output_tokens or 0))
        self.uso_totale["cache_write"] += max(0, int(cache_write or 0))
        self.uso_totale["cache_read"]  += max(0, int(cache_read or 0))
        self.uso_totale["chiamate"]    += 1

    @abstractmethod
    def chat(self, messages: list[dict]) -> tuple[str, list, dict]:
        """
        Chiama il modello con la cronologia dei messaggi.

        Returns:
            testo      — testo libero della risposta (può essere vuoto)
            tool_calls — lista di tool da eseguire (vuota se risposta finale)
            raw_msg    — messaggio grezzo da aggiungere alla cronologia
        """
        ...
