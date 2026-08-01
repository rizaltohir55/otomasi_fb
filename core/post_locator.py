"""
core/post_locator.py
Compatibility Shim Layer yang mengarahkan ke engine/dom_analyzer.py.
"""
from engine.dom_analyzer import (
    find_composer_trigger,
    find_caption_textbox,
    find_submit_button,
    get_active_composer_dialog,
    dismiss_all_overlays,
)

__all__ = [
    "find_composer_trigger",
    "find_caption_textbox",
    "find_submit_button",
    "get_active_composer_dialog",
    "dismiss_all_overlays",
]
