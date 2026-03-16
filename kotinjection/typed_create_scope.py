"""
TypedCreateScope

Helper for type-based scope creation.
"""

from typing import Type, TYPE_CHECKING

if TYPE_CHECKING:
    from .container import KotInjectionContainer
    from .scope import Scope


class TypedCreateScope:
    """Helper for type-based scope creation."""

    def __init__(self, container: 'KotInjectionContainer', scope_type: Type):
        self._container = container
        self._scope_type = scope_type

    def __call__(self, scope_id: str) -> 'Scope':
        """Create the scope with the given ID.

        Args:
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance
        """
        return self._container.create_scope(self._scope_type, scope_id)
