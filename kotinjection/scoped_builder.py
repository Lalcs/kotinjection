"""
ScopedBuilder

Builder for scoped definitions that live within a specific scope.
Scoped dependencies are shared within the same scope instance but
separate across different scope instances.
"""

from typing import TYPE_CHECKING, Type, TypeVar, Callable, Optional, Union

from .definition import Definition, ScopeQualifier
from .lifecycle import KotInjectionLifeCycle

if TYPE_CHECKING:
    from .module import KotInjectionModule

T = TypeVar('T')


class ScopedBuilder:
    """Builder for scoped definitions.

    Scoped dependencies are:
    - Shared within the same scope instance (like singleton within a scope)
    - Separate across different scope instances
    - Only accessible from within the scope they belong to

    Attributes:
        module: The KotInjectionModule to register definitions to
        scope_qualifier: The scope qualifier (name or type) this builder belongs to
    """

    def __init__(
        self,
        module: 'KotInjectionModule',
        scope_qualifier: ScopeQualifier
    ):
        """Initialize the scoped builder.

        Args:
            module: The KotInjectionModule to register definitions to
            scope_qualifier: The scope qualifier (string name or Type)
        """
        self.module = module
        self.scope_qualifier = scope_qualifier

    def __getitem__(self, interface: Type[T]) -> Callable[..., None]:
        """Enable subscript syntax: scoped[Type](factory).

        Args:
            interface: The type to register

        Returns:
            A registration function that accepts a factory callable

        Example::

            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
        """
        from .definition_builder import DefinitionBuilder

        def register(
            factory_or_type: Union[Callable[[], T], Type[T]],
        ) -> None:
            # Check if factory_or_type is a Type (class) or Callable (factory)
            if isinstance(factory_or_type, type):
                impl_type = factory_or_type
                module_ref = self.module

                def auto_factory(implementation: Type[T] = impl_type) -> T:
                    """Auto-generated factory that resolves dependencies from __init__."""
                    param_types = DefinitionBuilder._get_parameter_types(implementation)
                    args = [module_ref.get[t]() for t in param_types]
                    return implementation(*args)

                factory = auto_factory
            else:
                factory = factory_or_type

            definition = Definition(
                interface=interface,
                factory=factory,
                lifecycle=KotInjectionLifeCycle.SCOPED,
                scope_qualifier=self.scope_qualifier,
            )
            self.module.add_definition(definition)

        return register
