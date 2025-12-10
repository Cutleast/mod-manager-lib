"""
Copyright (c) Cutleast
"""

from base_test import BaseTest

from core.game import Game
from core.game_service import GameService


class TestGameService(BaseTest):
    """
    Tests for `core.game_service.GameService`.
    """

    def test_get_games_with_cache(self) -> None:
        """
        Tests the cached `GameService.get_supported_games()` method.
        """

        # when
        games1: list[Game] = GameService.get_supported_games()
        games2: list[Game] = GameService.get_supported_games()

        # then
        assert games1 == games2
        assert games1 is games2
        assert all(games1[i] is games2[i] for i in range(len(games1)))

    def test_get_game_by_id_with_cache(self) -> None:
        """
        Tests the cached `GameService.get_game_by_id()` method.
        """

        # given
        skyrimse: Game = GameService.get_game_by_id("skyrimse")

        # when
        cached_skyrimse: Game = GameService.get_game_by_id("skyrimse")

        # then
        assert skyrimse is cached_skyrimse
