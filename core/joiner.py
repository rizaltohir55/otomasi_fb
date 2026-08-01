"""
core/joiner.py
Compatibility Shim Layer yang mengarahkan ke engine/joiner.py.
"""
from engine.joiner import check_membership_status, execute_join_group

auto_join_group = execute_join_group
__all__ = ["check_membership_status", "execute_join_group", "auto_join_group"]
