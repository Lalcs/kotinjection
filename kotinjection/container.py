"""
KotInjectionContainer

This module provides the core DI container implementation with dependency
resolution and lifecycle management. It is the heart of the KotInjection
framework, responsible for:

- Storing and managing dependency definitions
- Resolving dependencies with type inference
- Managing singleton and factory lifecycles
- Detecting circular dependencies

The container is typically not used directly. Instead, use KotInjection
(global API) or KotInjectionCore (isolated container) classes.
"""

from typing import Any, Callable, cast, Dict, List, Type, TypeVar

from .resolution_context import _resolution_context
from .definition import Definition
from .exceptions import (
    CircularDependencyError,
    DefinitionNotFoundError,
    DuplicateDefinitionError,
    TypeInferenceError,
)
from .lifecycle import KotInjectionLifeCycle
from .module import KotInjectionModule
from .resolution_context import ResolutionContext

T = TypeVar('T')


class KotInjectionContainer:
    """Core DI Container with dependency resolution and lifecycle management.

    This class is the internal engine of KotInjection. It stores dependency
    definitions and resolves them with support for:

    - Type inference based on constructor parameter annotations
    - Singleton lifecycle (single instance per container)
    - Factory lifecycle (new instance per request)
    - Circular dependency detection
    - Subscript syntax: container[Type]()

    Attributes:
        _definitions: Dictionary mapping types to their Definition objects

    Note:
        This class is typically not instantiated directly. Use KotInjection
        or KotInjectionCore instead.
    """

    def __init__(self):
        """Initialize an empty container.

        Creates a new container with no registered definitions.
        Use load_modules() to add dependency definitions.
        """
        self._definitions: Dict[Type, Definition] = {}

    def load_modules(self, modules: List[KotInjectionModule]):
        """Load modules and register their definitions.

        Processes each module and adds its definitions to the container.
        Type information is pre-analyzed during module definition, so
        this operation is fast.

        Args:
            modules: List of KotInjectionModule instances to load

        Raises:
            DuplicateDefinitionError: When a type is already registered.
                This prevents accidental overwriting of existing definitions.

        Example::

            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())

            container = KotInjectionContainer()
            container.load_modules([module])
        """
        for module in modules:
            for definition in module.definitions:
                if definition.interface in self._definitions:
                    raise DuplicateDefinitionError(
                        f"{definition.interface} is already registered"
                    )
                self._definitions[definition.interface] = definition

    def get(self, interface: Type[T]) -> T:
        """Get dependency with automatic type inference.

        This method has two modes of operation:

        1. **Top-level call**: When called directly (not from within a factory),
           it resolves the specified interface type.

        2. **Factory call**: When called from within a factory function,
           it uses type inference to determine the parameter type based on
           the constructor signature of the class being instantiated.

        Args:
            interface: The type to resolve (used for top-level calls only)

        Returns:
            The resolved dependency instance

        Raises:
            DefinitionNotFoundError: When the type is not registered
            CircularDependencyError: When a circular dependency is detected
            ResolutionContextError: When called incorrectly within a factory

        Example::

            # Top-level call
            db = container.get(Database)

            # Factory with type inference
            module.factory[UserRepository](
                lambda: UserRepository(db=module.get())  # Type inferred from signature
            )
        """
        ctx = _resolution_context.get()

        if ctx is None:
            # Top-level call - use the provided interface
            return self._resolve(interface)
        else:
            # get() called from within a factory - use shared logic
            param_type = ctx.get_next_parameter_type()
            return self._resolve(cast(Type[T], param_type))

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency by its interface type (direct resolution).

        Unlike get(), this method does not use type inference from the resolution
        context. It always resolves the specified interface directly, regardless
        of whether it's called from within a factory.

        Args:
            interface: The type to resolve

        Returns:
            The resolved dependency instance

        Raises:
            DefinitionNotFoundError: When the interface is not registered
            CircularDependencyError: When a circular dependency is detected

        Example::

            # Always resolves Database, regardless of context
            db = container.resolve(Database)
        """
        return self._resolve(interface)

    def _resolve(self, interface: Type[T]) -> T:
        """Internal dependency resolution implementation.

        This method handles the core resolution logic:
        1. Look up the definition for the interface
        2. Return cached instance if singleton already created
        3. Check for circular dependencies
        4. Create new instance via _create_instance
        5. Cache instance if singleton lifecycle

        Args:
            interface: The type to resolve

        Returns:
            The resolved dependency instance

        Raises:
            DefinitionNotFoundError: When the interface is not registered
            CircularDependencyError: When a circular dependency is detected
        """
        definition = self._definitions.get(interface)
        if definition is None:
            # Handle both Type and string (forward reference) cases
            interface_name = interface.__name__ if hasattr(interface, '__name__') else str(interface)
            registered_types = ", ".join(
                t.__name__ if hasattr(t, '__name__') else str(t)
                for t in self._definitions.keys()
            ) or "None"

            raise DefinitionNotFoundError(
                f"{interface_name} is not registered.\n"
                f"Registered types: {registered_types}\n"
                f"Hint: module.single[{interface_name}](lambda: {interface_name}())"
            )

        # Already instantiated singleton
        if definition.lifecycle == KotInjectionLifeCycle.SINGLETON and definition.instance is not None:
            return definition.instance

        # Circular dependency check
        ctx = _resolution_context.get()
        if ctx is not None and interface in ctx.resolving:
            cycle = " -> ".join(str(t) for t in ctx.resolving) + f" -> {interface}"
            raise CircularDependencyError(f"Circular dependency detected: {cycle}")

        # Create instance
        instance = self._create_instance(interface, definition)

        # Cache if singleton
        if definition.lifecycle == KotInjectionLifeCycle.SINGLETON:
            definition.instance = instance

        return instance

    def _create_instance(self, interface: Type, definition: Definition) -> Any:
        """Create an instance using the factory function.

        This method:
        1. Discovers implementation type via dry-run if not cached
        2. Sets up a resolution context with parameter types
        3. Executes the factory function
        4. Validates the return type (in debug mode)
        5. Handles factory execution errors

        Args:
            interface: The type being instantiated
            definition: The Definition containing factory and metadata

        Returns:
            The newly created instance

        Raises:
            TypeInferenceError: When the factory returns wrong type or fails
            CircularDependencyError: Propagated from nested resolutions

        Note:
            - Singleton: Parameter types are lazily resolved on first access
              via dry-run, then cached for subsequent resolutions.
            - Factory: Dry-run is executed every time to support factories
              that return different implementation types.
        """
        # Type discovery strategy depends on lifecycle
        if definition.lifecycle == KotInjectionLifeCycle.FACTORY:
            # Factory: Always run dry-run (may return different implementations)
            parameter_types = self._discover_parameter_types(interface, definition)
        else:
            # Singleton: Lazy discovery with caching
            if definition.parameter_types is None:
                self._discover_and_cache_parameter_types(interface, definition)
            parameter_types = definition.parameter_types

        # Create a new resolution context
        parent_ctx = _resolution_context.get()
        ctx = ResolutionContext()
        ctx.parameter_types = parameter_types
        ctx.current_index = 0
        ctx.container = self  # Set current container

        if parent_ctx is not None:
            ctx.resolving = parent_ctx.resolving.copy()

        ctx.resolving.add(interface)

        # Set context and execute factory
        token = _resolution_context.set(ctx)
        try:
            instance = definition.factory()

            # Validate return type (only in debug mode for performance)
            # Skip validation if interface is ABC or Protocol (implementation returns subclass)
            if __debug__:
                from abc import ABC
                is_abstract = hasattr(interface, '__abstractmethods__') or (
                    isinstance(interface, type) and issubclass(interface, ABC)
                )
                if not is_abstract and not isinstance(instance, interface):
                    raise TypeInferenceError(
                        f"Factory for {interface.__name__} returned {type(instance).__name__}, "
                        f"expected {interface.__name__}. "
                        f"Ensure the factory returns the correct type."
                    )

            return instance
        except (DefinitionNotFoundError, CircularDependencyError, TypeInferenceError):
            # Re-raise KotInjection exceptions as-is
            raise
        except Exception as e:
            # Wrap unexpected factory exceptions with context
            raise TypeInferenceError(
                f"Factory for {interface.__name__} raised an exception: {e}\n"
                f"Ensure the factory function executes without errors."
            ) from e
        finally:
            _resolution_context.reset(token)

    def _discover_parameter_types(
        self,
        interface: Type,
        definition: Definition
    ) -> List[Type]:
        """Discover parameter types via dry-run without caching.

        Used for Factory lifecycle where different implementations
        may be returned on each call.

        Args:
            interface: The interface type being resolved
            definition: The Definition containing the factory

        Returns:
            List of parameter types for the implementation class

        Raises:
            TypeInferenceError: When type discovery fails
        """
        from .definition_builder import DefinitionBuilder

        # Create dry-run context
        ctx = ResolutionContext()
        ctx.dry_run = True
        ctx.container = self  # Set container for module.get[Type]() to work
        ctx.resolving.add(interface)

        token = _resolution_context.set(ctx)
        try:
            # Execute factory in dry-run mode
            instance = definition.factory()

            # Get the actual implementation type
            impl_type = type(instance)

            # Analyze implementation class constructor
            return DefinitionBuilder._get_parameter_types(impl_type)

        except TypeInferenceError:
            raise
        except Exception as e:
            raise TypeInferenceError(
                f"Failed to discover implementation type for {interface.__name__}. "
                f"The factory raised an exception during type discovery: {e}\n"
                f"Hint: Ensure the factory can be executed without side effects."
            ) from e
        finally:
            _resolution_context.reset(token)

    def _discover_and_cache_parameter_types(
        self,
        interface: Type,
        definition: Definition
    ) -> None:
        """Discover implementation type via dry-run and cache parameter types.

        Used for Singleton lifecycle where the implementation type
        is consistent across all resolutions.

        Args:
            interface: The interface type being resolved
            definition: The Definition to update with discovered types

        Raises:
            TypeInferenceError: When type discovery fails
        """
        parameter_types = self._discover_parameter_types(interface, definition)

        # Cache the results for singleton
        definition.parameter_types = parameter_types

    def unload_modules(self, modules: List[KotInjectionModule]):
        """Unload modules and remove their definitions.

        Removes all definitions that were loaded from the specified modules.
        Any cached singleton instances for these definitions are also released.

        Args:
            modules: List of KotInjectionModule instances to unload

        Note:
            If a definition was overwritten or doesn't exist, it is silently
            skipped. This makes the operation safe to call multiple times.

        Example::

            # Unload a module to replace its definitions
            container.unload_modules([old_module])
            container.load_modules([new_module])
        """
        for module in modules:
            for definition in module.definitions:
                if definition.interface in self._definitions:
                    del self._definitions[definition.interface]

    def __getitem__(self, interface: Type[T]) -> Callable[[], T]:
        """Support subscript syntax: container[Type]().

        This method enables the Koin-style syntax for dependency retrieval.
        When accessed with a type parameter, it returns a callable that
        resolves the dependency when invoked.

        Args:
            interface: The type to resolve

        Returns:
            A callable that returns the resolved dependency

        Example::

            # These are equivalent:
            service = container[MyService]()
            service = container.get(MyService)
        """

        def getter() -> T:
            return self.get(interface)

        return getter

    def eager_initialize(self) -> None:
        """Eagerly initialize all singleton definitions marked with created_at_start=True.

        This method is called after loading modules to initialize singletons
        that were registered with the `created_at_start=True` flag.

        Only SINGLETON definitions with `created_at_start=True` and no existing
        instance will be initialized.

        Example::

            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database(), created_at_start=True)

            container.load_modules([module])
            container.eager_initialize()  # Database instance created here
        """
        for definition in self._definitions.values():
            if (definition.lifecycle == KotInjectionLifeCycle.SINGLETON
                    and definition.created_at_start
                    and definition.instance is None):
                self._resolve(definition.interface)
