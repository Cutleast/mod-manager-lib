"""
Copyright (c) Cutleast
"""

import pytest

from base_test import BaseTest
from mod_manager_lib.core.exceptions import CyclicModConflictError
from mod_manager_lib.core.instance.instance import Instance
from mod_manager_lib.core.instance.mod import Mod


class TestInstance(BaseTest):
    """
    Tests `core.instance.instance.Instance`.
    """

    @staticmethod
    def __create_instance(*mods: Mod) -> Instance:
        return Instance(
            display_name="Test Instance",
            game_folder=mods[0].path.parent,
            mods=list(mods),
            tools=[],
        )

    def test_loadorder_simple(self, instance: Instance) -> None:
        """
        Tests `Instance.loadorder` on a simple conflict between two mods.
        """

        # given
        overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # then
        assert overwritten_mod.mod_conflicts == [overwriting_mod]

        # when
        loadorder: list[Mod] = instance.loadorder

        # then
        assert loadorder.index(overwritten_mod) < loadorder.index(overwriting_mod)

    def test_get_loadorder_without_order_matters(self, instance: Instance) -> None:
        """
        Tests `Instance.get_loadorder()` with `order_matters=False`.
        """

        # given
        overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # then
        assert overwritten_mod.mod_conflicts == [overwriting_mod]

        # when
        loadorder: list[Mod] = instance.get_loadorder(False)

        # then
        assert loadorder.index(overwritten_mod) < loadorder.index(overwriting_mod)

    def test_loadorder_unchanged(self, instance: Instance) -> None:
        """
        Tests `Instance.loadorder` with `order_matters=True`.
        """

        # given
        instance.order_matters = True
        overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # then
        assert overwritten_mod.mod_conflicts == [overwriting_mod]

        # when
        loadorder: list[Mod] = instance.loadorder

        # then
        assert loadorder.index(overwritten_mod) == instance.mods.index(overwritten_mod)
        assert loadorder.index(overwriting_mod) == instance.mods.index(overwriting_mod)

    def test_loadorder_empty(self, test_instance: Instance) -> None:
        """
        Tests `Instance.loadorder` with no mods.
        """

        # given
        test_instance.mods = []

        # when
        loadorder = test_instance.loadorder

        # then
        assert loadorder == []

    def test_get_loadorder_with_missing_mod(self, instance: Instance) -> None:
        """
        Tests `Instance.get_loadorder()` with a mod that is referenced by a mod conflict
        but missing in the instance.
        """

        # given
        instance.order_matters = True
        overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # then
        assert overwritten_mod.mod_conflicts == [overwriting_mod]

        # when
        instance.mods.remove(overwriting_mod)

        # then (mod conflict should be unaffected)
        assert overwritten_mod.mod_conflicts == [overwriting_mod]

        # when
        loadorder: list[Mod] = instance.get_loadorder(False)
        sorted_index: int = loadorder.index(overwritten_mod)
        original_index: int = (
            # subtract 1 for removed mod
            instance.mods.index(overwritten_mod) - 1
        )

        # then
        assert sorted_index == original_index

    def test_loadorder_multistage_chain(self) -> None:
        """
        Tests a transitive chain whose alphabetical order conflicts with its rules.
        """

        # given
        first = self.create_blank_mod("B")
        second = self.create_blank_mod("C")
        third = self.create_blank_mod("A")
        first.mod_conflicts = [second]
        second.mod_conflicts = [third]
        instance = self.__create_instance(third, second, first)
        original_order = instance.mods.copy()

        # when
        loadorder = instance.loadorder

        # then
        assert loadorder == [first, second, third]
        assert instance.mods == original_order

    def test_loadorder_branched_diamond(self) -> None:
        """
        Tests branched and diamond-shaped conflict rules.
        """

        # given
        first = self.create_blank_mod("D")
        left = self.create_blank_mod("B")
        right = self.create_blank_mod("C")
        last = self.create_blank_mod("A")
        first.mod_conflicts = [left, right]
        left.mod_conflicts = [last]
        right.mod_conflicts = [last]
        instance = self.__create_instance(last, right, left, first)

        # when
        loadorder = instance.loadorder

        # then
        assert loadorder == [first, left, right, last]

    def test_loadorder_resolves_copied_conflict_reference(self) -> None:
        """
        Tests equivalent conflict references that are not the installed mod object.
        """

        # given
        first = self.create_blank_mod("Z")
        second = self.create_blank_mod("A")
        first.mod_conflicts = [Mod.create_copy(second)]
        instance = self.__create_instance(second, first)

        # when
        loadorder = instance.loadorder

        # then
        assert loadorder == [first, second]

    def test_loadorder_ignores_missing_and_duplicate_conflicts(self) -> None:
        """
        Tests that missing references are ignored and duplicate edges are collapsed.
        """

        # given
        first = self.create_blank_mod("Z")
        second = self.create_blank_mod("A")
        missing = self.create_blank_mod("Missing")
        first.mod_conflicts = [second, second, missing]
        instance = self.__create_instance(second, first)

        # when
        loadorder = instance.loadorder

        # then
        assert loadorder == [first, second]

    def test_loadorder_rejects_self_cycle(self) -> None:
        """
        Tests that a direct self-reference is reported as a cycle.
        """

        # given
        mod = self.create_blank_mod("Self-referencing Mod")
        mod.mod_conflicts = [mod]
        instance = self.__create_instance(mod)

        # when
        with pytest.raises(CyclicModConflictError) as exc_info:
            instance.get_loadorder()

        # then
        message = str(exc_info.value)
        assert "Self-referencing Mod → Self-referencing Mod" in message
        assert "Vortex" in message

    def test_loadorder_rejects_multistage_cycle(self) -> None:
        """
        Tests that every mod in a multi-stage cycle is named in the error.
        """

        # given
        first = self.create_blank_mod("A")
        second = self.create_blank_mod("B")
        third = self.create_blank_mod("C")
        first.mod_conflicts = [second]
        second.mod_conflicts = [third]
        third.mod_conflicts = [first]
        instance = self.__create_instance(first, second, third)

        # when
        with pytest.raises(CyclicModConflictError) as exc_info:
            instance.get_loadorder()

        # then
        message = str(exc_info.value)
        assert "A → B → C → A" in message
        assert "Vortex" in message

    def test_loadorder_sorts_independent_mods_stably(self) -> None:
        """
        Tests case-sensitive alphabetical ordering and input stability for equal names.
        """

        # given
        lower = self.create_blank_mod("a")
        equal_first = self.create_blank_mod("Same")
        upper = self.create_blank_mod("A")
        equal_second = self.create_blank_mod("Same")
        instance = self.__create_instance(lower, equal_first, upper, equal_second)

        # when
        loadorder = instance.loadorder

        # then
        assert loadorder[0] is upper
        assert loadorder[1] is equal_first
        assert loadorder[2] is equal_second
        assert loadorder[3] is lower
