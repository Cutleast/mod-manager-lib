"""
Copyright (c) Cutleast
"""

from heapq import heapify, heappop, heappush
from pathlib import Path
from typing import Optional

from cutleast_core_lib.core.utilities.filter import get_first_match
from pydantic import BaseModel

from ..exceptions import CyclicModConflictError
from .mod import Mod
from .tool import Tool


class Instance(BaseModel):
    """
    Model representing an entire mod instance.
    """

    display_name: str
    """
    The name that is visible to the user.
    """

    game_folder: Path
    """
    The path to the instance's game folder.
    """

    mods: list[Mod]
    """
    List of the instance's mods.
    """

    tools: list[Tool]
    """
    List of the instance's tools.
    """

    last_tool: Optional[Tool] = None
    """
    (Optional) last tool that was executed/selected in the instance.
    """

    order_matters: bool = False
    """
    Whether the mods have a fixed order that matters.
    """

    separate_ini_files: bool = True
    """
    Whether the instance has its own separate ini files.
    """

    separate_save_games: bool = True
    """
    Whether the instance has its own separate save games.
    """

    def is_mod_installed(self, mod: Mod) -> bool:
        """
        Checks if a mod is already installed in this instance.

        Args:
            mod (Mod): The mod to check.

        Returns:
            bool: `True` if the mod is installed, `False` otherwise
        """

        try:
            self.get_installed_mod(mod)
            return True
        except ValueError:
            return False

    def get_installed_mod(self, mod: Mod) -> Mod:
        """
        Returns a mod from the instance matching the specified mod.

        Args:
            mod (Mod): The mod to get.

        Raises:
            ValueError: If the mod is not installed or cannot be found

        Returns:
            Mod: The matching mod
        """

        return get_first_match(
            self.mods,
            lambda m: (
                m == mod
                or (
                    (
                        (
                            m.display_name == mod.display_name
                            and m.metadata == mod.metadata
                        )
                        or (
                            m.metadata.mod_id == mod.metadata.mod_id
                            and m.metadata.file_id == mod.metadata.file_id
                            and bool(m.metadata.mod_id)
                            and bool(m.metadata.file_id)
                        )
                    )
                    and m.mod_type == mod.mod_type
                )
            ),
        )

    @property
    def loadorder(self) -> list[Mod]:
        """
        List of mods sorted alphabetically and after their mod conflicts
        (overwritten mods before overwriting mods).
        """

        return self.get_loadorder()

    def get_loadorder(self, order_matters: Optional[bool] = None) -> list[Mod]:
        """
        Sorts the mods in this instance if `order_matters` is not `True`.

        Args:
            order_matters (Optional[bool], optional):
                Whether the mods have a fixed order. Defaults to the instance's default.

        Raises:
            CyclicModConflictError: If the mod conflict rules contain a cycle.

        Returns:
            list[Mod]: The sorted list of mods
        """

        if order_matters is None:
            order_matters = self.order_matters

        if order_matters:
            return self.mods.copy()

        mod_indices: dict[int, int] = {
            id(mod): index for index, mod in enumerate(self.mods)
        }
        resolved_conflicts: dict[int, Optional[int]] = {}
        successors: list[set[int]] = [set() for _ in self.mods]
        predecessors: list[set[int]] = [set() for _ in self.mods]

        for source_index, mod in enumerate(self.mods):
            for conflict in mod.mod_conflicts:
                conflict_id = id(conflict)
                if conflict_id not in resolved_conflicts:
                    target_index = mod_indices.get(conflict_id)
                    if target_index is None:
                        try:
                            installed_mod = self.get_installed_mod(conflict)
                            target_index = mod_indices[id(installed_mod)]
                        except ValueError:
                            target_index = None

                    resolved_conflicts[conflict_id] = target_index

                target_index = resolved_conflicts[conflict_id]
                if target_index is None or target_index in successors[source_index]:
                    continue

                successors[source_index].add(target_index)
                predecessors[target_index].add(source_index)

        indegrees: list[int] = [len(nodes) for nodes in predecessors]
        ready: list[tuple[str, int]] = [
            (mod.display_name, index)
            for index, mod in enumerate(self.mods)
            if indegrees[index] == 0
        ]
        heapify(ready)
        loadorder: list[Mod] = []

        while ready:
            _, source_index = heappop(ready)
            loadorder.append(self.mods[source_index])

            for target_index in successors[source_index]:
                indegrees[target_index] -= 1
                if indegrees[target_index] == 0:
                    target = self.mods[target_index]
                    heappush(ready, (target.display_name, target_index))

        if len(loadorder) != len(self.mods):
            cycle = self.__find_conflict_cycle(predecessors, indegrees)
            raise CyclicModConflictError(
                [self.mods[index].display_name for index in cycle]
            )

        return loadorder

    def __find_conflict_cycle(
        self, predecessors: list[set[int]], indegrees: list[int]
    ) -> list[int]:
        """
        Extracts a directed cycle from the nodes left by topological sorting.

        Args:
            predecessors (list[set[int]]): Predecessors for every mod index.
            indegrees (list[int]): Remaining indegrees after topological sorting.

        Returns:
            list[int]: Mod indices forming a cycle, including the repeated first index.
        """

        remaining: set[int] = {
            index for index, indegree in enumerate(indegrees) if indegree > 0
        }
        current = min(
            remaining, key=lambda index: (self.mods[index].display_name, index)
        )
        positions: dict[int, int] = {}
        reverse_path: list[int] = []

        while current not in positions:
            positions[current] = len(reverse_path)
            reverse_path.append(current)
            current = min(
                predecessors[current] & remaining,
                key=lambda index: (self.mods[index].display_name, index),
            )

        reverse_cycle = reverse_path[positions[current] :] + [current]
        return list(reversed(reverse_cycle))

    @property
    def size(self) -> int:
        """
        The total size of all mods in this instance.
        """

        return sum(mod.size for mod in self.mods)
