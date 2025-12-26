"""
ScopeDefinitionContext

Context manager for defining scoped dependencies within a module.
Supports both string-based and type-based scope qualifiers.
"""

from typing import TYPE_CHECKING, Type, TypeVar, Callable

from .definition import ScopeQualifier
from .scoped_builder import ScopedBuilder

if TYPE_CHECKING:
    from .module import KotInjectionModule

T = TypeVar('T')


class ScopeDefinitionContext:
    """Context manager for defining scoped dependencies.

    Used with the `with module.scope(...)` syntax to define
    dependencies that belong to a specific scope.

    Example::

        # String-based scope
        with module.scope("request"):
            module.scoped[RequestContext](lambda: RequestContext())

        # Type-based scope
        with module.scope[UserSession]:
            module.scoped[SessionData](lambda: SessionData())
    """

    def __init__(self, module: 'KotInjectionModule', scope_qualifier: ScopeQualifier):
        """Initialize the scope definition context.

        Args:
            module: The KotInjectionModule this context belongs to
            scope_qualifier: The scope qualifier (string name or Type)
        """
        self.module = module
        self.scope_qualifier = scope_qualifier
        self._previous_scoped_builder: ScopedBuilder | None = None

    def __enter__(self) -> 'ScopeDefinitionContext':
        """Enter the scope definition context.

        Sets up the scoped builder on the module for registering
        scoped dependencies.

        Returns:
            The context itself
        """
        # Save previous scoped builder (for nested scopes)
        self._previous_scoped_builder = self.module._current_scoped_builder
        # Create new scoped builder for this scope
        self.module._current_scoped_builder = ScopedBuilder(
            self.module, self.scope_qualifier
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit the scope definition context.

        Restores the previous scoped builder.

        Returns:
            False (exceptions are not suppressed)
        """
        self.module._current_scoped_builder = self._previous_scoped_builder
        return False


class ScopeDefinitionProxy:
    """Proxy for module.scope that supports both call and subscript syntax.

    Enables:
    - module.scope("name") - string-based scope qualifier
    - module.scope[Type] - type-based scope qualifier
    """

    def __init__(self, module: 'KotInjectionModule'):
        """Initialize the proxy with a module reference.

        Args:
            module: The KotInjectionModule this proxy belongs to
        """
        self.module = module

    def __call__(self, scope_name: str) -> ScopeDefinitionContext:
        """Create a scope definition context with a string qualifier.

        Args:
            scope_name: The string name for the scope

        Returns:
            ScopeDefinitionContext for use with `with` statement

        Example::

            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
        """
        return ScopeDefinitionContext(self.module, scope_name)

    def __getitem__(self, scope_type: Type[T]) -> ScopeDefinitionContext:
        """Create a scope definition context with a type qualifier.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            ScopeDefinitionContext for use with `with` statement

        Example::

            with module.scope[UserSession]:
                module.scoped[SessionData](lambda: SessionData())
        """
        return ScopeDefinitionContext(self.module, scope_type)
