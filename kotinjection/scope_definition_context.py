"""
ScopeDefinitionContext

Context manager for defining scoped dependencies within a module.
"""

from typing import TYPE_CHECKING, Optional

from .definition import ScopeQualifier

if TYPE_CHECKING:
    from .module import KotInjectionModule
    from .scoped_builder import ScopedBuilder


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
        self._previous_scoped_builder: Optional['ScopedBuilder'] = None

    def __enter__(self) -> 'ScopeDefinitionContext':
        """Enter the scope definition context.

        Sets up the scoped builder on the module for registering
        scoped dependencies.

        Returns:
            The context itself
        """
        from .scoped_builder import ScopedBuilder

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
