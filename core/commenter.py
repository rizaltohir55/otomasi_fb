"""
core/commenter.py
Compatibility Shim Layer yang mengarahkan ke engine/commenter.py.
"""
from engine.commenter import auto_like_first_post, execute_auto_comment_on_group

__all__ = ["auto_like_first_post", "execute_auto_comment_on_group"]
