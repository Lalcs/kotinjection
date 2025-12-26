"""
CreateScopeProxy

Proxy for create_scope that supports both call and subscript syntax
for KotInjectionCore.
"""

from typing import Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .container import KotInjectionContainer
    from .scope import Scope

T = TypeVar('T')


class CreateScopeProxy:
    """Proxy for create_scope that supports both call and subscript syntax.

    Enables:
    - app.create_scope("scope_name", "scope_id")
    - app.create_scope[ScopeType]("scope_id")
    """

    def __init__(self, container: 'KotInjectionContainer'):
        """Initialize the proxy with a container reference.

        Args:
            container: The container to create scopes from
        """
        self._container = container

    def __call__(self, scope_qualifier: str, scope_id: str) -> 'Scope':
        """Create a scope with a string qualifier.

        Args:
            scope_qualifier: The string name for the scope
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance

        Example::

            with app.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        return self._container.create_scope(scope_qualifier, scope_id)

    def __getitem__(self, scope_type: Type[T]) -> 'TypedCreateScope[T]':
        """Get a typed scope creator for a type-based scope.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            A callable that creates the scope with just a scope_id

        Example::

            with app.create_scope[UserSession]("session-1") as scope:
                data = scope.get[SessionData]()
        """
        from .typed_create_scope import TypedCreateScope
        return TypedCreateScope(self._container, scope_type)
