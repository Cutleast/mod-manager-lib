"""
Copyright (c) Cutleast
"""

from typing import ClassVar

from .apis import ModManagerApi
from .mod_manager import ModManager
from .modorganizer.api import ModOrganizer
from .vortex.api import Vortex


class ModManagerService:
    """
    Stateless service class for providing mod manager API instances.
    """

    APIS: dict[ModManagerApi, type[ModManager]] = {
        ModManagerApi.ModOrganizer: ModOrganizer,
        ModManagerApi.Vortex: Vortex,
    }
    """Dictionary mapping mod manager APIs to their corresponding mod manager classes."""

    __instances: ClassVar[dict[ModManagerApi, ModManager]] = {}

    @classmethod
    def get_mod_manager(cls, api: ModManagerApi) -> ModManager:
        """
        Get a mod manager instance for the given API.

        Args:
            api: The mod manager API to get an instance for.

        Returns:
            An instance of the mod manager for the given API.
        """

        if api not in cls.APIS:
            raise ValueError(f"Unsupported mod manager API: {api}")

        if api not in cls.__instances:
            cls.__instances[api] = cls.APIS[api]()

        return cls.__instances[api]
