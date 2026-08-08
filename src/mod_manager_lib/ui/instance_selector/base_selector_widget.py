"""
Copyright (c) Cutleast
"""

from abc import abstractmethod
from typing import Generic, Optional, TypeVar, cast, override

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QSpinBox, QWidget

from mod_manager_lib.core.game import Game
from mod_manager_lib.core.mod_manager.apis import ModManagerApi
from mod_manager_lib.core.mod_manager.instance_info import InstanceInfo
from mod_manager_lib.core.mod_manager.mod_manager import ModManager
from mod_manager_lib.core.mod_manager.service import ModManagerService

InstanceInfoType = TypeVar("InstanceInfoType", bound=InstanceInfo)
ModManagerType = TypeVar("ModManagerType", bound=ModManager)


class BaseSelectorWidget(QWidget, Generic[InstanceInfoType, ModManagerType]):
    """
    Base class for selecting instances from a preselected mod manager.
    """

    _api: ModManagerType
    """The API of the corresponding mod manager."""

    _instance_names: list[str]
    """List of possible instance names."""

    changed = Signal()
    """This signal gets emitted everytime the selected instance changes."""

    valid = Signal(bool)
    """
    This signal gets emitted when the validation of the selected instance changes.
    
    Args:
        bool: `True` if the selected instance is valid, `False` otherwise.
    """

    def __init__(self, instance_names: Optional[list[str]] = None) -> None:
        """
        Args:
            instance_names (Optional[list[str]], optional):
                The names of the available mod instances. Defaults to None.
        """

        super().__init__()

        self._api = cast(
            ModManagerType,
            ModManagerService.get_mod_manager(self.__class__.get_mod_manager()),
        )
        self._instance_names = instance_names if instance_names is not None else []

        self._init_ui()

        self.changed.connect(self.__on_change)

    @classmethod
    @abstractmethod
    def get_mod_manager(cls) -> ModManagerApi:
        """
        Returns:
            ModManagerApi: The mod manager this selector belongs to
        """

    @abstractmethod
    def _init_ui(self) -> None: ...

    def __on_change(self) -> None:
        self.valid.emit(self.validate())

    @abstractmethod
    def _update(self) -> None: ...

    def set_instances(self, instance_names: list[str]) -> None:
        """
        Sets the list of possible instances.

        Args:
            instance_names (list[str]): The list of possible instances
        """

        self._instance_names = instance_names

        self._update()

    @abstractmethod
    def validate(self) -> bool:
        """
        Validates the selected instance.

        Returns:
            bool: `True` if the selected instance is valid, `False` otherwise
        """

    @abstractmethod
    def get_instance(self, game: Game) -> InstanceInfoType:
        """
        Returns the data for the selected instance and game.

        Args:
            game (Game): The game for which the selected instance belongs to.

        Returns:
            I: The data for the selected instance
        """

    @abstractmethod
    def set_instance(self, instance_data: InstanceInfoType) -> None:
        """
        Sets the currently selected instance.

        Args:
            instance_data (I): The data for the selected instance.
        """

    @abstractmethod
    def reset(self) -> None:
        """
        Resets the user selection.
        """

    @override
    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.Wheel
            and (isinstance(source, (QComboBox, QSpinBox)))
            and isinstance(event, QWheelEvent)
        ):
            self.wheelEvent(event)
            return True

        return super().eventFilter(source, event)
