"""
Copyright (c) Cutleast
"""

from pathlib import Path
from typing import Any

from base_test import BaseTest, MO2InstanceInfo

from mod_manager_lib.core.game_service import GameService


class TestMO2InstanceInfo(BaseTest):
    """
    Tests `core.mod_manager.modorganizer.mo2_instance_info.MO2InstanceInfo`.
    """

    def test_serialization(self) -> None:
        """
        Tests the serialization of MO2InstanceInfo.
        """

        # given
        mo2_instance_info = MO2InstanceInfo(
            display_name="Test Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=Path("Test Instance"),
            mods_folder=Path("Test Instance/mods"),
            profiles_folder=Path("Test Instance/profiles"),
        )

        # when
        actual: dict[str, Any] = mo2_instance_info.model_dump(mode="json")

        # then
        assert actual == {
            "display_name": "Test Instance",
            "game": "skyrimse",
            "profile": "Default",
            "is_global": False,
            "base_folder": "Test Instance",
            "mods_folder": "Test Instance\\mods",
            "profiles_folder": "Test Instance\\profiles",
            "mod_manager": "Mod Organizer 2",
        }

    def test_deserialization(self) -> None:
        """
        Tests the deserialization of MO2InstanceInfo.
        """

        # given
        data = {
            "display_name": "Test Instance",
            "game": "skyrimse",
            "profile": "Default",
            "is_global": False,
            "base_folder": "Test Instance",
            "mods_folder": "Test Instance/mods",
            "profiles_folder": "Test Instance/profiles",
            "mod_manager": "Mod Organizer 2",
        }

        # when
        actual = MO2InstanceInfo.model_validate(data)

        # then
        expected = MO2InstanceInfo(
            display_name="Test Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=Path("Test Instance"),
            mods_folder=Path("Test Instance/mods"),
            profiles_folder=Path("Test Instance/profiles"),
        )
        assert actual == expected
