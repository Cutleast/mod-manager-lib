"""
Copyright (c) Cutleast
"""

import os
import re
import time
from collections.abc import Mapping
from copy import copy
from pathlib import Path
from typing import Any, Optional, TypeVar, final, override

from cutleast_core_lib.core.downloader import Downloader
from cutleast_core_lib.core.filesystem.archive import Archive
from cutleast_core_lib.core.multithreading.progress import (
    ProgressUpdate,
    UpdateCallback,
    update,
)
from cutleast_core_lib.core.utilities.env_resolver import resolve
from cutleast_core_lib.core.utilities.ini_file import IniData, IniFile, IniValue
from cutleast_core_lib.core.utilities.reverse_dict import reverse_dict
from cutleast_core_lib.core.utilities.typing_utils import checked_cast
from cutleast_core_lib.core.utilities.unique import unique

from mod_manager_lib.core.exceptions import GameNotFoundError
from mod_manager_lib.core.game import Game
from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.core.instance.instance import Instance
from mod_manager_lib.core.instance.metadata import Metadata
from mod_manager_lib.core.instance.mod import Mod
from mod_manager_lib.core.instance.tool import Tool
from mod_manager_lib.core.mod_manager.exceptions import InstanceNotFoundError
from mod_manager_lib.core.mod_manager.modorganizer.exceptions import (
    CannotInstallGlobalMo2Error,
    InvalidGlobalInstancePathError,
)
from mod_manager_lib.core.utilities.filesystem import clean_fs_string

from ..mod_manager import ModManager
from .instance_info import MO2InstanceInfo


MappingValueType = TypeVar("MappingValueType")


def _get_case_insensitive(
    mapping: Mapping[str, MappingValueType], key: str
) -> Optional[MappingValueType]:
    """Returns a mapping value without requiring an exact key case match."""

    folded_key: str = key.casefold()
    return next(
        (value for name, value in mapping.items() if name.casefold() == folded_key),
        None,
    )


def _get_case_insensitive_key(mapping: Mapping[str, object], key: str) -> Optional[str]:
    """Returns the existing spelling of a mapping key, if present."""

    folded_key: str = key.casefold()
    return next((name for name in mapping if name.casefold() == folded_key), None)


