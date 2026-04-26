"""
Copyright (c) Cutleast
"""

from typing import Literal, override

from cutleast_core_lib.core.utilities.pydantic_utils import include_literal_defaults

from ..apis import ModManagerApi
from ..instance_info import InstanceInfo


@include_literal_defaults
class ProfileInfo(InstanceInfo, frozen=True):
    """
    Class for identifying a Vortex profile.
    """

    id: str
    """The ID of the profile."""

    mod_manager: Literal[ModManagerApi.Vortex] = ModManagerApi.Vortex
    """Discriminator value for deserialization."""

    @override
    def get_mod_manager(self) -> ModManagerApi:
        return self.mod_manager
