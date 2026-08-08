"""
Copyright (c) Cutleast
"""

from pathlib import Path

import pytest
from base_test import BaseTest
from cutleast_core_lib.core.utilities.ini_file import IniData, IniFile, IniValue
from cutleast_core_lib.test.utils import Utils
from mod_manager_lib.core.game import Game
from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.core.instance.instance import Instance
from mod_manager_lib.core.instance.metadata import Metadata
from mod_manager_lib.core.instance.mod import Mod
from mod_manager_lib.core.instance.tool import Tool
from mod_manager_lib.core.mod_manager.modorganizer.api import ModOrganizer
from mod_manager_lib.core.mod_manager.modorganizer.instance_info import (
    MO2InstanceInfo,
)
from pyfakefs.fake_filesystem import FakeFilesystem


class TestModOrganizer(BaseTest):
    """
    Tests `core.mod_manager.modorganizer.api.ModOrganizer`.
    """

    PARSE_META_INI_DATA: list[tuple[Path, Metadata]] = [
        (
            Path("Test Mods_separator") / "meta.ini",
            Metadata(
                mod_id=None,
                file_id=None,
                version="",
                file_name=None,
                game_id="skyrimspecialedition",
            ),
        ),
        (
            Path("RS Children Overhaul") / "meta.ini",
            Metadata(
                mod_id=2650,
                file_id=128013,
                version="1.1.3",
                file_name="RSSE Children Overhaul 1.1.3 with hotfix 1-2650-1-1-3HF1-1583835543.7z",
                game_id="enderalspecialedition",  # to test mods from different games
            ),
        ),
    ]

    @pytest.mark.parametrize("meta_ini_path, expected_metadata", PARSE_META_INI_DATA)
    def test_parse_meta_ini(
        self, meta_ini_path: Path, expected_metadata: Metadata, data_folder: Path
    ) -> None:
        """
        Tests `ModOrganizer.parse_meta_ini()`.
        """

        # given
        mo2 = ModOrganizer()
        test_meta_ini_path: Path = data_folder / "mod_instance" / "mods" / meta_ini_path

        # when
        metadata: Metadata = mo2.parse_meta_ini(
            meta_ini_path=test_meta_ini_path,
            default_game=GameService.get_game_by_id("skyrimse"),
        )

        # then
        assert metadata == expected_metadata

    def test_load_instance(
        self, test_fs: FakeFilesystem, mo2_instance_info: MO2InstanceInfo
    ) -> None:
        """
        Tests `ModOrganizer.load_instance()`.
        """

        # given
        mo2 = ModOrganizer()

        # when
        instance: Instance = mo2.load_instance(mo2_instance_info)

        # then
        assert len(instance.mods) == 11
        assert len(instance.tools) == 3

        # when
        obsidian_weathers: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        obsidian_weathers_german: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # then
        assert obsidian_weathers.mod_conflicts == [obsidian_weathers_german]
        assert obsidian_weathers_german.mod_conflicts == []
        assert obsidian_weathers.file_conflicts == {}
        assert obsidian_weathers_german.file_conflicts == {}

        # when
        wet_and_cold: Mod = self.get_mod_by_name("Wet and Cold SE", instance)
        wet_and_cold_german: Mod = self.get_mod_by_name(
            "Wet and Cold SE - German", instance
        )

        # then
        assert (
            wet_and_cold_german.file_conflicts["scripts\\_wetskyuiconfig.pex"]
            == wet_and_cold
        )

        # when
        skse_loader: Tool = self.get_tool_by_name("SKSE", instance)
        dip: Tool = self.get_tool_by_name("DIP", instance)
        dip_mod: Mod = self.get_mod_by_name("Dynamic Interface Patcher - DIP", instance)

        # then
        assert skse_loader.executable == Path("skse64_loader.exe")
        assert skse_loader.mod is None
        assert skse_loader.commandline_args == []
        assert skse_loader.is_in_game_dir
        assert skse_loader.working_dir is None
        assert dip.executable == Path("DIP\\DIP.exe")
        assert dip.mod is dip_mod
        assert dip.commandline_args == []
        assert not dip.is_in_game_dir
        assert dip.working_dir is None

        # when
        overwrite_mod: Mod = instance.mods[-1]

        # then
        assert overwrite_mod.display_name == "Overwrite"
        assert overwrite_mod.mod_type == Mod.Type.Overwrite
        assert overwrite_mod.files == [Path("test.txt")]

    def test_modorganizer_ini_is_case_insensitive(
        self, test_fs: FakeFilesystem, mo2_instance_info: MO2InstanceInfo
    ) -> None:
        """
        Tests that `ModOrganizer.ini` sections and keys are case-insensitive.
        """

        # given
        mo2 = ModOrganizer()
        portable_ini_path: Path = mo2_instance_info.base_folder / "ModOrganizer.ini"
        global_ini_path: Path = mo2.appdata_path / "Test Instance" / "ModOrganizer.ini"
        for ini_path in [portable_ini_path, global_ini_path]:
            ini_data: IniData = IniFile.load(ini_path)
            lowercase_ini_data: IniData = {
                section.casefold(): {
                    key.casefold(): value for key, value in values.items()
                }
                for section, values in ini_data.items()
            }
            IniFile.save(ini_path, lowercase_ini_data)

        # when
        instance: Instance = mo2.load_instance(mo2_instance_info)
        new_tool = Tool(
            display_name="Case-insensitive tool",
            mod=None,
            executable=Path("C:/Tools/test.exe"),
            commandline_args=[],
            working_dir=None,
            is_in_game_dir=False,
        )
        mo2.add_tool(
            new_tool,
            instance,
            mo2_instance_info,
            use_hardlinks=False,
            replace=False,
        )

        # then
        assert instance.game_folder == Path("E:/SteamLibrary/Skyrim Special Edition")
        assert len(instance.tools) == 4
        assert mo2.get_instance_names(mo2_instance_info.game) == ["Test Instance"]
        assert mo2.get_mods_folder(portable_ini_path) == mo2_instance_info.mods_folder
        assert (
            mo2.get_profiles_folder(portable_ini_path)
            == mo2_instance_info.profiles_folder
        )
        assert mo2.get_overwrite_folder(portable_ini_path) == (
            mo2_instance_info.base_folder / "overwrite"
        )
        assert mo2.get_profile_names(portable_ini_path) == ["Default", "TestProfile"]
        assert mo2.get_last_active_profile(portable_ini_path) == "Default"

        updated_ini_data: IniData = IniFile.load(portable_ini_path)
        custom_executable_sections: list[str] = [
            section
            for section in updated_ini_data
            if section.casefold() == "customexecutables"
        ]
        assert custom_executable_sections == ["customexecutables"]
        custom_executables: dict[str, IniValue] = updated_ini_data[
            custom_executable_sections[0]
        ]
        assert custom_executables["size"] == 6
        assert custom_executables["6\\title"] == new_tool.display_name

    @staticmethod
    def process_conflicts_stub(mods: list[Mod], file_blacklist: list[str]) -> None:
        """
        Method stub for `ModOrganizer.__process_conflicts()`.
        """

        raise NotImplementedError

    @staticmethod
    def get_root_builder_path_stub(file: Path, mods_folder: Path) -> Path:
        """Stub for `ModOrganizer.__get_root_builder_path`."""

        raise NotImplementedError

    def test_process_conflicts(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        Tests `ModOrganizer.__process_conflicts()`.
        """

        # given
        mo2 = ModOrganizer()
        mods: list[Mod] = [
            TestModOrganizer.create_blank_mod("test_mod_1"),
            TestModOrganizer.create_blank_mod("test_mod_2"),
            TestModOrganizer.create_blank_mod("test_mod_3"),
            TestModOrganizer.create_blank_mod("test_mod_4"),
            TestModOrganizer.create_blank_mod("test_mod_5"),
        ]
        file_index: dict[str, list[Mod]] = {
            "test_file_1": [mods[0], mods[2], mods[4]],
            "test_file_2": [mods[0], mods[1]],
            "test_file_2.mohidden": [mods[2]],
            "test_file_3": [mods[4]],
        }

        for i in range(
            100_000, 500_000
        ):  # simulate a large mod list with lots of files
            file_index[f"test_file_{i}"] = [mods[i // 100_000]]

            # add some hidden files
            if i % 5 == 0:
                file_index[f"hidden_test_file_{i}.mohidden"] = [mods[i // 100_000]]

        # when
        monkeypatch.setattr(
            ModOrganizer, "index_modlist", lambda mods, file_blacklist: file_index
        )
        Utils.get_private_method(mo2, "process_conflicts", self.process_conflicts_stub)(
            mods, []
        )

        # then
        assert mods[0].mod_conflicts == [mods[2], mods[4], mods[1]]
        assert mods[1].mod_conflicts == []
        assert mods[2].mod_conflicts == [mods[4]]
        assert mods[3].mod_conflicts == []
        assert mods[4].mod_conflicts == []

        assert mods[2].file_conflicts["test_file_2"] == mods[1]

    def test_get_actual_files(self) -> None:
        """
        Tests `ModOrganizer.get_actual_files()`.
        """

        # given
        mo2 = ModOrganizer()
        mod1_files: list[Path] = [Path("Test_File_1"), Path("test_file_2")]
        mod1: Mod = self.create_blank_mod("test_mod_1", mod1_files)
        mod2_files: list[Path] = [
            Path("Test_File_2.mohidden"),
            Path("Test_File_3"),
            Path("test_file_4.mohidden"),
        ]
        mod2: Mod = self.create_blank_mod("test_mod_2", mod2_files)
        mod2.file_conflicts = {"test_file_2": mod1}

        # when
        mod1_file_redirects: dict[Path, Path] = mo2.get_actual_files(mod1)
        mod2_file_redirects: dict[Path, Path] = mo2.get_actual_files(mod2)

        # then
        assert mod1_file_redirects == {}
        assert mod2_file_redirects == {
            Path("test_file_2.mohidden"): Path("test_file_2")
        }

    def test_create_instance(self, test_fs: FakeFilesystem) -> None:
        """
        Tests `ModOrganizer.create_instance()`.
        """

        # given
        mo2 = ModOrganizer()
        game: Game = GameService.get_game_by_id("skyrimse")
        game_folder = Path("E:\\SteamLibrary\\Skyrim Special Edition")
        test_instance_path = Path("E:\\Modding\\Test Instance")
        instance_data = MO2InstanceInfo(
            display_name="Test Instance",
            game=game,
            profile="Default",
            is_global=False,
            base_folder=test_instance_path,
            mods_folder=test_instance_path / "mods",
            profiles_folder=test_instance_path / "profiles",
            install_mo2=False,
        )

        # when
        instance: Instance = mo2.create_instance(instance_data, game_folder)

        # then
        assert instance.mods == []
        assert instance.tools == []
        assert instance_data.base_folder.is_dir()
        assert instance_data.mods_folder.is_dir()
        assert instance_data.profiles_folder.is_dir()
        assert (instance_data.base_folder / "ModOrganizer.ini").is_file()
        assert (instance_data.profiles_folder / instance_data.profile).is_dir()
        assert (
            instance_data.profiles_folder / instance_data.profile / "modlist.txt"
        ).is_file()

        # when
        ini_data: IniData = IniFile.load(instance_data.base_folder / "ModOrganizer.ini")

        # then
        assert ini_data["General"]["gameName"] == game.display_name
        assert ini_data["General"]["gamePath"] == str(game_folder).replace("\\", "/")

    def test_install_mod(self, test_fs: FakeFilesystem, instance: Instance) -> None:
        """
        Tests `ModOrganizer.install_mod()`.
        """

        self.test_create_instance(test_fs)

        # given
        mo2 = ModOrganizer()
        test_instance_path = Path("E:\\Modding\\Test Instance")
        instance_data = MO2InstanceInfo(
            display_name="Test Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=test_instance_path,
            mods_folder=test_instance_path / "mods",
            profiles_folder=test_instance_path / "profiles",
            install_mo2=False,  # This is important for now as the download is not mocked, yet
        )
        dst_instance: Instance = mo2.load_instance(instance_data)
        overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", instance
        )
        overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", instance
        )

        # when
        for mod in [overwritten_mod, overwriting_mod]:
            mo2.install_mod(
                mod,
                dst_instance,
                instance_data,
                file_redirects=mo2.get_actual_files(mod),
                use_hardlinks=True,
                replace=True,
            )
        mo2.finalize_instance(dst_instance, instance_data, activate_instance=True)

        dst_instance = mo2.load_instance(instance_data)
        migrated_overwritten_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons", dst_instance
        )
        migrated_overwriting_mod: Mod = self.get_mod_by_name(
            "Obsidian Weathers and Seasons - German", dst_instance
        )

        # then
        assert migrated_overwritten_mod.metadata == overwritten_mod.metadata
        assert migrated_overwriting_mod.metadata == overwriting_mod.metadata
        assert migrated_overwritten_mod.mod_conflicts == [migrated_overwriting_mod]
        assert dst_instance.loadorder.index(
            migrated_overwritten_mod
        ) < dst_instance.loadorder.index(migrated_overwriting_mod)
        assert migrated_overwritten_mod.files == overwritten_mod.files
        assert migrated_overwriting_mod.files == overwriting_mod.files

    def test_install_root_builder_mod_splits_game_and_root_files(
        self, test_fs: FakeFilesystem
    ) -> None:
        """
        Tests Root Builder places Data files at the mod root and game files in Root.
        """

        # given
        mo2 = ModOrganizer()
        game = GameService.get_game_by_id("skyrimse")
        instance_path = Path("E:/Modding/Root Builder Test")
        instance_data = MO2InstanceInfo(
            display_name="Root Builder Test",
            game=game,
            profile="Default",
            is_global=False,
            base_folder=instance_path,
            mods_folder=instance_path / "mods",
            profiles_folder=instance_path / "profiles",
            install_mo2=False,
            use_root_builder=True,
        )
        instance: Instance = mo2.create_instance(
            instance_data, Path("E:/SteamLibrary/Skyrim Special Edition")
        )
        source_path = Path("C:/Source/Root Builder Mod")
        test_fs.create_file(source_path / "meta.ini", contents="[General]\n")
        test_fs.create_file(source_path / "skse64_loader.exe")
        test_fs.create_file(source_path / "Data" / "Scripts" / "a.pex")
        test_fs.create_file(source_path / "redirected" / "interface.swf")
        test_fs.create_file(source_path / "Data" / "Scripts" / "hidden.pex.mohidden")
        mod = Mod(
            display_name="Root Builder Mod",
            path=source_path,
            deploy_path=Path("."),
            metadata=Metadata.create_blank(),
            installed=True,
            enabled=True,
        )
        mod.file_conflicts[str(Path("Data/Scripts/hidden.pex")).lower()] = mod
        file_redirects: dict[Path, Path] = mo2.get_actual_files(mod)
        file_redirects[Path("redirected/interface.swf")] = Path(
            "Data/interface/interface.swf"
        )

        # when
        mo2.install_mod(
            mod,
            instance,
            instance_data,
            file_redirects=file_redirects,
            use_hardlinks=False,
            replace=True,
        )

        # then
        mod_folder: Path = instance_data.mods_folder / mod.display_name
        assert (mod_folder / "meta.ini").is_file()
        assert not (mod_folder / "Root" / "meta.ini").exists()
        assert (mod_folder / "Root" / "skse64_loader.exe").is_file()
        assert (mod_folder / "Scripts" / "a.pex").is_file()
        assert (mod_folder / "interface" / "interface.swf").is_file()
        assert (mod_folder / "Scripts" / "hidden.pex.mohidden").is_file()
        assert not (mod_folder / "Data").exists()
        assert not (mod_folder / "Root" / "Data").exists()

    def test_root_builder_treats_file_named_like_mods_folder_as_root_file(
        self,
    ) -> None:
        """Tests a file named `Data` is not redirected to the mod directory itself."""

        # given
        get_root_builder_path = Utils.get_private_method(
            ModOrganizer,
            "get_root_builder_path",
            self.get_root_builder_path_stub,
        )

        # when
        root_builder_path: Path = get_root_builder_path(Path("Data"), Path("data"))

        # then
        assert root_builder_path == Path("Root/Data")

    @pytest.mark.parametrize(
        ("version", "expected_version"),
        [
            ("", None),
            ("1", "1.0.0.0"),
            ("1.0", "1.0.0.0"),
            ("1.2.3", "1.2.3.0"),
            ("1.2.3.4", "1.2.3.4"),
            ("1.2.3.4.5", "1.2.3.4.5"),
            ("f1.07", "f1.07.0.0"),
        ],
    )
    def test_write_meta_ini_file_pads_version(
        self, tmp_path: Path, version: str, expected_version: IniValue
    ) -> None:
        """
        Tests that generated MO2 metadata contains at least four version segments.
        """

        # given
        meta_ini_path: Path = tmp_path / "meta.ini"
        metadata = Metadata(
            mod_id=1,
            file_id=2,
            version=version,
            file_name="test.7z",
            game_id="skyrimspecialedition",
        )

        # when
        ModOrganizer.write_meta_ini_file(
            meta_ini_path, metadata, GameService.get_game_by_id("skyrimse")
        )

        # then
        meta_ini_data: IniData = IniFile.load(meta_ini_path)
        assert meta_ini_data["General"]["version"] == expected_version

    def test_load_mods_assigns_variants_for_shared_archive(
        self, test_fs: FakeFilesystem, mo2_instance_info: MO2InstanceInfo
    ) -> None:
        """
        Tests that MO2 mods from the same archive receive distinct variants.
        """

        # given
        mo2 = ModOrganizer()
        archive_name = "Dear Diary Dark Mode-60837-1-1-1-1667594519.7z"
        mod_names: list[str] = [
            "Dear Diary Dark Mode",
            "Dear Diary Dark Mode - 21x9",
        ]
        metadata = Metadata(
            mod_id=60837,
            file_id=1,
            version="1.1.1",
            file_name=archive_name,
            game_id="skyrimspecialedition",
        )
        for mod_name in mod_names:
            mod_folder: Path = mo2_instance_info.mods_folder / mod_name
            mod_folder.mkdir()
            ModOrganizer.write_meta_ini_file(
                mod_folder / "meta.ini", metadata, mo2_instance_info.game
            )
            test_fs.create_file(mod_folder / "interface" / f"{mod_name}.txt")

        modlist_path: Path = (
            mo2_instance_info.profiles_folder
            / mo2_instance_info.profile
            / "modlist.txt"
        )
        modlist_path.write_text(
            modlist_path.read_text()
            + "\n"
            + "\n".join(f"+{name}" for name in mod_names)
        )

        # when
        mods: list[Mod] = mo2.load_mods(
            mo2_instance_info,
            Path("E:/SteamLibrary/Skyrim Special Edition"),
            load_conflicts=False,
        )

        # then
        base_mod: Mod = next(mod for mod in mods if mod.display_name == mod_names[0])
        variant_mod: Mod = next(mod for mod in mods if mod.display_name == mod_names[1])
        assert base_mod.metadata.file_name == archive_name
        assert variant_mod.metadata.file_name == archive_name
        assert base_mod.variant is None
        assert variant_mod.variant == "21x9"
        assert Mod.create_copy(variant_mod).variant == "21x9"

    def test_install_mod_with_separator(
        self, test_fs: FakeFilesystem, instance: Instance
    ) -> None:
        """
        Tests `ModOrganizer.install_mod()` with a separator mod.
        """

        self.test_create_instance(test_fs)

        # given
        mo2 = ModOrganizer()
        test_instance_path = Path("E:\\Modding\\Test Instance")
        instance_data = MO2InstanceInfo(
            display_name="Test Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=test_instance_path,
            mods_folder=test_instance_path / "mods",
            profiles_folder=test_instance_path / "profiles",
            install_mo2=False,  # This is important for now as the download is not mocked, yet
        )
        dst_instance: Instance = mo2.load_instance(instance_data)
        separator_mod: Mod = self.get_mod_by_name("Test Mods", instance)

        # when
        mo2.install_mod(
            separator_mod,
            dst_instance,
            instance_data,
            file_redirects=mo2.get_actual_files(separator_mod),
            use_hardlinks=True,
            replace=True,
        )
        mo2.finalize_instance(dst_instance, instance_data, activate_instance=True)

        dst_instance = mo2.load_instance(instance_data)
        migrated_separator_mod: Mod = self.get_mod_by_name("Test Mods", dst_instance)

        # then
        assert migrated_separator_mod.mod_type == Mod.Type.Separator
        assert dst_instance.loadorder[-1] is migrated_separator_mod

    def test_install_mod_with_overwrite(
        self, test_fs: FakeFilesystem, instance: Instance
    ) -> None:
        """
        Tests `ModOrganizer.install_mod()` with an overwrite mod.
        """

        self.test_create_instance(test_fs)

        # given
        mo2 = ModOrganizer()
        test_instance_path = Path("E:\\Modding\\Test Instance")
        instance_data = MO2InstanceInfo(
            display_name="Test Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=test_instance_path,
            mods_folder=test_instance_path / "mods",
            profiles_folder=test_instance_path / "profiles",
            install_mo2=False,  # This is important for now as the download is not mocked, yet
        )
        dst_instance: Instance = mo2.load_instance(instance_data)
        overwrite_mod: Mod = instance.mods[-1]

        # when
        mo2.install_mod(
            overwrite_mod,
            dst_instance,
            instance_data,
            file_redirects=mo2.get_actual_files(overwrite_mod),
            use_hardlinks=True,
            replace=True,
        )
        mo2.finalize_instance(dst_instance, instance_data, activate_instance=True)

        dst_instance = mo2.load_instance(instance_data)
        migrated_overwrite_mod: Mod = dst_instance.mods[-1]

        # then
        assert migrated_overwrite_mod.mod_type == Mod.Type.Overwrite
        assert Path("E:\\Modding\\Test Instance\\overwrite\\test.txt").is_file()
        assert (
            Path("E:\\Modding\\Test Instance\\overwrite\\test.txt").read_text()
            == "This file should make MMM to load the overwrite folder as extra mod."
        )
        assert (
            "+Overwrite"
            not in Path("E:\\Modding\\Test Instance\\profiles\\Default\\modlist.txt")
            .read_text()
            .splitlines()
        )

    PROCESS_INI_ARGS_DATA: list[tuple[str, list[str]]] = [
        (
            r"""-D:\"C:\\Games\\Nolvus Ascension\\STOCK GAME\\Data\" -c:\"C:\\Games\\Nolvus Ascension\\TOOLS\\SSE Edit\\Cache\\\"""",
            [
                '-D:"C:\\Games\\Nolvus Ascension\\STOCK GAME\\Data"',
                '-c:"C:\\Games\\Nolvus Ascension\\TOOLS\\SSE Edit\\Cache\\"',
            ],
        ),
        (
            r"""-DontCache -D:\"C:\\Games\\Nolvus Ascension\\STOCK GAME\\Data\"""",
            [
                "-DontCache",
                '-D:"C:\\Games\\Nolvus Ascension\\STOCK GAME\\Data"',
            ],
        ),
        (
            r"""\"C:\\Games\\Nolvus Ascension\\STOCK GAME\"""",
            [
                "C:\\Games\\Nolvus Ascension\\STOCK GAME",
            ],
        ),
        (
            r'"--game=\"Skyrim Special Edition\""',
            [
                '--game="Skyrim Special Edition"',
            ],
        ),
    ]

    @pytest.mark.parametrize("raw_args, expected_args", PROCESS_INI_ARGS_DATA)
    def test_process_ini_arguments(
        self, raw_args: str, expected_args: list[str]
    ) -> None:
        """
        Tests `ModOrganizer.process_ini_arguments()`.
        """

        # when
        actual_args: list[str] = ModOrganizer.process_ini_arguments(raw_args)

        # then
        assert actual_args == expected_args

    def test_is_instance_existing(
        self, test_fs: FakeFilesystem, mo2_instance_info: MO2InstanceInfo
    ) -> None:
        """
        Tests `ModOrganizer.is_instance_existing()`.
        """

        # given
        mo2 = ModOrganizer()

        # when/then
        assert mo2.is_instance_existing(mo2_instance_info)

        # when
        non_existing_instance_info = MO2InstanceInfo(
            display_name="Non Existing Instance",
            game=GameService.get_game_by_id("skyrimse"),
            profile="Default",
            is_global=False,
            base_folder=Path("E:\\Modding\\Non Existing Instance"),
            mods_folder=Path("E:\\Modding\\Non Existing Instance\\mods"),
            profiles_folder=Path("E:\\Modding\\Non Existing Instance\\profiles"),
        )

        # then
        assert not mo2.is_instance_existing(non_existing_instance_info)

        # when
        non_existing_profile = MO2InstanceInfo(
            display_name=mo2_instance_info.display_name,
            game=mo2_instance_info.game,
            profile="Non Existing Profile",
            is_global=mo2_instance_info.is_global,
            base_folder=mo2_instance_info.base_folder,
            mods_folder=mo2_instance_info.mods_folder,
            profiles_folder=mo2_instance_info.profiles_folder,
        )

        # then
        assert not mo2.is_instance_existing(non_existing_profile)

        # when
        wrong_game = MO2InstanceInfo(
            display_name=mo2_instance_info.display_name,
            game=GameService.get_game_by_id("skyrim"),
            profile=mo2_instance_info.profile,
            is_global=mo2_instance_info.is_global,
            base_folder=mo2_instance_info.base_folder,
            mods_folder=mo2_instance_info.mods_folder,
            profiles_folder=mo2_instance_info.profiles_folder,
        )

        # then
        assert mo2.is_instance_existing(wrong_game)
