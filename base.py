"""
backends/base.py — Interfaccia astratta per i backend AI

Ogni backend implementa un solo metodo: chat().
Questo garantisce che agent.py non dipenda da Ollama o Claude direttamente.
"""

from abc import ABC, abstractmethod


class BaseBackend(ABC):
    """
    Contratto che ogni backend deve rispettare.

    chat() riceve la lista completa di messaggi e ritorna sempre la stessa
    tripla (testo, tool_calls, raw_msg), indipendentemente dal provider.
    """

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
