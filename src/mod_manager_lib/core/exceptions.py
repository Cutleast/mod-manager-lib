"""
Copyright (c) Cutleast
"""

from typing import override

from cutleast_core_lib.core.utilities.exceptions import LocalizedException
from qtpy.QtWidgets import QApplication


class GameNotFoundError(LocalizedException):
    """
    Exception when the installation folder for a game could not be found.
    """

    @override
    def getLocalizedMessage(self) -> str:
        return QApplication.translate(
            "exceptions",
            "The installation folder for the selected game could not be found!",
        )


class CyclicModConflictError(LocalizedException):
    """
    Exception when mod conflict rules contain a cycle.
    """

    def __init__(self, cycle: list[str]) -> None:
        """
        Args:
            cycle (list[str]): Mod names forming the detected cycle.
        """

        self.cycle: list[str] = cycle.copy()
        super().__init__(" → ".join(self.cycle))

    @override
    def getLocalizedMessage(self) -> str:
        return QApplication.translate(
            "exceptions",
            "The mod conflict rules contain a cycle: {0}\n"
            "Resolve these rules in Vortex and try again.",
        )
