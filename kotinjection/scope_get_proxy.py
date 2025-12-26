"""
ScopeGetProxy

Proxy for scope.get[Type]() syntax.
Enables type-safe dependency resolution within a scope using subscript syntax.
"""

from typing import TYPE_CHECKING, Type, TypeVar, Callable

if TYPE_CHECKING:
    from .scope import Scope

T = TypeVar('T')


class ScopeGetProxy:
    """Proxy for scope.get[Type]() syntax.

    Enables type-safe dependency resolution within a scope
    using subscript syntax.
    """

    def __init__(self, scope: 'Scope'):
        """Initialize the proxy with a scope reference.

        Args:
            scope: The Scope to resolve dependencies from
        """
        self._scope = scope

    def __getitem__(self, interface: Type[T]) -> Callable[[], T]:
        """Enable subscript syntax: scope.get[Type]().

        Args:
            interface: The type to resolve

        Returns:
            A callable that returns the resolved dependency

        Example::

            ctx = scope.get[RequestContext]()
        """
        def getter() -> T:
            return self._scope.resolve(interface)
        return getter
