"""
GlobalTypedCreateScope

Helper for type-based scope creation in global API.
"""

from typing import Type, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .global_context import GlobalContext
    from .scope import Scope


class GlobalTypedCreateScope:
    """Helper for type-based scope creation in global API."""

    def __init__(self, context_getter: Callable[[], 'GlobalContext'], scope_type: Type):
        self._context_getter = context_getter
        self._scope_type = scope_type

    def __call__(self, scope_id: str) -> 'Scope':
        """Create the scope with the given ID.

        Args:
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance
        """
        return self._context_getter().get().create_scope[self._scope_type](scope_id)
