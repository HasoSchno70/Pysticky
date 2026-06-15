"""
Hintergrund-Worker fuer GUI-Operationen.

QObject-Subklassen, die rechenintensive Arbeit in eigenen QThreads
ausfuehren und Ergebnisse via Signal an den UI-Thread liefern.
"""

from .optimization_worker import OptimizationWorker

__all__ = ["OptimizationWorker"]
