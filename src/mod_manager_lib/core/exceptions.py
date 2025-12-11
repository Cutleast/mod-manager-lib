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
