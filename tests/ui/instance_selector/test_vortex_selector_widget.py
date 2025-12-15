"""
Copyright (c) Cutleast
"""

import pytest
from base_test import BaseTest
from cutleast_core_lib.test.utils import Utils
from cutleast_core_lib.ui.widgets.placeholder_dropdown import PlaceholderDropdown
from pytestqt.qtbot import QtBot
from setup.mock_plyvel import MockPlyvelDB

from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.core.mod_manager.vortex.profile_info import ProfileInfo
from mod_manager_lib.core.mod_manager.vortex.vortex import Vortex
from mod_manager_lib.ui.instance_selector.vortex_selector_widget import (
    VortexSelectorWidget,
)

PROFILE_DROPDOWN: tuple[str, type[PlaceholderDropdown]] = (
    "profile_dropdown",
    PlaceholderDropdown,
)
"""Identifier for accessing the private profile_dropdown field."""


class TestVortexSelectorWidget(BaseTest):
    """
    Tests `ui.modinstance_selector.vortex_selector_widget.VortexSelectorWidget`.
    """

    @pytest.fixture
    def widget(
        self, full_vortex_db: MockPlyvelDB, qtbot: QtBot
    ) -> VortexSelectorWidget:
        """
        Fixture to create and provide a VortexSelectorWidget instance for tests.
        """

        vortex_widget = VortexSelectorWidget(
            Vortex().get_instance_names(GameService.get_game_by_id("skyrimse"))
        )
        qtbot.addWidget(vortex_widget)
        vortex_widget.show()
        return vortex_widget

    def assert_initial_state(self, widget: VortexSelectorWidget) -> None:
        """
        Asserts the initial state of the widget.
        """

        profile_dropdown: PlaceholderDropdown = Utils.get_private_field(
            widget, *PROFILE_DROPDOWN
        )

        assert profile_dropdown.currentIndex() == -1
        assert profile_dropdown.isEnabled()
        assert profile_dropdown.count() == 2
        assert not widget.validate()

    def test_initial_state(self, widget: VortexSelectorWidget) -> None:
        """
        Tests the initial state of the widget.
        """

        self.assert_initial_state(widget)

    def test_select_profile(
        self,
        vortex_profile_info: ProfileInfo,
        widget: VortexSelectorWidget,
        qtbot: QtBot,
    ) -> None:
        """
        Tests the selection of a profile.
        """

        # given
        profile_dropdown: PlaceholderDropdown = Utils.get_private_field(
            widget, *PROFILE_DROPDOWN
        )

        # then
        assert profile_dropdown.count() == 2
        assert profile_dropdown.itemText(0) == "Default (BkIX54nayg)"
        assert profile_dropdown.itemText(1) == "Test Instance (1a2b3c4d)"

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                profile_dropdown.setCurrentIndex(0)

        # then
        assert valid_signal.args == [True]
        assert widget.validate()

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                profile_dropdown.setCurrentIndex(-1)

        # then
        assert valid_signal.args == [False]
        assert not widget.validate()

        # when
        with qtbot.waitSignal(widget.changed):
            with qtbot.waitSignal(widget.valid) as valid_signal:
                profile_dropdown.setCurrentIndex(1)

        # then
        assert valid_signal.args == [True]
        assert widget.validate()

        # when
        profile_info: ProfileInfo = widget.get_instance(
            GameService.get_game_by_id("skyrimse")
        )

        # then
        assert profile_info.id == vortex_profile_info.id
