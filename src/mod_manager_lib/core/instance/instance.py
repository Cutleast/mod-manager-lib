"""
Copyright (c) Cutleast
"""

import heapq
from pathlib import Path
from typing import Optional

from cutleast_core_lib.core.utilities.filter import get_first_match
from pydantic import BaseModel

from .mod import Mod
from .tool import Tool


class Instance(BaseModel):
    """
    Model representing an entire modinstance.
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
            lambda m: m == mod
            or (
                (
                    (m.display_name == mod.display_name and m.metadata == mod.metadata)
                    or (
                        m.metadata.mod_id == mod.metadata.mod_id
                        and m.metadata.file_id == mod.metadata.file_id
                        and bool(m.metadata.mod_id)
                        and bool(m.metadata.file_id)
                    )
                )
                and m.mod_type == mod.mod_type
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

        When order does not matter (e.g. Vortex instances), the mods are sorted
        topologically according to their `mod_conflicts` (overwrite rules) using
        Kahn's BFS algorithm with a min-heap for stable alphabetical tie-breaking.
        This correctly handles arbitrarily long dependency chains (A→B→C) and
        cycles (remaining mods after cycle detection are appended alphabetically).

        Args:
            order_matters (Optional[bool], optional):
                Whether the mods have a fixed order. Defaults to the instance's default.

        Returns:
            list[Mod]: The sorted list of mods, lowest priority first.
                       ``mod.mod_conflicts`` edges point from lower-priority mods to
                       higher-priority mods (i.e. if A.mod_conflicts = [B], B must
                       come *after* A in the returned list).
        """

        if order_matters is None:
            order_matters = self.order_matters

        if order_matters:
            return self.mods.copy()

        # --- Topological sort (Kahn's algorithm) ---
        # Stable base: alphabetical.  The sorted index doubles as heap priority so
        # that alphabetically earlier mods are always preferred when multiple mods
        # become available at the same time.
        sorted_mods: list[Mod] = sorted(self.mods, key=lambda m: m.display_name)
        n = len(sorted_mods)
        if n == 0:
            return []

        # Map object identity → index in sorted_mods for O(1) lookup.
        # All Mod objects in mod_conflicts are guaranteed to be the same objects
        # that live in self.mods (they are populated directly from the same list),
        # so id()-based lookup is safe.
        id_to_idx: dict[int, int] = {id(m): i for i, m in enumerate(sorted_mods)}

        # Build directed graph: edge src→dst means src must precede dst.
        adjacency: list[list[int]] = [[] for _ in range(n)]
        in_degree: list[int] = [0] * n
        seen_edges: set[tuple[int, int]] = set()

        for mod in self.mods:
            src_idx = id_to_idx.get(id(mod))
            if src_idx is None:
                continue
            for conflict_mod in mod.mod_conflicts:
                dst_idx = id_to_idx.get(id(conflict_mod))
                if dst_idx is None or dst_idx == src_idx:
                    # conflict_mod not in this instance, or self-reference – skip
                    continue
                edge = (src_idx, dst_idx)
                if edge not in seen_edges:
                    seen_edges.add(edge)
                    adjacency[src_idx].append(dst_idx)
                    in_degree[dst_idx] += 1

        # Initialise the min-heap with all roots (in_degree == 0).
        # Because sorted_mods is alphabetically sorted, lower indices are
        # alphabetically earlier – the heap therefore gives stable alpha order.
        heap: list[int] = [i for i in range(n) if in_degree[i] == 0]
        heapq.heapify(heap)

        result: list[Mod] = []
        while heap:
            i = heapq.heappop(heap)
            result.append(sorted_mods[i])
            for j in adjacency[i]:
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    heapq.heappush(heap, j)

        # If the graph contained a cycle, the remaining mods will still have
        # in_degree > 0.  Append them in alphabetical order so the result is
        # always complete.
        if len(result) < n:
            included_ids: set[int] = {id(m) for m in result}
            result.extend(m for m in sorted_mods if id(m) not in included_ids)

        return result

    @property
    def size(self) -> int:
        """
        The total size of all mods in this instance.
        """

        return sum(mod.size for mod in self.mods)
