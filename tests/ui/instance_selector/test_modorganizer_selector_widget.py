"""
Copyright (c) Cutleast
"""

from pathlib import Path

import pytest
from base_test import BaseTest
from cutleast_core_lib.core.utilities.env_resolver import resolve
from cutleast_core_lib.test.utils import Utils
from cutleast_core_lib.ui.widgets.browse_edit import BrowseLineEdit
from pyfakefs.fake_filesystem import FakeFilesystem
from PySide6.QtWidgets import QComboBox
from pytestqt.qtbot import QtBot

from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.core.mod_manager.modorganizer.mo2_instance_info import (
    MO2InstanceInfo,
)
from mod_manager_lib.core.mod_manager.modorganizer.modorganizer import ModOrganizer
from mod_manager_lib.ui.instance_selector.modorganizer_selector_widget import (
    ModOrganizerSelectorWidget,
)


class TestModOrganizerSelectorWidget(BaseTest):
    """
    Tests `ui.modinstance_selector.modorganizer_selector_widget.ModOrganizerSelectorWidget`.
    """

    INSTANCE_DROPDOWN: tuple[str, type[QComboBox]] = "instance_dropdown", QComboBox
    """Identifier for accessing the private instance_dropdown field."""

    PORTABLE_PATH_ENTRY: tuple[str, type[BrowseLineEdit]] = (
        "portable_path_entry",
        BrowseLineEdit,
    )
    """Identifier for accessing the private portable_path_entry field."""

    PROFILE_DROPDOWN: tuple[str, type[QComboBox]] = "profile_dropdown", QComboBox
    """Identifier for accessing the private profile_dropdown field."""

    @pytest.fixture
    def widget(
        self, test_fs: FakeFilesystem, qtbot: QtBot
    ) -> ModOrganizerSelectorWidget:
        """
        Fixture to create and provide a ModOrganizerSelectorWidget instance for tests.
        """

        mo2_widget = ModOrganizerSelectorWidget(
            ModOrganizer().get_instance_names(GameService.get_game_by_id("skyrimse"))
        )
        qtbot.addWidget(mo2_widget)
        mo2_widget.show()
        return mo2_widget

    def assert_initial_state(self, widget: ModOrganizerSelectorWidget) -> None:
        """
        Asserts the initial state of the widget.
        """

        instance_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.INSTANCE_DROPDOWN
        )
        portable_path_entry: BrowseLineEdit = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PORTABLE_PATH_ENTRY
        )
        profile_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PROFILE_DROPDOWN
        )

        assert instance_dropdown.currentIndex() == 0
        assert instance_dropdown.isEnabled()
        assert portable_path_entry.text() == ""
        assert not portable_path_entry.isEnabled()
        assert profile_dropdown.currentIndex() == 0
        assert not profile_dropdown.isEnabled()
        assert not widget.validate()

    def test_initial_state(self, widget: ModOrganizerSelectorWidget) -> None:
        """
        Tests the initial state of the widget.
        """

        self.assert_initial_state(widget)

    def test_select_global_instance(
        self, test_fs: FakeFilesystem, widget: ModOrganizerSelectorWidget, qtbot: QtBot
    ) -> None:
        """
        Tests the selection of a global instance.
        """

        # given
        instance_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.INSTANCE_DROPDOWN
        )
        portable_path_entry: BrowseLineEdit = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PORTABLE_PATH_ENTRY
        )
        profile_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PROFILE_DROPDOWN
        )

        # then
        assert instance_dropdown.count() == 3
        assert instance_dropdown.itemText(1) == "Test Instance"
        assert instance_dropdown.itemText(2) == "Portable"

        # when
        with qtbot.waitSignal(widget.changed):
            instance_dropdown.setCurrentIndex(1)

        # then
        assert not portable_path_entry.isEnabled()
        assert profile_dropdown.isEnabled()
        assert profile_dropdown.count() == 3
        assert profile_dropdown.itemText(1) == "Default"
        assert profile_dropdown.itemText(2) == "TestProfile"
        assert not widget.validate()

        # when
        with qtbot.waitSignal(widget.changed):
            profile_dropdown.setCurrentIndex(2)

        # then
        assert widget.validate()

        # when
        instance_data: MO2InstanceInfo = widget.get_instance(
            GameService.get_game_by_id("skyrimse")
        )

        # then
        assert instance_data.display_name == "Test Instance"
        assert (
            instance_data.base_folder
            == resolve(Path("%LOCALAPPDATA%")) / "ModOrganizer" / "Test Instance"
        )
        assert instance_data.profile == "TestProfile"

    def test_select_portable_instance(
        self,
        test_fs: FakeFilesystem,
        mo2_instance_info: MO2InstanceInfo,
        widget: ModOrganizerSelectorWidget,
        qtbot: QtBot,
    ) -> None:
        """
        Tests the selection of a portable instance.
        """

        # given
        instance_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.INSTANCE_DROPDOWN
        )
        portable_path_entry: BrowseLineEdit = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PORTABLE_PATH_ENTRY
        )
        profile_dropdown: QComboBox = Utils.get_private_field(
            widget, *TestModOrganizerSelectorWidget.PROFILE_DROPDOWN
        )

        # then
        assert instance_dropdown.count() == 3
        assert instance_dropdown.itemText(1) == "Test Instance"
        assert instance_dropdown.itemText(2) == "Portable"

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                instance_dropdown.setCurrentIndex(2)

        # then
        assert valid_signal.args == [False]
        assert portable_path_entry.isEnabled()
        assert not profile_dropdown.isEnabled()
        assert not widget.validate()

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                portable_path_entry.setPath(mo2_instance_info.base_folder)

        # then
        assert valid_signal.args == [False]
        assert profile_dropdown.isEnabled()
        assert profile_dropdown.count() == 3
        assert profile_dropdown.itemText(1) == "Default"
        assert profile_dropdown.itemText(2) == "TestProfile"
        assert not widget.validate()

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                profile_dropdown.setCurrentIndex(2)

        # then
        assert valid_signal.args == [True]
        assert widget.validate()

        # when
        instance_data: MO2InstanceInfo = widget.get_instance(
            GameService.get_game_by_id("skyrimse")
        )

        # then
        assert instance_data.display_name == "Portable"
        assert instance_data.base_folder == mo2_instance_info.base_folder
        assert instance_data.profile == "TestProfile"