@final
class ModOrganizer(ModManager[MO2InstanceInfo]):
    """
    API class for Mod Organizer 2.
    """

    # TODO: Make this dynamic instead of a fixed url
    DOWNLOAD_URL: str = "https://github.com/ModOrganizer2/modorganizer/releases/download/v2.5.2/Mod.Organizer-2.5.2.7z"

    BYTE_ARRAY_PATTERN: re.Pattern[str] = re.compile(r"^@ByteArray\((.*)\)$")
    INI_ARG_PATTERN: re.Pattern[str] = re.compile(r'(?:[^ "]+|"[^"]+")+')
    INI_ARG_QUOTED_PATTERN: re.Pattern[str] = re.compile(r'^"?(([^"]|\\")+)"?$')
    INI_QUOTE_PATTERN: re.Pattern[str] = re.compile(r'^"([^"]+)"$')
    EXE_BLACKLIST: list[str] = ["Explorer++.exe"]
    """List of executable names to ignore when loading tools."""

    FILE_BLACKLIST: list[str] = ["meta.ini"]
    """List of filenames to ignore when processing mod conflicts."""

    MOD_SEPARATOR_SUFFIX: str = "_separator"
    """Suffix for the folder name of mod separators."""

    appdata_path: Path = resolve(Path("%LOCALAPPDATA%") / "ModOrganizer")

    GAME_SHORT_NAME_OVERRIDES: dict[str, str] = {
        "EnderalSpecialEdition": "EnderalSE",
    }
    """Dictionary of overrides for game short names."""

    @override
    def get_instance_names(self, game: Game) -> list[str]:
        self.log.info(f"Getting global MO2 instances for {game.id}...")

        instances: list[str] = []

        if self.appdata_path.is_dir():
            for instance_ini in self.appdata_path.glob("**/ModOrganizer.ini"):
                instance_data: IniData = IniFile.load(instance_ini)
                general: Optional[dict[str, IniValue]] = _get_case_insensitive(
                    instance_data, "General"
                )
                if general is None:
                    continue

                instance_game: str = str(
                    _get_case_insensitive(general, "gameName") or ""
                )
                if instance_game.lower() == game.display_name.lower():
                    instances.append(instance_ini.parent.name)

        self.log.info(f"Got {len(instances)} instances.")

        return sorted(instances)

    @override
    def load_instance(
        self,
        instance_data: MO2InstanceInfo,
        modname_limit: int = 255,
        file_blacklist: Optional[list[str]] = None,
        game_folder: Optional[Path] = None,
        load_conflicts: bool = True,
        update_callback: Optional[UpdateCallback] = None,
    ) -> Instance:
        instance_name: str = instance_data.display_name
        profile_name: str = instance_data.profile
        game: Game = instance_data.game

        if instance_data.is_global and instance_name not in self.get_instance_names(
            game
        ):
            raise InstanceNotFoundError(f"{instance_name} > {profile_name}")

        instance_path: Path = instance_data.base_folder
        mo2_ini_path: Path = instance_path / "ModOrganizer.ini"

        if not mo2_ini_path.is_file():
            raise InstanceNotFoundError(f"{instance_name} > {profile_name}")

        mo2_ini_data: IniData = IniFile.load(mo2_ini_path)
        general: dict[str, IniValue] = (
            _get_case_insensitive(mo2_ini_data, "General") or {}
        )
        raw_game_folder: IniValue = _get_case_insensitive(general, "gamePath")
        if isinstance(raw_game_folder, str):
            raw_game_folder = ModOrganizer.BYTE_ARRAY_PATTERN.sub(
                r"\1", raw_game_folder
            )
            raw_game_folder = raw_game_folder.replace("\\\\", "\\")
            game_folder = Path(raw_game_folder)
        elif game_folder is None:
            raise GameNotFoundError

        self.log.info(
            f"Loading profile '{profile_name}' from instance '{instance_name}' at "
            f"'{instance_path}'..."
        )
        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Loading mods from {0} > {1}...").format(
                    instance_name, profile_name
                )
            ),
        )

        mods: list[Mod] = self.load_mods(
            instance_data=instance_data,
            game_folder=game_folder,
            modname_limit=modname_limit,
            file_blacklist=file_blacklist,
            load_conflicts=load_conflicts,
            update_callback=update_callback,
        )

        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Loading tools from {0} > {1}...").format(
                    instance_name, profile_name
                )
            ),
        )

        tools: list[Tool] = self.load_tools(
            instance_data, mods, game_folder, file_blacklist, update_callback
        )

        widgets: dict[str, IniValue] = (
            _get_case_insensitive(mo2_ini_data, "Widgets") or {}
        )
        last_tool_index: IniValue = _get_case_insensitive(
            widgets, "MainWindow_executablesListBox_index"
        )
        last_tool: Optional[Tool] = None
        if isinstance(last_tool_index, int):
            try:
                last_tool = tools[
                    # -1 because of the first item "edit"
                    int(last_tool_index) - 1
                ]
            except IndexError:
                pass

        instance = Instance(
            display_name=f"{instance_name} > {profile_name}",
            game_folder=game_folder,
            mods=mods,
            tools=tools,
            last_tool=last_tool,
            order_matters=True,
        )

        self.log.info(
            f"Loaded {instance_name} > {profile_name} with {len(mods)} mod(s) and "
            f"{len(instance.tools)} tool(s)."
        )

        return instance

    @override
    def load_mods(
        self,
        instance_data: MO2InstanceInfo,
        game_folder: Path,
        modname_limit: int = 255,
        file_blacklist: Optional[list[str]] = None,
        load_conflicts: bool = True,
        update_callback: Optional[UpdateCallback] = None,
    ) -> list[Mod]:
        instance_name: str = instance_data.display_name
        profile_name: str = instance_data.profile

        if file_blacklist is None:
            file_blacklist = ModOrganizer.FILE_BLACKLIST
        else:
            file_blacklist = file_blacklist + ModOrganizer.FILE_BLACKLIST

        self.log.info(f"Loading mods from {instance_name} > {profile_name}...")
        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Loading mods from {0} > {1}...").format(
                    instance_name, profile_name
                )
            ),
        )

        mo2_ini_path: Path = instance_data.base_folder / "ModOrganizer.ini"
        mods_dir: Path = ModOrganizer.get_mods_folder(mo2_ini_path)
        prof_dir: Path = ModOrganizer.get_profiles_folder(mo2_ini_path)
        modlist_txt_path: Path = prof_dir / instance_data.profile / "modlist.txt"

        if not (mods_dir.is_dir() and prof_dir.is_dir() and modlist_txt_path.is_file()):
            raise InstanceNotFoundError(f"{instance_name} > {profile_name}")

        modnames: list[tuple[str, bool]] = self.parse_modlist_txt(modlist_txt_path)
        unmanaged_modnames: list[str] = [
            f.name
            for f in mods_dir.iterdir()
            if f.is_dir() and not any(f.name.lower() in m[0].lower() for m in modnames)
        ]
        if unmanaged_modnames:
            self.log.warning(f"Found {len(unmanaged_modnames)} unmanaged mod(s):")
            for modname in unmanaged_modnames:
                self.log.warning(f" - {modname}")
        modnames += [(m, False) for m in unmanaged_modnames]
        mods: list[Mod] = []
        missing_metadata_count: int = 0
        start_time: float = time.perf_counter()

        for m, (modname, enabled) in enumerate(modnames):
            update(
                update_callback,
                ProgressUpdate(
                    status_text=self.tr("Loading mods from {0} > {1}: {2}...").format(
                        instance_name, profile_name, modname
                    ),
                    value=m,
                    maximum=len(modnames),
                ),
            )
            self.log.debug(f"Loading mod '{modname}'...")

            mod_path: Path = mods_dir / modname
            mod_meta_path: Path = mod_path / "meta.ini"
            metadata: Metadata
            if mod_meta_path.is_file():
                metadata = self.parse_meta_ini(mod_meta_path, instance_data.game)
            else:
                metadata = Metadata(
                    mod_id=None, file_id=None, version="", file_name="", game_id=""
                )
                missing_metadata_count += 1
                self.log.debug(f"No metadata available for '{modname}'.")

            deploy_path: Optional[Path] = None
            if (mod_path / "Root").is_dir():
                deploy_path = Path(".")
                mod_path /= "Root"

                self.log.debug(f"Detected mod using Root Builder plugin: {modname}")

            mod = Mod(
                display_name=modname.removesuffix(ModOrganizer.MOD_SEPARATOR_SUFFIX),
                path=mod_path,
                deploy_path=deploy_path,
                metadata=metadata,
                installed=True,
                enabled=enabled,
                mod_type=(
                    Mod.Type.Separator
                    if modname.endswith(ModOrganizer.MOD_SEPARATOR_SUFFIX)
                    else Mod.Type.Regular
                ),
            )
            mods.append(mod)

        ModOrganizer.__assign_variants(mods)

        # Load overwrite folder as mod
        overwrite_folder: Path = ModOrganizer.get_overwrite_folder(mo2_ini_path)
        if overwrite_folder.is_dir() and os.listdir(overwrite_folder):
            overwrite_mod = Mod(
                display_name="Overwrite",
                path=overwrite_folder,
                deploy_path=None,
                metadata=Metadata(
                    mod_id=None, file_id=None, version="", file_name=None, game_id=""
                ),
                installed=True,
                enabled=True,
                mod_type=Mod.Type.Overwrite,
            )
            mods.append(overwrite_mod)

        if load_conflicts:
            update(
                update_callback,
                ProgressUpdate(
                    status_text=self.tr("Processing mod conflicts..."), maximum=0
                ),
            )

            self.__process_conflicts(mods, file_blacklist, update_callback)

        enabled_mod_count: int = sum(mod.enabled for mod in mods)
        duration: float = time.perf_counter() - start_time
        self.log.info(
            f"Loaded {len(mods)} mod(s) ({enabled_mod_count} enabled) from "
            f"{instance_name} > {profile_name} in {duration:.2f}s."
        )
        if missing_metadata_count:
            self.log.warning(
                f"{missing_metadata_count} loaded mod(s) have no metadata."
            )

        return mods

    @staticmethod
    def __assign_variants(mods: list[Mod]) -> None:
        """Assigns stable variants to mods sharing an installation archive."""

        mods_by_archive: dict[str, list[Mod]] = {}
        for mod in mods:
            if mod.metadata.file_name:
                mods_by_archive.setdefault(
                    mod.metadata.file_name.casefold(), []
                ).append(mod)

        for matching_mods in mods_by_archive.values():
            if len(matching_mods) < 2:
                continue

            base_mod: Mod = min(matching_mods, key=lambda mod: len(mod.display_name))
            used_variants: set[str] = set()
            for index, mod in enumerate(matching_mods, start=1):
                if mod is base_mod:
                    continue

                if mod.display_name.casefold().startswith(
                    base_mod.display_name.casefold()
                ):
                    variant: str = mod.display_name[len(base_mod.display_name) :].strip(
                        "-_. "
                    )
                else:
                    variant = mod.display_name.strip("-_. ")

                variant = clean_fs_string(variant) or f"variant-{index}"
                unique_variant: str = variant
                suffix: int = 2
                while unique_variant.casefold() in used_variants:
                    unique_variant = f"{variant}-{suffix}"
                    suffix += 1

                mod.variant = unique_variant
                used_variants.add(unique_variant.casefold())

    def parse_meta_ini(self, meta_ini_path: Path, default_game: Game) -> Metadata:
        """
        Parses the meta.ini file of a mod.

        Args:
            meta_ini_path (Path): Path to the meta.ini file.
            default_game (Game): The default game if the meta.ini does not specify one.

        Returns:
            Metadata: Parsed metadata.
        """

        short_name_overrides: dict[str, str] = reverse_dict(
            ModOrganizer.GAME_SHORT_NAME_OVERRIDES
        )

        meta_ini_data: IniData = IniFile.load(meta_ini_path)
        general: Optional[dict[str, IniValue]] = meta_ini_data.get("General")
        mod_id: Optional[int] = None
        file_id: Optional[int] = None
        version: str = ""
        game_id: str = default_game.nexus_id
        install_file: Optional[str] = None
        if general is not None:
            try:
                mod_id = int(general.get("modid") or 0) or None
                version = str(general.get("version") or "")
                if general.get("installationFile"):
                    install_file = Path(str(general["installationFile"])).name

                while version.endswith(".0") and version.count(".") > 1:
                    version = version.removesuffix(".0")

                try:
                    game_name = str(general["gameName"])
                    game_id = GameService.get_game_by_short_name(
                        short_name_overrides.get(game_name, game_name)
                    ).nexus_id
                except KeyError:
                    self.log.debug(
                        f"No game specified for '{meta_ini_path.parent.name}'. Falling "
                        "back to instance's default..."
                    )
                except ValueError:
                    self.log.warning(
                        f"Unknown game for mod '{meta_ini_path.parent.name}': {general.get('gameName')}"
                    )

                if "installedFiles" in meta_ini_data:
                    file_id = (
                        int(meta_ini_data["installedFiles"].get("1\\fileid") or 0)
                        or None
                    )
            except Exception as ex:  # noqa: BLE001
                self.log.error(
                    f"Failed to parse meta.ini in '{meta_ini_path.parent}': {ex}"
                )
        else:
            self.log.warning(f"Incomplete meta.ini in '{meta_ini_path.parent}'!")

        return Metadata(
            mod_id=mod_id,
            file_id=file_id,
            version=version,
            file_name=install_file,
            game_id=game_id,
        )

    @staticmethod
    def parse_modlist_txt(modlist_txt_path: Path) -> list[tuple[str, bool]]:
        """
        Parses the modlist.txt of a profile.

        Args:
            modlist_txt_path (Path): Path to the modlist.txt file.

        Returns:
            list[tuple[str, bool]]: List of mod names and their activation state.
        """

        with open(modlist_txt_path, "r", encoding="utf8") as modlist_file:
            lines: list[str] = modlist_file.readlines()

        mods: list[tuple[str, bool]] = [
            (line[1:].removesuffix("\n"), line.startswith("+"))
            for line in reversed(lines)
            if line.strip() and line[0] in ("+", "-")
        ]

        return mods

    @staticmethod
    def dump_modlist_txt(modlist_txt_path: Path, mods: list[Mod]) -> None:
        """
        Dumps the modlist.txt of a profile.

        Args:
            modlist_txt_path (Path): Path to the modlist.txt file.
            mods (list[Mod]): List of mods that are installed in the mod instance.
        """

        lines: list[str] = unique(
            [
                (
                    ("+" if mod.enabled and mod.mod_type != Mod.Type.Separator else "-")
                    + clean_fs_string(mod.display_name)
                    + (
                        ModOrganizer.MOD_SEPARATOR_SUFFIX
                        if mod.mod_type == Mod.Type.Separator
                        else ""
                    )
                    + "\n"
                )
                for mod in reversed(mods)
                if mod.mod_type != Mod.Type.Overwrite
            ],
            key=lambda line: line.lower(),  # ensure that there are no duplicates
        )
        with open(modlist_txt_path, "w", encoding="utf8") as modlist_file:
            modlist_file.writelines(lines)

    def __process_conflicts(
        self,
        mods: list[Mod],
        file_blacklist: list[str],
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        file_index: dict[str, list[Mod]] = ModOrganizer.index_modlist(
            mods, file_blacklist
        )
        self.log.debug(f"Modlist has {len(file_index)} file(s) in {len(mods)} mod(s).")

        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Processing mod conflicts..."), maximum=0
            ),
        )

        for mod_list in file_index.values():
            for m, mod in enumerate(mod_list):
                mod.mod_conflicts.extend(mod_list[m + 1 :])

        # Remove duplicate conflicts
        for mod in mods:
            mod.mod_conflicts = unique(mod.mod_conflicts)

        # Process single file conflicts (.mohidden files)
        update(
            update_callback,
            ProgressUpdate(status_text=self.tr("Processing single file conflicts...")),
        )

        hidden_files: dict[str, list[Mod]] = {
            f: m
            for f, m in file_index.items()
            if f.endswith(".mohidden") and f.removesuffix(".mohidden") in file_index
        }
        self.log.debug(f"Found {len(hidden_files)} hidden file(s) with conflicts.")

        for hidden_file, mod_list in hidden_files.items():
            real_file: str = hidden_file.removesuffix(".mohidden")
            overwriting_mod: Mod = file_index[real_file][-1]
            for mod in mod_list:
                mod.file_conflicts[real_file] = overwriting_mod

    @override
    def load_tools(
        self,
        instance_data: MO2InstanceInfo,
        mods: list[Mod],
        game_folder: Path,
        file_blacklist: Optional[list[str]] = None,
        update_callback: Optional[UpdateCallback] = None,
    ) -> list[Tool]:
        instance_name: str = instance_data.display_name
        profile_name: str = instance_data.profile
        mods_by_folders: dict[Path, Mod] = {m.path: m for m in mods}

        self.log.info(f"Loading tools from {instance_name} > {profile_name}...")

        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Loading tools from {0} > {1}...").format(
                    instance_name, profile_name
                )
            ),
        )

        mo2_ini_path: Path = instance_data.base_folder / "ModOrganizer.ini"

        tools: list[Tool] = self.get_custom_executables(mo2_ini_path)
        for tool in tools:
            if tool.working_dir == game_folder:
                tool.working_dir = None

            mod: Optional[Mod] = ModOrganizer.get_mod_for_path(
                tool.executable, mods_by_folders
            )
            if mod is not None:
                tool.executable = tool.executable.relative_to(mod.path)
                tool.mod = mod
            elif tool.executable.is_relative_to(game_folder):
                tool.executable = tool.executable.relative_to(game_folder)
                tool.is_in_game_dir = True

        self.log.info(
            f"Loaded {len(tools)} tool(s) from {instance_name} > {profile_name}."
        )

        return tools

    def get_custom_executables(self, mo2_ini_path: Path) -> list[Tool]:
        """
        Parses the specified ModOrganizer.ini file and extracts all custom executables.
        This method does not map them to their mods nor the game folder.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file.

        Returns:
            list[Tool]: List of executables as-is.
        """

        mo2_ini_data: IniData = IniFile.load(mo2_ini_path)
        custom_executables: dict[str, IniValue] = (
            _get_case_insensitive(mo2_ini_data, "customExecutables") or {}
        )
        custom_executables_size: IniValue = (
            _get_case_insensitive(custom_executables, "size") or 0
        )
        if not isinstance(custom_executables_size, int):
            return []

        tools: list[Tool] = []
        for i in range(1, custom_executables_size + 1):
            try:
                exe_path = Path(
                    checked_cast(
                        str,
                        _get_case_insensitive(custom_executables, f"{i}\\binary"),
                    )
                )
                raw_args: str = checked_cast(
                    str,
                    _get_case_insensitive(custom_executables, f"{i}\\arguments") or "",
                )
                name: str = checked_cast(
                    str,
                    _get_case_insensitive(custom_executables, f"{i}\\title"),
                )
                raw_working_dir: Optional[IniValue] = custom_executables[
                    _get_case_insensitive_key(
                        custom_executables, f"{i}\\workingDirectory"
                    )
                    or f"{i}\\workingDirectory"
                ]
            except Exception as ex:
                self.log.error(f"Failed to load tool with index {i}: {ex}", exc_info=ex)
                continue

            if exe_path.name in ModOrganizer.EXE_BLACKLIST:
                self.log.debug(
                    f"Skipped tool '{exe_path.name}' due to mod manager blacklist."
                )
                continue

            working_dir: Optional[Path] = (
                Path(raw_working_dir) if isinstance(raw_working_dir, str) else None
            )

            tool = Tool(
                display_name=name,
                mod=None,
                executable=exe_path,
                commandline_args=ModOrganizer.process_ini_arguments(raw_args),
                working_dir=working_dir,
                is_in_game_dir=False,
            )
            tools.append(tool)

        return tools

    @staticmethod
    def process_ini_arguments(raw_args: str) -> list[str]:
        r"""
        Processes a raw string of commandline arguments for an executable by splitting
        it into a list of separate arguments.

        Examples:
            `-D:\"C:\Games\Nolvus Ascension\STOCK GAME\Data\" -c:\"C:\Games\Nolvus Ascension\TOOLS\SSE Edit\Cache\"`

            => `[r'-D:"C:\Games\Nolvus Ascension\STOCK GAME\Data"', r'-c:"C:\Games\Nolvus Ascension\TOOLS\SSE Edit\Cache\"']`

        Args:
            raw_args (str): Raw string of commandline arguments.

        Returns:
            list[str]: List of commandline arguments.
        """

        if raw_args.startswith('"') and raw_args.endswith('"'):
            raw_args = ModOrganizer.INI_ARG_QUOTED_PATTERN.sub(r"\1", raw_args)
        raw_args = raw_args.replace('\\"', '"').replace("\\\\", "\\")

        raw_matches: list[str] = ModOrganizer.INI_ARG_PATTERN.findall(raw_args)
        args: list[str] = [
            ModOrganizer.INI_QUOTE_PATTERN.sub(r"\1", arg) for arg in raw_matches
        ]
        return args

    @override
    @classmethod
    def get_actual_files(cls, mod: Mod) -> dict[Path, Path]:
        return {
            Path(file): Path(file).with_suffix(file.suffix.removesuffix(".mohidden"))
            for file in mod.files
            if file.suffix.endswith(".mohidden")
            and str(file).lower().removesuffix(".mohidden") in mod.file_conflicts
        }

    @override
    def create_instance(
        self,
        instance_data: MO2InstanceInfo,
        game_folder: Path,
        update_callback: Optional[UpdateCallback] = None,
    ) -> Instance:
        self.log.info(f"Creating instance '{instance_data.display_name}'...")

        mo2_ini_path: Path = instance_data.base_folder / "ModOrganizer.ini"
        game: Game = instance_data.game

        if instance_data.is_global:
            if not mo2_ini_path.is_relative_to(self.appdata_path):
                raise InvalidGlobalInstancePathError

            if instance_data.install_mo2:
                raise CannotInstallGlobalMo2Error

        mods_dir: str
        if instance_data.mods_folder.is_relative_to(instance_data.base_folder):
            mods_dir = "%BASE_DIR%/" + str(
                instance_data.mods_folder.relative_to(instance_data.base_folder)
            ).replace("\\", "/")
        else:
            mods_dir = str(instance_data.mods_folder).replace("\\", "/")

        prof_dir: str
        if instance_data.profiles_folder.is_relative_to(instance_data.base_folder):
            prof_dir = "%BASE_DIR%/" + str(
                instance_data.profiles_folder.relative_to(instance_data.base_folder)
            ).replace("\\", "/")
        else:
            prof_dir = str(instance_data.profiles_folder).replace("\\", "/")

        mo2_ini_path.parent.mkdir(parents=True, exist_ok=True)
        mo2_ini_data: IniData = {
            "General": {
                "gameName": game.display_name,
                "selected_profile": "@ByteArray(Default)",
                "gamePath": str(game_folder).replace("\\", "/"),
                "first_start": True,
            },
            "Settings": {
                "base_directory": str(instance_data.base_folder).replace("\\", "/"),
                "download_directory": "%BASE_DIR%/downloads",  # TODO: Make this configurable
                "mod_directory": mods_dir,
                "profiles_directory": prof_dir,
                "overwrite_directory": "%BASE_DIR%/overwrite",
                "language": "en",
                "style": "Paper Dark.qss",
            },
        }
        IniFile.save(mo2_ini_path, mo2_ini_data)

        instance_data.mods_folder.mkdir(parents=True, exist_ok=True)
        instance_data.profiles_folder.mkdir(parents=True, exist_ok=True)
        os.makedirs(
            instance_data.profiles_folder / instance_data.profile, exist_ok=True
        )
        os.makedirs(instance_data.base_folder / "downloads", exist_ok=True)
        os.makedirs(instance_data.base_folder / "overwrite", exist_ok=True)
        (instance_data.profiles_folder / instance_data.profile / "modlist.txt").touch()

        if instance_data.install_mo2:
            self.__download_and_install_mo2(instance_data.base_folder, update_callback)

        self.log.info("Instance created successfully.")

        return Instance(
            display_name=instance_data.display_name,
            game_folder=game_folder,
            mods=[],
            tools=[],
            order_matters=True,
        )

    def __download_and_install_mo2(
        self, dest: Path, update_callback: Optional[UpdateCallback] = None
    ) -> None:
        self.log.info(f"Downloading and installing ModOrganizer to '{dest}'...")

        update(
            update_callback,
            ProgressUpdate(
                status_text=self.tr("Downloading and installing ModOrganizer...")
            ),
        )

        downloaded_archive: Path = self.__download_mo2(dest, update_callback)
        self.__install_mo2(downloaded_archive, dest, update_callback)

        downloaded_archive.unlink()
        self.log.debug(f"Deleted downloaded '{downloaded_archive}'.")

        self.log.info("ModOrganizer downloaded and installed successfully.")

    def __download_mo2(
        self, dest: Path, update_callback: Optional[UpdateCallback] = None
    ) -> Path:
        self.log.info("Downloading ModOrganizer...")

        return Downloader().download(
            download_url=ModOrganizer.DOWNLOAD_URL,
            dest_folder=dest,
            progress_callback=update_callback,
        )

    def __install_mo2(
        self,
        downloaded_archive: Path,
        dest: Path,
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        self.log.info("Installing ModOrganizer...")

        update(
            update_callback,
            ProgressUpdate(status_text=self.tr("Extracting archive..."), maximum=0),
        )

        archive = Archive(downloaded_archive)
        archive.extract_all(dest, full_paths=True)

    @override
    def install_mod(
        self,
        mod: Mod,
        instance: Instance,
        instance_data: MO2InstanceInfo,
        file_redirects: dict[Path, Path],
        use_hardlinks: bool,
        replace: bool,
        blacklist: Optional[list[str]] = None,
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        self.log.info(f"Installing mod '{mod.display_name}'...")

        game: Game
        try:
            game = GameService.get_game_by_nexus_id(mod.metadata.game_id)
        except ValueError:
            self.log.warning(
                f"Unsupported game '{mod.metadata.game_id}' for mod! Falling back to "
                "instance's default..."
            )
            game = instance_data.game

        mod_folder: Path
        regular_deployment: bool = True

        if mod.mod_type in [Mod.Type.Regular, Mod.Type.Separator]:
            mod_name: str = mod.display_name
            if mod.mod_type == Mod.Type.Separator:
                mod_name += ModOrganizer.MOD_SEPARATOR_SUFFIX
            mod_folder = instance_data.mods_folder / clean_fs_string(mod_name)
            meta_ini_path: Path = mod_folder / "meta.ini"
            if mod.deploy_path is not None and mod.deploy_path == Path("."):
                if instance_data.use_root_builder:
                    mod_folder /= "Root"
                else:
                    mod_folder = instance.game_folder
                    regular_deployment = False
            elif mod.deploy_path is not None:
                mod_folder /= mod.deploy_path

            self.log.debug(f"Deploy path: {mod.deploy_path}")
            self.log.debug(f"Mod folder: {mod_folder}")

            if mod_folder.is_dir() and regular_deployment:
                self.log.warning(
                    f"Mod '{mod.display_name}' already exists! Merging files..."
                )
            mod_folder.mkdir(parents=True, exist_ok=True)

            # Create and write metadata to meta.ini
            # if the mod doesn't already have one
            if regular_deployment and Path("meta.ini") not in mod.files:
                ModOrganizer.write_meta_ini_file(meta_ini_path, mod.metadata, game)
            elif regular_deployment and Path("meta.ini") in mod.files:
                meta_ini_path.write_bytes((mod.path / "meta.ini").read_bytes())
                self.log.info("Copied original meta.ini from mod.")

        # Process overwrite folder
        elif mod.mod_type == Mod.Type.Overwrite:
            mo2_ini_path: Path = instance_data.base_folder / "ModOrganizer.ini"
            mod_folder = ModOrganizer.get_overwrite_folder(mo2_ini_path)

        else:
            self.log.error(f"Unknown mod type: {mod.mod_type}")
            return

        self.install_mod_files(
            mod=mod,
            mod_folder=mod_folder,
            file_redirects=file_redirects,
            use_hardlinks=use_hardlinks,
            replace=replace,
            blacklist=blacklist,
            update_callback=update_callback,
        )

        # Append .mohidden suffix to files in mod.file_conflicts
        for file in mod.file_conflicts:
            src: Path = mod_folder / file
            dst: Path = src.with_suffix(src.suffix + ".mohidden")
            os.rename(src, dst)
            self.log.debug(
                f"Renamed '{file}' to '{dst}' due to configured file conflict."
            )

        # Merge conflicts with already installed mods
        if instance.is_mod_installed(mod):
            existing_mod: Mod = instance.get_installed_mod(mod)
            existing_mod.mod_conflicts = unique(
                existing_mod.mod_conflicts + mod.mod_conflicts
            )
            existing_mod.file_conflicts.update(mod.file_conflicts)

        elif regular_deployment:
            new_mod: Mod = Mod.create_copy(mod)
            new_mod.path = mod_folder
            instance.mods.append(new_mod)

    @staticmethod
    def write_meta_ini_file(
        meta_ini_path: Path, metadata: Metadata, game: Game
    ) -> None:
        """
        Writes metadata to a meta.ini file.

        Args:
            meta_ini_path (Path): Path to the meta.ini file.
            metadata (Metadata): Mod metadata.
            game (Game): Game.
        """

        meta_ini_data: IniData = {
            "General": {
                "gameName": ModOrganizer.GAME_SHORT_NAME_OVERRIDES.get(
                    game.short_name, game.short_name
                ),
                "modid": metadata.mod_id,
                "version": ModOrganizer.__format_version(metadata.version),
                "installationFile": metadata.file_name,
            },
            "installedFiles": {
                "1\\modid": metadata.mod_id,
                "size": "1",
                "1\\fileid": metadata.file_id,
            },
        }
        IniFile.save(meta_ini_path, meta_ini_data)

    @staticmethod
    def __format_version(version: str) -> str:
        """Pads a non-empty MO2 version to at least four segments."""

        if not version:
            return version

        segments: list[str] = version.split(".")
        segments.extend("0" for _ in range(4 - len(segments)))
        return ".".join(segments)

    @override
    def add_tool(
        self,
        tool: Tool,
        instance: Instance,
        instance_data: MO2InstanceInfo,
        use_hardlinks: bool,
        replace: bool,
        blacklist: Optional[list[str]] = None,
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        if tool in instance.tools:
            return

        self.log.info(f"Adding tool '{tool.display_name}'...")

        mo2_ini_path: Path = instance_data.base_folder / "ModOrganizer.ini"
        mo2_ini_data: IniData = IniFile.load(mo2_ini_path)
        section_key: Optional[str] = _get_case_insensitive_key(
            mo2_ini_data, "customExecutables"
        )
        if section_key is None:
            section_key = "customExecutables"
            mo2_ini_data[section_key] = {"size": 0}
        custom_executables: dict[str, IniValue] = mo2_ini_data[section_key]

        size_key: str = _get_case_insensitive_key(custom_executables, "size") or "size"
        new_index = int(custom_executables.get(size_key) or 0) + 1

        new_tool: Tool = copy(tool)
        if new_tool.mod is not None and instance.is_mod_installed(new_tool.mod):
            # Map tool to the installed mod
            new_tool.mod = instance.get_installed_mod(new_tool.mod)

        custom_executables.update(
            ModOrganizer.tool_to_ini_data(new_tool, new_index, instance.game_folder)
        )
        custom_executables[size_key] = new_index

        IniFile.save(mo2_ini_path, mo2_ini_data)

        instance.tools.append(new_tool)

    @staticmethod
    def tool_to_ini_data(tool: Tool, index: int, game_folder: Path) -> dict[str, Any]:
        """
        Creates an INI data section for the specified tool to be written to an
        instance's ModOrganizer.ini file.

        Args:
            tool (Tool): Tool to add to the instance
            index (int): New index for the tool
            game_folder (Path): Path to the game folder

        Returns:
            dict[str, Any]: INI data
        """

        return {
            f"{index}\\arguments": ModOrganizer.prepare_ini_arguments(
                tool.commandline_args
            ),
            f"{index}\\binary": str(tool.get_full_executable_path(game_folder)).replace(
                "\\", "/"
            ),
            f"{index}\\hide": False,
            f"{index}\\ownicon": False,
            f"{index}\\steamAppID": None,
            f"{index}\\title": tool.display_name,
            f"{index}\\toolbar": False,
            f"{index}\\workingDirectory": str(tool.working_dir or ""),
        }

    @staticmethod
    def prepare_ini_arguments(args: list[str]) -> str:
        """
        Prepares a list of arguments for writing to a ModOrganizer.ini file.

        Args:
            args (list[str]): List of arguments

        Returns:
            str: Concatenated and escaped list of arguments
        """

        return repr(" ".join(args))[1:-1]

    @override
    def get_instance_ini_dir(self, instance_data: MO2InstanceInfo) -> Path:
        return instance_data.profiles_folder / instance_data.profile

    @override
    def get_additional_files_folder(self, instance_data: MO2InstanceInfo) -> Path:
        return instance_data.profiles_folder / instance_data.profile

    @override
    def finalize_instance(
        self,
        instance: Instance,
        instance_data: MO2InstanceInfo,
        activate_instance: bool,
    ) -> None:
        modlist_txt_path: Path = (
            instance_data.profiles_folder / instance_data.profile / "modlist.txt"
        )
        self.dump_modlist_txt(modlist_txt_path, instance.get_loadorder())
        self.log.debug(f"Dumped modlist to '{modlist_txt_path}'.")

        settings_ini_path: Path = (
            instance_data.profiles_folder / instance_data.profile / "settings.ini"
        )
        settings_ini_data: IniData = {
            "General": {
                "LocalSaves": str(instance.separate_save_games).lower(),
                "LocalSettings": str(instance.separate_ini_files).lower(),
            }
        }
        IniFile.save(settings_ini_path, settings_ini_data)
        self.log.debug(f"Dumped settings to '{settings_ini_path}'.")

    @staticmethod
    def get_mods_folder(mo2_ini_path: Path) -> Path:
        """
        Gets the path to the mods folder of the specified MO2 instance.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file of the instance.

        Returns:
            Path: Path to the mods folder.
        """

        ini_data: IniData = IniFile.load(mo2_ini_path)
        settings: Optional[dict[str, IniValue]] = _get_case_insensitive(
            ini_data, "Settings"
        )
        if settings is None:
            raise KeyError("Settings")
        raw_base_dir: IniValue = _get_case_insensitive(settings, "base_directory")
        base_dir: Path = (
            Path(checked_cast(str, raw_base_dir))
            if raw_base_dir is not None
            else mo2_ini_path.parent
        )

        mods_dir: Path
        raw_mods_dir: IniValue = _get_case_insensitive(settings, "mod_directory")
        if raw_mods_dir is not None:
            mods_dir = resolve(
                Path(checked_cast(str, raw_mods_dir)), base_dir=str(base_dir)
            )
        else:
            mods_dir = base_dir / "mods"

        return mods_dir

    @staticmethod
    def get_profiles_folder(mo2_ini_path: Path) -> Path:
        """
        Gets the path to the profiles folder of the specified MO2 instance.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file of the instance.

        Returns:
            Path: Path to the profiles folder.
        """

        ini_data: IniData = IniFile.load(mo2_ini_path)
        settings: Optional[dict[str, IniValue]] = _get_case_insensitive(
            ini_data, "Settings"
        )
        if settings is None:
            raise KeyError("Settings")
        raw_base_dir: IniValue = _get_case_insensitive(settings, "base_directory")
        base_dir: Path = (
            Path(checked_cast(str, raw_base_dir))
            if raw_base_dir is not None
            else mo2_ini_path.parent
        )

        prof_dir: Path
        raw_profiles_dir: IniValue = _get_case_insensitive(
            settings, "profiles_directory"
        )
        if raw_profiles_dir is not None:
            prof_dir = resolve(
                Path(checked_cast(str, raw_profiles_dir)),
                base_dir=str(base_dir),
            )
        else:
            prof_dir = base_dir / "profiles"

        return prof_dir

    @staticmethod
    def get_overwrite_folder(mo2_ini_path: Path) -> Path:
        """
        Gets the path to the overwrite folder of the specified MO2 instance.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file of the instance.

        Returns:
            Path: Path to the overwrite folder.
        """

        ini_data: IniData = IniFile.load(mo2_ini_path)
        settings: Optional[dict[str, IniValue]] = _get_case_insensitive(
            ini_data, "Settings"
        )
        if settings is None:
            raise KeyError("Settings")
        raw_base_dir: IniValue = _get_case_insensitive(settings, "base_directory")
        base_dir: Path = (
            Path(checked_cast(str, raw_base_dir))
            if raw_base_dir is not None
            else mo2_ini_path.parent
        )

        overwrite_dir: Path
        raw_overwrite_dir: IniValue = _get_case_insensitive(
            settings, "overwrite_directory"
        )
        if raw_overwrite_dir is not None:
            overwrite_dir = resolve(
                Path(checked_cast(str, raw_overwrite_dir)),
                base_dir=str(base_dir),
            )
        else:
            overwrite_dir = base_dir / "overwrite"

        return overwrite_dir

    @staticmethod
    def get_profile_names(mo2_ini_path: Path) -> list[str]:
        """
        Gets the names of all profiles in the specified MO2 instance.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file of the instance.

        Returns:
            list[str]: List of profile names.
        """

        ini_data: IniData = IniFile.load(mo2_ini_path)
        settings: Optional[dict[str, IniValue]] = _get_case_insensitive(
            ini_data, "Settings"
        )
        if settings is None:
            raise KeyError("Settings")
        raw_base_dir: IniValue = _get_case_insensitive(settings, "base_directory")
        base_dir: Path = (
            Path(checked_cast(str, raw_base_dir))
            if raw_base_dir is not None
            else mo2_ini_path.parent
        )

        prof_dir: Path
        raw_profiles_dir: IniValue = _get_case_insensitive(
            settings, "profiles_directory"
        )
        if raw_profiles_dir is not None:
            prof_dir = resolve(
                Path(checked_cast(str, raw_profiles_dir)),
                base_dir=str(base_dir),
            )
        else:
            prof_dir = base_dir / "profiles"

        return sorted([prof.name for prof in prof_dir.iterdir() if prof.is_dir()])

    @staticmethod
    def get_last_active_profile(mo2_ini_path: Path) -> Optional[str]:
        """
        Gets the name of the last active profile in the specified MO2 instance.

        Args:
            mo2_ini_path (Path): Path to the ModOrganizer.ini file of the instance.

        Returns:
            Optional[str]: Name of the last active profile.
        """

        ini_data: IniData = IniFile.load(mo2_ini_path)
        general: Optional[dict[str, IniValue]] = _get_case_insensitive(
            ini_data, "General"
        )
        if general is None:
            raise KeyError("General")

        profile_name: Optional[IniValue] = _get_case_insensitive(
            general, "selected_profile"
        )
        if profile_name is None:
            return

        if not isinstance(profile_name, str):
            return

        return ModOrganizer.BYTE_ARRAY_PATTERN.sub(r"\1", profile_name)

    def detect_global_instances(self) -> bool:
        r"""
        Checks for global instances at AppData\Local\ModOrganizer.

        Returns:
            bool: Whether there are global MO2 instances.
        """

        self.log.info("Checking for global instances...")

        instances_found: bool = False

        global_instance_path: Path = resolve(Path("%LOCALAPPDATA%")) / "ModOrganizer"
        if global_instance_path.is_dir():
            instances_found = (
                len(list(global_instance_path.glob("*/ModOrganizer.ini"))) > 0
            )

        self.log.info(f"Global instances found: {instances_found}")

        return instances_found

    @override
    def get_mods_path(self, instance_data: MO2InstanceInfo) -> Path:
        return instance_data.mods_folder

    @override
    def is_instance_existing(self, instance_data: MO2InstanceInfo) -> bool:
        instance_name: str = instance_data.display_name
        profile_name: str = instance_data.profile
        game: Game = instance_data.game

        if instance_data.is_global and instance_name in self.get_instance_names(game):
            return True

        instance_path: Path = instance_data.base_folder
        mo2_ini_path: Path = instance_path / "ModOrganizer.ini"
        if mo2_ini_path.is_file():
            profile_path: Path = (
                ModOrganizer.get_profiles_folder(mo2_ini_path) / profile_name
            )
            return profile_path.is_dir()

        return False
