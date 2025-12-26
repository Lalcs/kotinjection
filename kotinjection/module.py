"""
KotInjectionModule

This module provides the DI module class for defining dependencies.
A KotInjectionModule is a container that holds dependency definitions,
which are then loaded into a KotInjection container.

Key features:
- Koin-style DSL syntax: module.single[Type]() and module.factory[Type]()
- Type inference via module.get() within factories
- Context manager support for cleaner definition blocks

Example::

    module = KotInjectionModule()
    with module:
        module.single[Database](lambda: Database())
        module.factory[UserRepository](
            lambda: UserRepository(db=module.get())
        )

    KotInjection.start(modules=[module])
"""

from typing import List, Any, Optional, Type, TypeVar, TYPE_CHECKING

from .resolution_context import _resolution_context
from .definition import Definition
from .exceptions import NotInitializedError, ResolutionContextError
from .factory_builder import FactoryBuilder
from .singleton_builder import SingletonBuilder
from .module_get_proxy import ModuleGetProxy
from .scope_definition_proxy import ScopeDefinitionProxy

if TYPE_CHECKING:
    from .scoped_builder import ScopedBuilder

T = TypeVar('T')


class KotInjectionModule:
    """DI Module for defining dependency registrations.

    This class provides the Koin-style DSL for registering dependencies:
    - single[Type]: Register a singleton (same instance reused)
    - factory[Type]: Register a factory (new instance per request)
    - scoped[Type]: Register a scoped dependency (shared within scope)
    - scope("name") or scope[Type]: Define a scope for scoped dependencies
    - get(): Type inference within factories

    Attributes:
        single: Builder for singleton registrations
        factory: Builder for factory registrations
        scope: Proxy for defining scope contexts
        scoped: Builder for scoped registrations (only valid within scope context)
        _definitions: Internal list of registered definitions

    Example::

        module = KotInjectionModule()
        with module:
            # Singleton - same instance every time
            module.single[Database](lambda: Database())

            # Factory - new instance every time
            module.factory[UserRepository](
                lambda: UserRepository(db=module.get())
            )

            # Scoped - shared within the same scope instance
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
    """

    def __init__(self, created_at_start: bool = False):
        """Initialize a new module with empty definitions.

        Creates builders for singleton and factory registrations.

        Args:
            created_at_start: If True, all singleton definitions in this module
                will be eagerly initialized at start() time. Defaults to False.
        """
        self._definitions: List[Definition] = []
        self._created_at_start: bool = created_at_start
        self.single = SingletonBuilder(self)
        self.factory = FactoryBuilder(self)
        self.scope = ScopeDefinitionProxy(self)
        self._current_scoped_builder: Optional['ScopedBuilder'] = None

    def __enter__(self) -> 'KotInjectionModule':
        """Enter context manager for cleaner definition blocks.

        The context manager is optional but provides visual structure
        for module definitions.

        Returns:
            The module instance itself
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised

        Returns:
            False (exceptions are not suppressed)
        """
        return False

    @property
    def definitions(self) -> List[Definition]:
        """Get registered definitions (read-only access for container).

        Returns:
            List of Definition objects registered in this module
        """
        return self._definitions

    @property
    def scoped(self) -> 'ScopedBuilder':
        """Get the scoped builder for registering scoped dependencies.

        This property is only valid within a scope definition context.
        Use `with module.scope("name"):` or `with module.scope[Type]:`
        to enter a scope context before using scoped.

        Returns:
            ScopedBuilder for registering scoped dependencies

        Raises:
            ResolutionContextError: When called outside a scope context

        Example::

            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
        """
        if self._current_scoped_builder is None:
            raise ResolutionContextError(
                "scoped[] must be used within a scope context. "
                "Use 'with module.scope(\"name\"):' or 'with module.scope[Type]:' first."
            )
        return self._current_scoped_builder

    def add_definition(self, definition: Definition) -> None:
        """Add a definition to the module.

        This is used internally by definition builders (SingletonBuilder,
        FactoryBuilder) to register new dependency definitions.

        Args:
            definition: The Definition object to add

        Note:
            This method does not check for duplicates. Duplicate checking
            is performed when the module is loaded into a container.
        """
        self._definitions.append(definition)

    @property
    def get(self) -> ModuleGetProxy:
        """Get proxy for dependency resolution within factories.

        Supports two styles of dependency resolution:
        - module.get[Type]()  # Explicit type (works during DryRun)
        - module.get()        # Type inference (placeholder during DryRun)

        When using get[Type](), the dependency is resolved immediately even
        during DryRun, allowing the actual instance to be used in places where
        DryRunPlaceholder would cause errors (e.g., third-party libraries).

        Returns:
            ModuleGetProxy that supports both subscript and call syntax

        Example with type inference::

            module.single[Repository](lambda: Repository(module.get()))

        Example with explicit type (avoids DryRun issues)::

            module.single[DatabaseClient](
                lambda: DatabaseClient(module.get[Config]())
            )
        """
        return ModuleGetProxy(self)

    def _get_with_type(self, interface: Type[T]) -> T:
        """Resolve dependency with explicit type specification.

        This method resolves the actual instance even during DryRun,
        allowing it to be used with third-party libraries that cannot
        handle DryRunPlaceholder.

        Args:
            interface: The type to resolve from the container

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionContextError: When called outside a resolution context
            NotInitializedError: When the container is not initialized
        """
        ctx = _resolution_context.get()
        if ctx is None:
            raise ResolutionContextError(
                "get[Type]() must be used within a factory function"
            )

        # Increment index to maintain consistency with _get_inferred()
        ctx.current_index += 1

        if ctx.container is None:
            raise NotInitializedError(
                "Container is not initialized. "
                "Call KotInjection.start() or app.load_modules() first"
            )

        # Always resolve actual instance (even in DryRun)
        return ctx.container.resolve(interface)

    def _get_inferred(self, index: Optional[int] = None) -> Any:
        """Resolve dependency with type inference.

        This is the original get() logic that uses the resolution context
        to determine the type based on parameter position.

        During DryRun, returns a DryRunPlaceholder for type discovery.

        Args:
            index: Optional parameter index to resolve. If specified, resolves
                the parameter at that index directly instead of using sequential
                type inference.

        Returns:
            The resolved dependency instance, or DryRunPlaceholder during DryRun

        Raises:
            ResolutionContextError: When called outside a resolution context,
                or when index is out of range
            NotInitializedError: When the container is not initialized

        Example::

            module.single[Repository](lambda: Repository(module.get()))

        Example with index::

            module.single[UserRepository](
                lambda: UserRepository(Redis(host="localhost"), module.get(1))
            )
        """
        ctx = _resolution_context.get()
        if ctx is None:
            raise ResolutionContextError(
                "get() cannot be used without a type parameter. "
                "Use type inference within a factory function or use get[Type]()"
            )

        # In dry-run mode, return a placeholder for type discovery
        if ctx.dry_run:
            from .dry_run_placeholder import DryRunPlaceholder
            return DryRunPlaceholder()

        if ctx.container is None:
            raise NotInitializedError(
                "Container is not initialized. "
                "Call KotInjection.start() or app.load_modules() first"
            )

        # If index is specified, resolve that specific parameter
        if index is not None:
            if index < 0 or index >= len(ctx.parameter_types):
                raise ResolutionContextError(
                    f"Index {index} out of range. "
                    f"Expected 0-{len(ctx.parameter_types) - 1}."
                )
            param_type = ctx.parameter_types[index]
        else:
            # Use shared logic from ResolutionContext
            param_type = ctx.get_next_parameter_type()

        # Resolve dependency from the runtime context's container
        return ctx.container.resolve(param_type)
