"""
Worker-Klasse fuer die Hintergrund-Optimierung von Stickpfaden.

Fuehrt die Optimierung und den Strategievergleich in einem
separaten Thread durch, um die GUI nicht zu blockieren.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ...core import (
    OptimizationStrategy,
    Pattern,
    StitchPathOptimizer,
    compare_strategies,
)


class OptimizationWorker(QObject):
    """Worker fuer Hintergrund-Optimierung."""

    progress = Signal(int, int, str)  # current, total, message
    finished = Signal(object)  # OptimizationResult oder None
    comparison_finished = Signal(object)  # dict oder None

    # Signale zum Starten der Arbeit (vom Hauptthread)
    start_optimization = Signal(object, int)  # strategy, fabric_count
    start_comparison = Signal(int)  # fabric_count

    def __init__(self, pattern: Pattern) -> None:
        super().__init__()
        self._pattern = pattern
        self._cancelled = False

    def cancel(self) -> None:
        """Markiert den Worker zum Abbrechen."""
        self._cancelled = True

    def _is_cancelled(self) -> bool:
        """Prueft ob abgebrochen wurde."""
        return self._cancelled

    def _report_progress(self, current: int, total: int, message: str) -> None:
        """Meldet Fortschritt an GUI."""
        self.progress.emit(current, total, message)

    def _run_optimization(self, strategy: OptimizationStrategy, fabric_count: int) -> None:
        """Fuehrt einzelne Optimierung durch."""
        self._cancelled = False

        optimizer = StitchPathOptimizer(
            self._pattern, progress_callback=self._report_progress, cancel_check=self._is_cancelled
        )

        result = optimizer.optimize(strategy, fabric_count)
        self.finished.emit(result)

    def _run_comparison(self, fabric_count: int) -> None:
        """Vergleicht alle Strategien."""
        self._cancelled = False

        results = compare_strategies(
            self._pattern,
            fabric_count,
            progress_callback=self._report_progress,
            cancel_check=self._is_cancelled,
        )

        self.comparison_finished.emit(results)
