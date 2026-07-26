"""
Copyright (c) Cutleast
"""

from typing import override

from cutleast_core_lib.core.utilities.exceptions import LocalizedException
from PySide6.QtWidgets import QApplication


class ModManagerError(LocalizedException):
    """
    Exception for general mod manager-related errors.
    """

    @override
    def getLocalizedMessage(self) -> str:
        return QApplication.translate("exceptions", "A mod manager error occured!")


class InstanceNotFoundError(ModManagerError):
    """
    Exception when a mod instance does not exist.
    """

    def __init__(self, instance_name: str) -> None:
        """
        Args:
            instance_name (str): The name of the mod instance that could not be found.
        """

        super().__init__(instance_name)

    @override
    def getLocalizedMessage(self) -> str:
        return QApplication.translate(
            "exceptions", "The mod instance {0} could not be found!"
        )


class InstanceCreationError(ModManagerError):
    """
    Exception when a mod instance could not be created.
    """

    @override
    def getLocalizedMessage(self) -> str:
        return QApplication.translate(
            "exceptions", "The mod instance could not be created!"
        )
