"""
Copyright (c) Cutleast
"""

from abc import ABCMeta

from pydantic import BaseModel

from ..game import Game


class InstanceInfo(BaseModel, metaclass=ABCMeta, frozen=True):
    """
    Base model for identifying an instance within a mod manager.
    """

    display_name: str
    """
    The display name of the instance.
    """

    game: Game
    """
    The primary game of this instance.
    """
