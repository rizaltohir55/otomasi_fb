"""
core/poster.py
Compatibility Shim Layer yang mengarahkan ke engine/composer.py.
"""
from engine.composer import execute_post_to_group, open_group_composer, type_post_caption, submit_group_post

post_to_group = execute_post_to_group
__all__ = ["post_to_group", "execute_post_to_group", "open_group_composer", "type_post_caption", "submit_group_post"]
