"""
Copyright (c) Cutleast
"""

from cutleast_core_lib.core.cache.function_cache import FunctionCache
from cutleast_core_lib.core.utilities.singleton import Singleton
from pydantic import TypeAdapter

from .game import Game

GameData = TypeAdapter(list[Game])


class GameService(Singleton):
    """
    Singleton service for managing game specifications.
    """

    __games: list[Game]

    def __init__(self, game_json_data: str) -> None:
        """
        Args:
            game_json_data (str): JSON string containing game specifications.
        """

        super().__init__()

        self.__games = GameData.validate_json(game_json_data)

    @classmethod
    @FunctionCache.cache
    def get_supported_games(cls) -> list[Game]:
        """
        Gets a list of supported games from the JSON resource.

        Returns:
            list[Game]: List of supported games
        """

        return cls.get().__games

    @classmethod
    @FunctionCache.cache
    def get_game_by_id(cls, game_id: str) -> Game:
        """
        Gets a game by its id. This method works case-insensitive.

        Args:
            game_id (str): Game id

        Raises:
            ValueError: when the game could not be found

        Returns:
            Game: Game with specified id
        """

        games: dict[str, Game] = {
            game.id.lower(): game for game in cls.get_supported_games()
        }

        if game_id.lower() in games:
            return games[game_id.lower()]

        raise ValueError(f"Game '{game_id}' not found!")

    @classmethod
    @FunctionCache.cache
    def get_game_by_short_name(cls, short_name: str) -> Game:
        """
        Gets a game by its short name. This method works case-insensitive.

        Args:
            short_name (str): Game short name

        Raises:
            ValueError: when the game could not be found

        Returns:
            Game: Game with specified short name
        """

        games: dict[str, Game] = {
            game.short_name.lower(): game for game in cls.get_supported_games()
        }

        if short_name.lower() in games:
            return games[short_name.lower()]

        raise ValueError(f"Game '{short_name}' not found!")

    @classmethod
    @FunctionCache.cache
    def get_game_by_nexus_id(cls, nexus_id: str) -> Game:
        """
        Gets a game by its nexus id.

        Args:
            nexus_id (str): Game nexus id

        Raises:
            ValueError: when the game could not be found

        Returns:
            Game: Game with specified nexus id
        """

        games: dict[str, Game] = {
            game.nexus_id: game for game in reversed(cls.get_supported_games())
        }

        if nexus_id in games:
            return games[nexus_id]

        raise ValueError(f"Game '{nexus_id}' not found!")
