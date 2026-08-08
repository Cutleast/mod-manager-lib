"""
Copyright (c) Cutleast
"""

import logging
from abc import abstractmethod
from typing import Generic, TypeVar, override

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget

from mod_manager_lib.core.game import Game
from mod_manager_lib.core.mod_manager.apis import ModManagerApi
from mod_manager_lib.core.mod_manager.instance_info import InstanceInfo

InstanceInfoType = TypeVar("InstanceInfoType", bound=InstanceInfo)


class BaseCreatorWidget(QWidget, Generic[InstanceInfoType]):
    """
    Base class for customizing an instance for a preselected mod manager.
    """

    valid = Signal(bool)
    """
    This signal gets emitted when the validation of the customized instance changes.

    Args:
        bool: `True` if the customized instance is valid, `False` otherwise.
    """

    log: logging.Logger

    @override
    def __init__(self) -> None:
        super().__init__()

        self.log = logging.getLogger(self.__class__.__name__)

        self._init_ui()

    @classmethod
    @abstractmethod
    def get_mod_manager(cls) -> ModManagerApi:
        """
        Returns:
            ModManagerApi: The mod manager this selector belongs to
        """

    @abstractmethod
    def _init_ui(self) -> None: ...

    @abstractmethod
    def validate(self) -> bool:
        """
        Validates the customized instance data.

        Returns:
            bool: `True` if the customized instance is valid, `False` otherwise
        """

    @abstractmethod
    def get_instance(self, game: Game) -> InstanceInfoType:
        """
        Gets the data for the customized instance.

        Args:
            game (Game): The game of the instance

        Returns:
            InstanceInfoType: The data for the customized instance
        """
