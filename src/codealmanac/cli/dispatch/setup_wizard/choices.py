"""Drive one setup choice screen with the keyboard."""

from codealmanac.cli.dispatch.setup_wizard.models import SetupCancelled
from codealmanac.cli.dispatch.setup_wizard.options import shortcut_option_index
from codealmanac.cli.dispatch.setup_wizard.terminal import read_setup_key
from codealmanac.cli.render.setup import (
    SetupChoiceScreen,
    render_setup_choice_screen,
)


def choose_setup_option(screen: SetupChoiceScreen, initial_index: int) -> int:
    selected_index = enabled_index(screen, initial_index)
    render_setup_choice_screen(screen, selected_index)
    while True:
        key = read_setup_key()
        if key in {"\x03", "\x1b", "q"}:
            raise SetupCancelled()
        if key in {"\r", "\n"}:
            if screen.options[selected_index].disabled:
                render_setup_choice_screen(screen, selected_index)
                continue
            return selected_index
        shortcut_index = shortcut_option_index(screen, key)
        if shortcut_index is not None:
            return shortcut_index
        next_index = selected_index
        if key in {"\x1b[D", "a"}:
            next_index = (selected_index - 1) % len(screen.options)
        elif key in {"\x1b[C", "d"}:
            next_index = (selected_index + 1) % len(screen.options)
        elif key in {"\x1b[A", "w"}:
            next_index = (selected_index - 1) % len(screen.options)
        elif key in {"\x1b[B", "s"}:
            next_index = (selected_index + 1) % len(screen.options)
        if next_index != selected_index:
            selected_index = enabled_index(screen, next_index, selected_index)
            render_setup_choice_screen(screen, selected_index)


def enabled_index(
    screen: SetupChoiceScreen,
    index: int,
    fallback: int = 0,
) -> int:
    if len(screen.options) == 0:
        return index
    if not screen.options[index].disabled:
        return index
    for offset in range(1, len(screen.options) + 1):
        candidate = (index + offset) % len(screen.options)
        if not screen.options[candidate].disabled:
            return candidate
    return fallback
