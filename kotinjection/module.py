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

from typing import List, Any

from .resolution_context import _resolution_context
from .definition import Definition
from .exceptions import NotInitializedError, ResolutionContextError
from .factory_builder import FactoryBuilder
from .singleton_builder import SingletonBuilder


class KotInjectionModule:
    """DI Module for defining dependency registrations.

    This class provides the Koin-style DSL for registering dependencies:
    - single[Type]: Register a singleton (same instance reused)
    - factory[Type]: Register a factory (new instance per request)
    - get(): Type inference within factories

    Attributes:
        single: Builder for singleton registrations
        factory: Builder for factory registrations
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
    """

    def __init__(self):
        """Initialize a new module with empty definitions.

        Creates builders for singleton and factory registrations.
        """
        self._definitions: List[Definition] = []
        self.single = SingletonBuilder(self)
        self.factory = FactoryBuilder(self)

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

    @staticmethod
    def get() -> Any:
        """
        Type inference version of get() - for use within factories only

        Retrieves the appropriate container from the runtime context and resolves
        dependencies. Automatically determines whether the global container or
        an isolated container is being used.

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionContextError: When called outside a resolution context
            NotInitializedError: When the container is not initialized

        Example:
            ```python
            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())
                module.single[Repository](lambda: Repository(module.get()))

            # Use with global container
            KotInjection.start(modules=[module])

            # Or use with isolated container
            app = KotInjectionCore()
            app.load_modules([module])
            ```
        """
        ctx = _resolution_context.get()
        if ctx is None:
            raise ResolutionContextError(
                "get() cannot be used without a type parameter. "
                "Use type inference within a factory function or use get[Type]()"
            )

        if ctx.container is None:
            raise NotInitializedError(
                "Container is not initialized. "
                "Call KotInjection.start() or app.load_modules() first"
            )

        # Use shared logic from ResolutionContext
        param_type = ctx.get_next_parameter_type()

        # Resolve dependency from the runtime context's container
        return ctx.container.resolve(param_type)
