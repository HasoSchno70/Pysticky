"""
Hintergrund-Worker für GUI-Operationen.

QObject-Subklassen, die rechenintensive Arbeit in eigenen QThreads
ausführen und Ergebnisse via Signal an den UI-Thread liefern.
"""

from .optimization_worker import OptimizationWorker

__all__ = ["OptimizationWorker"]
