"""
Copyright (c) Cutleast
"""

from base_test import BaseTest

from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.core.mod_manager.vortex.profile_info import ProfileInfo


class TestProfileInfo(BaseTest):
    """
    Tests `core.mod_manager.vortex.profile_info.ProfileInfo`.
    """

    def test_serialization(self) -> None:
        """
        Tests the serialization of ProfileInfo.
        """

        # given
        profile_info = ProfileInfo(
            display_name="Default Profile",
            game=GameService.get_game_by_id("skyrimse"),
            id="1a2b3c4d",
        )

        # when
        actual = profile_info.model_dump(
            mode="json",
            exclude_defaults=True,  # to test that the discriminator is still serialized
        )

        # then
        assert actual == {
            "display_name": "Default Profile",
            "game": "skyrimse",
            "id": "1a2b3c4d",
            "mod_manager": "Vortex",
        }

    def test_deserialization(self) -> None:
        """
        Tests the deserialization of ProfileInfo.
        """

        # given
        data = {
            "display_name": "Default Profile",
            "game": "skyrimse",
            "id": "1a2b3c4d",
            "mod_manager": "Vortex",
        }

        # when
        profile_info = ProfileInfo.model_validate(data)

        # then
        assert profile_info == ProfileInfo(
            display_name="Default Profile",
            game=GameService.get_game_by_id("skyrimse"),
            id="1a2b3c4d",
        )
