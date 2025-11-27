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

from typing import List, Any, Optional

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
    def get(index: Optional[int] = None) -> Any:
        """
        Type inference version of get() - for use within factories only

        Retrieves the appropriate container from the runtime context and resolves
        dependencies. Automatically determines whether the global container or
        an isolated container is being used.

        Args:
            index: Optional parameter index to resolve. If specified, resolves
                the parameter at that index directly instead of using sequential
                type inference. Use this when mixing manual instances with
                module.get() calls.

        Returns:
            The resolved dependency instance

        Raises:
            ResolutionContextError: When called outside a resolution context,
                or when index is out of range
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

        Example with index parameter:
            ```python
            class UserRepository:
                def __init__(self, redis: Redis, db: Database):
                    ...

            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())
                # Use index=1 to resolve the second parameter (Database)
                module.single[UserRepository](
                    lambda: UserRepository(Redis(host="localhost"), module.get(1))
                )
            ```

        Note:
            When mixing manual instances with module.get(), prefer using
            keyword arguments for clarity:
            ``lambda: UserRepository(redis=Redis(), db=module.get())``
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
