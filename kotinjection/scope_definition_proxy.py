"""
ScopeDefinitionProxy

Proxy for module.scope that supports both call and subscript syntax.
"""

from typing import TYPE_CHECKING, Type, TypeVar

if TYPE_CHECKING:
    from .module import KotInjectionModule
    from .scope_definition_context import ScopeDefinitionContext

T = TypeVar('T')


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

    def __call__(self, scope_name: str) -> 'ScopeDefinitionContext':
        """Create a scope definition context with a string qualifier.

        Args:
            scope_name: The string name for the scope

        Returns:
            ScopeDefinitionContext for use with `with` statement

        Example::

            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
        """
        from .scope_definition_context import ScopeDefinitionContext
        return ScopeDefinitionContext(self.module, scope_name)

    def __getitem__(self, scope_type: Type[T]) -> 'ScopeDefinitionContext':
        """Create a scope definition context with a type qualifier.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            ScopeDefinitionContext for use with `with` statement

        Example::

            with module.scope[UserSession]:
                module.scoped[SessionData](lambda: SessionData())
        """
        from .scope_definition_context import ScopeDefinitionContext
        return ScopeDefinitionContext(self.module, scope_type)
