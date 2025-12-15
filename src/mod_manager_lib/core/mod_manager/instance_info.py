"""
Copyright (c) Cutleast
"""

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, BeforeValidator, PlainSerializer

from ..game import Game
from ..game_service import GameService

if TYPE_CHECKING:
    from .mod_manager import ModManager


class InstanceInfo(BaseModel, metaclass=ABCMeta, frozen=True):
    """
    Base model for identifying an instance within a mod manager.
    """

    display_name: str
    """
    The display name of the instance.
    """

    game: Annotated[
        Game,
        PlainSerializer(lambda g: g.id),  # serialize only the id
        BeforeValidator(
            lambda v: GameService.get_game_by_id(v) if isinstance(v, str) else v
        ),
    ]
    """
    The primary game of this instance.
    """

    @abstractmethod
    def get_mod_manager(self) -> "ModManager":
        """
        Returns the mod manager that manages this instance.

        Returns:
            ModManager: The mod manager that manages this instance.
        """
