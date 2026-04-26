"""
Copyright (c) Cutleast
"""

from enum import StrEnum

from PySide6.QtGui import QIcon


class ModManagerApi(StrEnum):
    """Enum for available mod manager APIs."""

    ModOrganizer = "Mod Organizer 2"
    """Mod Organizer 2."""

    Vortex = "Vortex"
    """Vortex."""

    def get_icon(self) -> QIcon:
        """
        Returns:
            The icon for this mod manager API.
        """

        ICONS: dict[ModManagerApi, str] = {
            ModManagerApi.ModOrganizer: ":/icons/mo2.png",
            ModManagerApi.Vortex: ":/icons/vortex.png",
        }

        return QIcon(ICONS[self])
