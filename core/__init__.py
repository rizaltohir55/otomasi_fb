"""
Package init untuk core (Compatibility Shim Layer).
"""
from core.poster import post_to_group, execute_post_to_group
from core.joiner import auto_join_group, execute_join_group, check_membership_status
from core.commenter import auto_like_first_post, execute_auto_comment_on_group

__all__ = [
    "post_to_group",
    "execute_post_to_group",
    "auto_join_group",
    "execute_join_group",
    "check_membership_status",
    "auto_like_first_post",
    "execute_auto_comment_on_group",
]
