"""
Copyright (c) Cutleast
"""

from typing import Optional, override

from cutleast_core_lib.ui.widgets.enum_placeholder_dropdown import (
    EnumPlaceholderDropdown,
)
from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QSpinBox,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from mod_manager_lib.core.game import Game
from mod_manager_lib.core.mod_manager.instance_info import InstanceInfo
from mod_manager_lib.core.mod_manager.mod_manager import ModManager
from mod_manager_lib.core.mod_manager.mod_manager_api import ModManagerApi

from . import INSTANCE_WIDGETS
from .base_creator_widget import BaseCreatorWidget


class InstanceCreatorWidget(QWidget):
    """
    Widget for creating and customizing the destination instance.
    """

    instance_valid = Signal(bool)
    """
    This signal is emitted when the instance is valid.
    """

    __cur_mod_manager: Optional[ModManager] = None
    """
    Selected destination mod manager.
    """

    __mod_managers: dict[ModManager, BaseCreatorWidget]
    """
    Maps mod managers to their corresponding instance widgets.
    """

    __vlayout: QVBoxLayout
    __mod_manager_dropdown: EnumPlaceholderDropdown[ModManager]
    __instance_stack_layout: QStackedLayout
    __placeholder_widget: QWidget

    def __init__(self) -> None:
        super().__init__()

        self.__init_ui()

        self.__mod_manager_dropdown.currentValueChanged.connect(
            self.__set_cur_mod_manager
        )
        self.__mod_manager_dropdown.setCurrentValue(None)

    def __init_ui(self) -> None:
        self.__vlayout = QVBoxLayout()
        self.__vlayout.setContentsMargins(0, 0, 0, 0)
        self.__vlayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.__vlayout)

        self.__init_header()
        self.__init_instance_widgets()

    def __init_header(self) -> None:
        glayout = QGridLayout()
        glayout.setContentsMargins(0, 0, 0, 0)
        glayout.setColumnStretch(0, 1)
        glayout.setColumnStretch(1, 3)
        self.__vlayout.addLayout(glayout)

        mod_manager_label = QLabel(self.tr("Mod manager:"))
        glayout.addWidget(mod_manager_label, 0, 0)

        self.__mod_manager_dropdown = EnumPlaceholderDropdown(ModManager)
        self.__mod_manager_dropdown.installEventFilter(self)
        glayout.addWidget(self.__mod_manager_dropdown, 0, 1)

    def __init_instance_widgets(self) -> None:
        self.__instance_stack_layout = QStackedLayout()
        self.__instance_stack_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.__placeholder_widget = QWidget()
        self.__instance_stack_layout.addWidget(self.__placeholder_widget)
        self.__vlayout.addLayout(self.__instance_stack_layout)

        self.__mod_managers = {}

        for instance_widget_type in INSTANCE_WIDGETS:
            mod_manager: ModManager = instance_widget_type.get_mod_manager()

            instance_widget: BaseCreatorWidget = instance_widget_type()
            instance_widget.valid.connect(self.instance_valid.emit)

            self.__instance_stack_layout.addWidget(instance_widget)
            self.__mod_managers[mod_manager] = instance_widget

    def __set_cur_mod_manager(self, mod_manager: Optional[ModManager]) -> None:
        if mod_manager is not None:
            instance_widget: BaseCreatorWidget = self.__mod_managers[mod_manager]
            self.__instance_stack_layout.setCurrentWidget(instance_widget)
            self.instance_valid.emit(instance_widget.validate())
        else:
            self.__instance_stack_layout.setCurrentWidget(self.__placeholder_widget)
            self.instance_valid.emit(False)

        self.__cur_mod_manager = mod_manager

    def get_selected_mod_manager(self) -> Optional[ModManager]:
        """
        Returns the currently selected mod manager.

        Returns:
            Optional[ModManager]: The selected mod manager.
        """

        return self.__cur_mod_manager

    def validate(self) -> bool:
        """
        Returns whether the currently selected instance data is valid.

        Returns:
            bool: whether the currently selected instance data is valid
        """

        if self.__cur_mod_manager is not None:
            instance_widget: BaseCreatorWidget = self.__mod_managers[
                self.__cur_mod_manager
            ]
            return instance_widget.validate()

        return False

    def get_instance_data(self, game: Game) -> InstanceInfo:
        """
        Returns the customized destination instance data.

        Args:
            game (Game): The selected game.

        Raises:
            ValueError:
                when no mod manager is selected or the customized instance is invalid.

        Returns:
            InstanceData: The customized destination instance data.
        """

        mod_manager: Optional[ModManagerApi] = self.get_selected_mod_manager()

        if mod_manager is None:
            raise ValueError("No mod manager selected!")

        instance_widget: BaseCreatorWidget = self.__mod_managers[mod_manager]

        if not instance_widget.validate():
            raise ValueError("Customized instance data is invalid!")

        return instance_widget.get_instance(game)

    @override
    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.Wheel
            and (isinstance(source, QComboBox) or isinstance(source, QSpinBox))
            and isinstance(event, QWheelEvent)
        ):
            self.wheelEvent(event)
            return True

        return super().eventFilter(source, event)
