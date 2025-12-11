"""
Copyright (c) Cutleast
"""

from ..instance_info import InstanceInfo


class ProfileInfo(InstanceInfo, frozen=True):
    """
    Class for identifying a Vortex profile.
    """

    id: str
    """
    The ID of the profile.
    """
