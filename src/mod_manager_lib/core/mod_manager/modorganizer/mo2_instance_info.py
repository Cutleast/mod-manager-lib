"""
Copyright (c) Cutleast
"""

from pathlib import Path
from typing import Annotated, Literal, override

from cutleast_core_lib.core.utilities.pydantic_utils import include_literal_defaults
from pydantic import Field

from ..instance_info import InstanceInfo
from ..mod_manager import ModManager


@include_literal_defaults
class MO2InstanceInfo(InstanceInfo, frozen=True):
    """
    Class for identifying an MO2 instance and profile.
    """

    profile: str
    """The selected profile of the instance."""

    is_global: bool
    """Whether the instance is a global or portable instance."""

    base_folder: Path
    """
    Path to the base directory of the instance.
    **The folder must contain the instance's ModOrganizer.ini file!**
    """

    mods_folder: Path
    """Path to the instance's "mods" folder."""

    profiles_folder: Path
    """Path to the instance's "profiles" folder."""

    install_mo2: Annotated[bool, Field(exclude=True)] = True
    """
    Whether to install Mod Organizer 2 to the instance (only relevant for portable
    destination instances) upon instance creation.
    """

    use_root_builder: Annotated[bool, Field(exclude=True)] = True
    """
    Whether the instance uses the Root Builder plugin instead of copying files to the
    game folder.
    """

    mod_manager: Literal[ModManager.ModOrganizer] = ModManager.ModOrganizer
    """Discriminator value for deserialization."""

    @override
    def get_mod_manager(self) -> ModManager:
        return self.mod_manager
