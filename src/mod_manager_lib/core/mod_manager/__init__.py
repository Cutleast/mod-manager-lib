"""
Copyright (c) Cutleast
"""

from .mod_manager_api import ModManagerApi
from .modorganizer.modorganizer import ModOrganizer
from .vortex.vortex import Vortex

MOD_MANAGERS: list[type[ModManagerApi]] = [
    Vortex,
    ModOrganizer,
]
"""
This list contains all available mod managers.
"""
