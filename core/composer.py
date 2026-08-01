"""
core/composer.py
Compatibility Shim Layer yang mengarahkan ke engine/composer.py.
"""
from engine.composer import (
    extract_group_id_and_url,
    extract_group_id_and_urls,
    is_composer_active,
    open_group_composer,
    type_post_caption,
    attach_media_files,
    submit_group_post,
    execute_post_to_group,
)

__all__ = [
    "extract_group_id_and_url",
    "extract_group_id_and_urls",
    "is_composer_active",
    "open_group_composer",
    "type_post_caption",
    "attach_media_files",
    "submit_group_post",
    "execute_post_to_group",
]