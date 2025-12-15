"""
Copyright (c) Cutleast
"""

if __name__ == "__main__":
    from pathlib import Path

    from cutleast_core_lib.ui.utilities.icon_provider import IconProvider
    from cutleast_core_lib.ui.utilities.ui_mode import UIMode
    from PySide6.QtWidgets import QApplication

    from mod_manager_lib.core.game_service import GameService
    from mod_manager_lib.ui.instance_selector.instance_selector_widget import (
        InstanceSelectorWidget,
    )

    app = QApplication([])

    IconProvider(UIMode.Dark, "#ffffff")
    GameService(Path("tests/data/games.json").read_text("utf-8"))

    widget = InstanceSelectorWidget()
    widget.set_cur_game(GameService.get_game_by_id("skyrimse"))

    def on_instance_valid(valid: bool) -> None:
        print(f"Instance valid: {valid}")
        if valid:
            print(f"Selected instance: {widget.get_cur_instance_data()}")

    widget.instance_valid.connect(on_instance_valid)
    widget.changed.connect(lambda: print("Instance selection changed"))
    widget.show()

    app.exec()
