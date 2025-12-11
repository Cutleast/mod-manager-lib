"""
Copyright (c) Cutleast
"""

import logging
import os
import shutil
from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Optional, override

from cutleast_core_lib.core.multithreading.progress import (
    ProgressUpdate,
    UpdateCallback,
    update,
)
from cutleast_core_lib.core.utilities.logger import Logger
from cutleast_core_lib.core.utilities.scale import scale_value
from PySide6.QtCore import QObject

from ..game import Game
from ..instance.instance import Instance
from ..instance.mod import Mod
from ..instance.tool import Tool
from .instance_info import InstanceInfo


class ModManager[I: InstanceInfo](QObject, metaclass=ABCMeta):
    """
    Abstract class for mod managers.
    """

    log: logging.Logger

    def __init__(self) -> None:
        super().__init__()

        self.log = logging.getLogger(self.__repr__())

    @classmethod
    @abstractmethod
    def get_id(cls) -> str:
        """
        Returns:
            str: The internal id of the mod manager.
        """

    @classmethod
    @abstractmethod
    def get_display_name(cls) -> str:
        """
        Returns:
            str: The display name of the mod manager.
        """

    @classmethod
    @abstractmethod
    def get_icon_name(cls) -> str:
        """
        Returns:
            str: The name of the icon resource of the mod manager.
        """

    @override
    def __hash__(self) -> int:
        return hash(self.get_id())

    @abstractmethod
    def get_instance_names(self, game: Game) -> list[str]:
        """
        Loads and returns a list of the names of all mod instances that are managed
        by this mod manager.

        Args:
            game (Game): The selected game.

        Returns:
            list[str]: The names of all mod instances.
        """

    @abstractmethod
    def load_instance(
        self,
        instance_data: I,
        modname_limit: int = 255,
        file_blacklist: list[str] = [],
        game_folder: Optional[Path] = None,
        update_callback: Optional[UpdateCallback] = None,
    ) -> Instance:
        """
        Loads and returns the mod instance with the given name.

        Args:
            instance_data (I): The data of the mod instance.
            modname_limit (int, optional): A character limit for mod names. Defaults to 255.
            file_blacklist (list[str], optional): A list of files to ignore.
            game_folder (Optional[Path], optional): The game folder of the instance.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.

        Raises:
            InstanceNotFoundError: If the mod instance does not exist.
            GameNotFoundError:
                If the game folder of the instance could not be found and is not
                specified.

        Returns:
            Instance: The mod instance with the given name.
        """

    @abstractmethod
    def _load_mods(
        self,
        instance_data: I,
        game_folder: Path,
        modname_limit: int = 255,
        file_blacklist: list[str] = [],
        update_callback: Optional[UpdateCallback] = None,
    ) -> list[Mod]:
        """
        Loads and returns a list of mods for the given instance name.

        Args:
            instance_data (I): The data of the mod instance.
            game_folder (Path): The game folder of the instance.
            modname_limit (int, optional): A character limit for mod names. Defaults to 255.
            file_blacklist (list[str], optional): A list of files to ignore.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.

        Returns:
            list[Mod]: The list of mods.
        """

    @abstractmethod
    def _load_tools(
        self,
        instance_data: I,
        mods: list[Mod],
        game_folder: Path,
        file_blacklist: list[str] = [],
        update_callback: Optional[UpdateCallback] = None,
    ) -> list[Tool]:
        """
        Loads and returns a list of tools for the given instance.

        Args:
            instance_data (I): The data of the mod instance.
            mods (list[Mod]): The list of already loaded mods.
            game_folder (Path): The game folder of the instance.
            file_blacklist (list[str], optional): A list of files to ignore.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.

        Returns:
            list[Tool]: The list of tools.
        """

    @staticmethod
    def _get_mod_for_path(
        path: Path, mods_by_folders: dict[Path, Mod]
    ) -> Optional[Mod]:
        """
        Returns the mod that contains the given path.

        Args:
            path (Path): The path.
            mods_by_folders (dict[Path, Mod]): The dict of mods by folders.

        Returns:
            Optional[Mod]: The mod that contains the given path or None.
        """

        for mod_path, mod in mods_by_folders.items():
            if path.is_relative_to(mod_path):
                return mod

    @classmethod
    @Logger.timeit(logger_name="ModManager")
    def _index_modlist(
        cls, mods: list[Mod], file_blacklist: list[str]
    ) -> dict[str, list[Mod]]:
        """
        Indexes all mod files and maps each file to a list of mods that contain it.

        Args:
            mods (list[Mod]): The list of mods.
            file_blacklist (list[str], optional): A list of file paths to ignore.

        Returns:
            dict[str, list[Mod]]: The indexed list of mods.
        """

        indexed_mods: dict[str, list[Mod]] = {}
        for mod in mods:
            for file in filter(
                lambda f: f.name.lower() not in file_blacklist, mod.files
            ):
                indexed_mods.setdefault(str(file).lower(), []).append(mod)

        return indexed_mods

    @classmethod
    def _get_reversed_mod_conflicts(cls, mods: list[Mod]) -> dict[Mod, list[Mod]]:
        """
        Returns a dict of mods that overwrite other mods.

        Args:
            mods (list[Mod]): The list of mods.

        Returns:
            dict[Mod, list[Mod]]: The dict of mods that overwrite other mods.
        """

        mod_overrides: dict[Mod, list[Mod]] = {}

        for mod in mods:
            if mod.mod_conflicts:
                for overwriting_mod in mod.mod_conflicts:
                    mod_overrides.setdefault(overwriting_mod, []).append(mod)

        return mod_overrides

    @classmethod
    def get_actual_files(cls, mod: Mod) -> dict[Path, Path]:
        """
        Returns a dict of real file paths to actual file paths.
        Only contains files where the real path differs from the actual path.

        For example:
            `scripts\\_wetskyuiconfig.pex.mohidden` -> `scripts\\_wetskyuiconfig.pex`

        Args:
            mod (Mod): The mod.

        Returns:
            dict[Path, Path]: The dict of real file paths to actual file paths.
        """

        return {}

    def prepare_instance(self, instance_data: I) -> None:
        """
        Prepares a mod instance for modifications.

        Args:
            instance_data (I): The data of the instance.
        """

    @abstractmethod
    def create_instance(
        self,
        instance_data: I,
        game_folder: Path,
        update_callback: Optional[UpdateCallback] = None,
    ) -> Instance:
        """
        Creates an instance in this mod manager.

        Args:
            instance_data (Instance_data): The customized instance data to create.
            game_folder (Path): The game folder to use for the created instance.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.

        Raises:
            InstanceCreationError: If the instance could not be created.

        Returns:
            Instance: The created instance.
        """

    @abstractmethod
    def install_mod(
        self,
        mod: Mod,
        instance: Instance,
        instance_data: I,
        file_redirects: dict[Path, Path],
        use_hardlinks: bool,
        replace: bool,
        blacklist: list[str] = [],
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        """
        Installs a mod to the current instance.

        Args:
            mod (Mod): The mod to install.
            instance (Instance): The instance to install the mod to.
            instance_data (I): The data of the instance above.
            file_redirects (dict[Path, Path]): A dict of file redirects.
            use_hardlinks (bool): Whether to use hardlinks if possible.
            replace (bool): Whether to replace existing files.
            blacklist (list[str], optional): A list of files to not migrate.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.
        """

    @abstractmethod
    def add_tool(
        self,
        tool: Tool,
        instance: Instance,
        instance_data: I,
        use_hardlinks: bool,
        replace: bool,
        blacklist: list[str] = [],
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        """
        Adds a tool to the mod manager.

        Args:
            tool (Tool): The tool to add.
            instance (Instance): The instance to add the tool to.
            instance_data (I): The data of the instance above.
            use_hardlinks (bool): Whether to use hardlinks if possible.
            replace (bool): Whether to replace existing files.
            blacklist (list[str], optional): A list of files to not migrate.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.
        """

    def _install_mod_files(
        self,
        mod: Mod,
        mod_folder: Path,
        file_redirects: dict[Path, Path],
        use_hardlinks: bool,
        replace: bool,
        blacklist: list[str] = [],
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        """
        Installs the files of a mod to the destination path.

        Args:
            mod (Mod): The mod to install.
            mod_folder (Path): The destination path.
            use_hardlinks (bool): Whether to use hardlinks if possible.
            file_redirects (dict[Path, Path]): A dict of file redirects.
            replace (bool): Whether to replace existing files.
            blacklist (list[str], optional): A list of files to not migrate.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.
        """

        for f, file in enumerate(mod.files):
            if file.name.lower() in blacklist:
                self.log.info(
                    f"Skipped file due to configured blacklist: {file.name!r}"
                )
                continue

            src_path: Path = mod.path / file
            dst_path: Path = mod_folder / file_redirects.get(file, file)

            update(
                update_callback,
                ProgressUpdate(
                    status_text=f"{file.name} ({scale_value(src_path.stat().st_size)})",
                    value=f,
                    maximum=len(mod.files),
                ),
            )

            if src_path == dst_path:
                self.log.warning(f"Skipped file due to same path: {str(src_path)!r}")
                continue

            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if dst_path.is_file() and replace:
                dst_path.unlink()
                self.log.warning(f"Deleted existing file: {str(dst_path)!r}")
            elif not replace:
                self.log.info(f"Skipped existing file: {str(dst_path)!r}")
                continue

            if src_path.drive.lower() == dst_path.drive.lower() and use_hardlinks:
                os.link(src_path, dst_path)
            else:
                shutil.copyfile(src_path, dst_path)

    def get_ini_files(self, instance: Instance, instance_data: I) -> list[Path]:
        """
        Returns a list of INI files belonging to an instance.

        Args:
            instance (Instance): The instance.
            instance_data (I): The data of the instance.

        Returns:
            list[Path]: The list of INI files.
        """

        ini_filenames: list[Path] = instance_data.game.inifiles
        ini_dir: Path = self.get_ini_dir(instance_data, instance.separate_ini_files)

        return [(ini_dir / file) for file in ini_filenames]

    def get_ini_dir(self, instance_data: I, separate_ini_files: bool) -> Path:
        """
        Returns path to folder for INI files, either game's INI folder or
        instance's INI folder.

        Args:
            instance_data (I): The data of the instance.
            separate_ini_files (bool): Whether to use separate INI folders.

        Returns:
            Path: The path to the INI folder.
        """

        if separate_ini_files:
            return self.get_instance_ini_dir(instance_data)

        return instance_data.game.inidir

    @abstractmethod
    def get_instance_ini_dir(self, instance_data: I) -> Path:
        """
        Returns the path to the instance's INI folder.

        Args:
            instance_data (I): The data of the instance.

        Returns:
            Path: The path to the instance's INI folder.
        """

    def import_ini_files(
        self,
        files: list[Path],
        dst_instance_data: I,
        separate_ini_files: bool,
        use_hardlinks: bool,
        replace: bool,
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        """
        Imports the specified INI files to a desination instance.

        Args:
            files (list[Path]): The INI files to migrate.
            dst_instance_data (I): The data of the destination instance.
            separate_ini_files (bool): Whether to use separate INI folders.
            use_hardlinks (bool): Whether to use hardlinks if possible.
            replace (bool): Whether to replace existing files.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.
        """

        dest_folder: Path = self.get_ini_dir(dst_instance_data, separate_ini_files)

        for f, file in enumerate(files):
            dst_path: Path = dest_folder / file.name

            self.log.info(
                f"Migrating ini file {file.name!r} from "
                f"{str(file.parent)!r} to {str(dest_folder)!r}..."
            )
            update(
                update_callback,
                ProgressUpdate(
                    status_text=f"{file.name} ({scale_value(file.stat().st_size)})",
                    value=f,
                    maximum=len(files),
                ),
            )

            if not file.is_file():
                self.log.warning(f"Skipped not existing file: {str(file)!r}")
                continue

            dest_folder.mkdir(parents=True, exist_ok=True)

            if dst_path.is_file() and replace:
                dst_path.unlink()
                self.log.warning(f"Deleted existing file: {str(dst_path)!r}")
            elif not replace:
                self.log.info(f"Skipped existing file: {str(dst_path)!r}")
                continue

            if file.drive.lower() == dst_path.drive.lower() and use_hardlinks:
                os.link(file, dst_path)
            else:
                shutil.copyfile(file, dst_path)

    def get_additional_files(self, instance_data: I) -> list[Path]:
        """
        Returns a list of additional files to belonging to an instance.

        Args:
            instance_data (I): The data of the instance.

        Returns:
            list[Path]: The list of additional files.
        """

        file_names: list[str] = instance_data.game.additional_files
        add_folder: Path = self.get_additional_files_folder(instance_data)

        return [
            add_folder / file_name
            for file_name in file_names
            if (add_folder / file_name).is_file()
        ]

    def import_additional_files(
        self,
        files: list[Path],
        dst_instance_data: I,
        use_hardlinks: bool,
        replace: bool,
        update_callback: Optional[UpdateCallback] = None,
    ) -> None:
        """
        Imports the specified additional files to a destination instance.

        Args:
            files (list[Path]): The list of additional files.
            dst_instance_data (I): The data of the destination instance.
            use_hardlinks (bool): Whether to use hardlinks if possible.
            replace (bool): Whether to replace existing files.
            update_callback (Optional[UpdateCallback], optional):
                Optional update callback for progress updates. Defaults to None.
        """

        dest_folder: Path = self.get_additional_files_folder(dst_instance_data)

        for f, file in enumerate(files):
            dst_path: Path = dest_folder / file.name

            self.log.info(
                f"Migrating additional file {file.name!r} from "
                f"{str(file.parent)!r} to {str(dest_folder)!r}..."
            )
            update(
                update_callback,
                ProgressUpdate(
                    status_text=f"{file.name} ({scale_value(file.stat().st_size)})",
                    value=f,
                    maximum=len(files),
                ),
            )

            dest_folder.mkdir(parents=True, exist_ok=True)

            if dst_path.is_file() and replace:
                dst_path.unlink()
                self.log.warning(f"Deleted existing file: {str(dst_path)!r}")
            elif not replace:
                self.log.info(f"Skipped existing file: {str(dst_path)!r}")
                continue

            if file.drive.lower() == dst_path.drive.lower() and use_hardlinks:
                os.link(file, dst_path)
            else:
                shutil.copyfile(file, dst_path)

    @abstractmethod
    def get_additional_files_folder(self, instance_data: I) -> Path:
        """
        Gets the path for the additional files of the specified instance.

        Args:
            instance_data (I): The data of the instance.

        Returns:
            Path: The path for the additional files.
        """

    def finalize_instance(
        self, instance: Instance, instance_data: I, activate_instance: bool
    ) -> None:
        """
        Finalizes a mod instance.

        Args:
            instance (Instance): The mod instance to finalize.
            instance_data (I): The data of the mod instance to finalize.
            activate_instance (bool):
                Whether to activate the instance (if supported by the mod manager).
        """

    @abstractmethod
    def get_mods_path(self, instance_data: I) -> Path:
        """
        Returns the path to the specified instance's mods folder.

        Args:
            instance_data (I): The data of the instance.

        Returns:
            Path: The path to the mods folder.
        """

    @abstractmethod
    def is_instance_existing(self, instance_data: I) -> bool:
        """
        Checks if the specified instance exists.

        Args:
            instance_data (I): The data of the instance.

        Returns:
            bool: Whether the instance exists.
        """
