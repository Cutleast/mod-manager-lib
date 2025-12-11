# mod-manager-lib

A core library primarily used by [SSE Auto Translator](https://github.com/Cutleast/SSE-Auto-Translator) and [Mod Manager Migrator](https://github.com/Cutleast/Mod-Manager-Migrator) for interfacing with mod managers like Mod Organizer 2 and Vortex.
It provides core classes and services to represent and handle game specifications, mod instances, mods, and tools.

## Installation

### As Git Submodule

1. Add this repository as a [git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) to `<project root>/mod-manager-lib` with this command:
    `git submodule add -b master https://github.com/Cutleast/mod-manager-lib.git mod-manager-lib`.
2. Add the lib from the submodule as editable dependency with `uv`:
    `uv add ./mod-manager-lib --editable`

## Basic Usage

The recommended way to load or create a mod instance is by using the respective widgets in `ui/instance_creator` and `ui/instance_selector`.

```python
from PySide6.QtWidgets import QApplication

from mod_manager_lib.core.game_service import GameService
from mod_manager_lib.ui.instance_selector.instance_selector_widget import InstanceSelectorWidget

app = QApplication()

# initialize game service (singleton)
# see tests/data/games.json for an example
GameService("<json data containing the specifications of your supported games>")

widget = InstanceSelectorWidget()
widget.set_cur_game(GameService.get_game_by_id("skyrimse"))

def on_instance_valid(valid: bool) -> None:
    if valid:
        print(f"User selected valid instance: {widget.get_cur_instance_data()} with {widget.get_selected_mod_manager()}")

widget.instance_valid.connect(on_instance_valid)

widget.show()
app.exec()
```
