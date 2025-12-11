"""
Copyright (c) Cutleast
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, override

from cutleast_core_lib.core.utilities.env_resolver import resolve
from pydantic import AfterValidator, BaseModel, Field

from .utilities.filesystem import get_documents_folder


class Game(BaseModel, frozen=True):
    """
    Base class for general game specifications.
    """

    id: str
    """
    Game identifier, should match the one used by Vortex (eg. "skyrimse").
    """

    display_name: str
    """
    Display name of the game (eg. "Skyrim Special Edition").
    """

    short_name: str
    """
    Short name of the game (eg. "SkyrimSE").
    """

    nexus_id: str
    """
    Name of the game's nexus page (eg. "skyrimspecialedition").
    """

    inidir: Annotated[
        Path,
        AfterValidator(lambda p: resolve(p, documents=str(get_documents_folder()))),
    ]
    """
    Path to the game's ini directory.
    Variables like `%%DOCUMENTS%%` are automatically resolved.
    """

    inifiles: Annotated[
        list[Path],
        AfterValidator(
            lambda f: [resolve(f, documents=str(get_documents_folder())) for f in f]
        ),
    ]
    """
    Paths to the game's ini files, relative to `inidir`.
    Variables like `%%DOCUMENTS%%` are automatically resolved.
    """

    mods_folder: Path
    """
    The game's default folder for mods, relative to its install directory.
    """

    additional_files: list[str] = Field(default_factory=list)
    """
    List of additional files to include in the migration.
    These filenames are relative to the respective mod manager's profiles folder.
    """

    @override
    def __hash__(self) -> int:
        return hash((self.id, self.display_name, self.short_name, self.nexus_id))
