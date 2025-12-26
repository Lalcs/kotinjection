"""
GlobalCreateScopeProxy

Proxy for KotInjection.create_scope that supports both call and subscript syntax.
"""

from typing import Type, TypeVar, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .global_context import GlobalContext
    from .scope import Scope

T = TypeVar('T')


class GlobalCreateScopeProxy:
    """Proxy for KotInjection.create_scope that supports both call and subscript syntax.

    Enables:
    - KotInjection.create_scope("scope_name", "scope_id")
    - KotInjection.create_scope[ScopeType]("scope_id")
    """

    def __init__(self, context_getter: Callable[[], 'GlobalContext']):
        """Initialize the proxy with a context getter function.

        Args:
            context_getter: A callable that returns the GlobalContext
        """
        self._context_getter = context_getter

    def __call__(self, scope_qualifier: str, scope_id: str) -> 'Scope':
        """Create a scope with a string qualifier.

        Args:
            scope_qualifier: The string name for the scope
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance

        Example::

            with KotInjection.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        from .global_typed_create_scope import GlobalTypedCreateScope
        return self._context_getter().get().create_scope(scope_qualifier, scope_id)

    def __getitem__(self, scope_type: Type[T]) -> 'GlobalTypedCreateScope[T]':
        """Get a typed scope creator for a type-based scope.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            A callable that creates the scope with just a scope_id

        Example::

            with KotInjection.create_scope[UserSession]("session-1") as scope:
                data = scope.get[SessionData]()
        """
        from .global_typed_create_scope import GlobalTypedCreateScope
        return GlobalTypedCreateScope(self._context_getter, scope_type)
