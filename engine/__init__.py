"""
Package init untuk engine.
FB AutoEngine 3.0 Ultra.
"""
from engine.selectors import (
    DESKTOP_COMPOSER_TRIGGERS,
    CAPTION_TEXTBOX_SELECTORS,
    POST_BUTTON_SELECTORS,
    JOIN_GROUP_SELECTORS,
)
from engine.browser import (
    create_stealth_context,
    get_session_info,
    save_session_state,
    verify_login_status,
)
from engine.dom_analyzer import (
    dismiss_all_overlays,
    get_active_composer_dialog,
    find_composer_trigger,
    find_caption_textbox,
    find_submit_button,
)
from engine.composer import (
    extract_group_id_and_url,
    is_composer_active,
    open_group_composer,
    type_post_caption,
    attach_media_files,
    submit_group_post,
    execute_post_to_group,
)
from engine.joiner import (
    check_membership_status,
    execute_join_group,
)
from engine.commenter import (
    auto_like_first_post,
    execute_auto_comment_on_group,
)
from engine.collector import (
    load_groups,
    load_caption,
    find_media_images,
)

__all__ = [
    "create_stealth_context",
    "get_session_info",
    "save_session_state",
    "verify_login_status",
    "dismiss_all_overlays",
    "get_active_composer_dialog",
    "find_composer_trigger",
    "find_caption_textbox",
    "find_submit_button",
    "extract_group_id_and_url",
    "is_composer_active",
    "open_group_composer",
    "type_post_caption",
    "attach_media_files",
    "submit_group_post",
    "execute_post_to_group",
    "check_membership_status",
    "execute_join_group",
    "auto_like_first_post",
    "execute_auto_comment_on_group",
    "load_groups",
    "load_caption",
    "find_media_images",
]
