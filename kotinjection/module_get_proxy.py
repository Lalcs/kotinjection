"""
ModuleGetProxy

This module provides a proxy object that enables the module.get[Type]() syntax
for explicit type resolution within factory functions.

The proxy allows two styles of dependency resolution:
- module.get[Type]()  # Explicit type (works during DryRun)
- module.get()        # Type inference (returns placeholder during DryRun)

When explicit type is specified, the dependency is resolved immediately,
even during DryRun. This is useful when the resolved instance is used
directly in ways that DryRunPlaceholder cannot handle (e.g., passed to
third-party libraries like SQLAlchemy's create_engine()).

Example::

    module = KotInjectionModule()
    with module:
        module.single[Config](lambda: Config())
        # Use get[Config]() to get actual instance during DryRun
        module.single[DatabaseClient](
            lambda: DatabaseClient(module.get[Config]())
        )
"""

from typing import Callable, Optional, Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .module import KotInjectionModule

T = TypeVar('T')


class ModuleGetProxy:
    """Proxy object supporting module.get[Type]() syntax.

    This class enables both subscript access (get[Type]()) and direct call
    (get()) for dependency resolution within factory functions.

    When using get[Type](), the dependency is resolved immediately even
    during DryRun, allowing the actual instance to be used in places where
    DryRunPlaceholder would cause errors.

    Attributes:
        _module: Reference to the parent KotInjectionModule

    Example::

        # Explicit type - actual instance even in DryRun
        config = module.get[Config]()

        # Type inference - placeholder in DryRun
        config = module.get()
    """

    def __init__(self, module: 'KotInjectionModule'):
        """Initialize the proxy with a reference to the module.

        Args:
            module: The KotInjectionModule instance
        """
        self._module = module

    def __getitem__(self, interface: Type[T]) -> Callable[[], T]:
        """Enable subscript access for explicit type resolution.

        This method is called when using the syntax get[Type].
        It returns a callable that, when invoked, resolves and returns
        the dependency with the specified type.

        During DryRun, this will resolve the actual instance instead of
        returning a DryRunPlaceholder.

        Args:
            interface: The type to retrieve from the container

        Returns:
            A callable that returns an instance of the specified type

        Example::

            # This expression:
            getter = module.get[Config]

            # Returns a callable, and this:
            config = getter()

            # Is equivalent to:
            config = module.get[Config]()
        """
        def resolver() -> T:
            return self._module._get_with_type(interface)
        return resolver

    def __call__(self, index: Optional[int] = None):
        """Support module.get() syntax with type inference.

        This method delegates to the module's type inference logic,
        which uses the resolution context to determine the type.

        During DryRun, this returns a DryRunPlaceholder.

        Args:
            index: Optional index to specify which parameter to resolve.
                   If None, uses the next parameter in sequence.

        Returns:
            The resolved dependency, or DryRunPlaceholder during DryRun
        """
        return self._module._get_inferred(index)
