"""
KotInjectionCore

This module provides the isolated DI container instance for Context Isolation.
Each KotInjectionCore instance maintains its own dependency definitions,
completely separate from the global KotInjection container.

Use Cases:
    - Library development (avoid polluting global container)
    - Multi-tenant applications (tenant-specific dependencies)
    - Test isolation (fresh container per test)

Example::

    # Create an isolated container
    app = KotInjectionCore(modules=[my_module])
    service = app.get[MyService]()

    # Use as context manager for automatic cleanup
    with KotInjectionCore(modules=[module]) as app:
        service = app.get[MyService]()
    # close() is called automatically
"""

from typing import List, TypeVar, Optional

from .container import KotInjectionContainer
from .exceptions import ContainerClosedError
from .module import KotInjectionModule

T = TypeVar('T')


class KotInjectionCore:
    """Isolated KotInjection container instance.

    Provides an independent DI container completely separate from the global container.
    Ideal for library development, multi-tenant applications, and test isolation.

    Attributes:
        _container: Internal KotInjectionContainer instance
        _closed: Flag indicating if the container has been closed

    Example::

        # Create an isolated container instance
        app = KotInjectionCore(modules=[my_module])

        # Get dependencies from the instance
        service = app.get[MyService]()

        # Multiple isolated containers can be used simultaneously
        app1 = KotInjectionCore(modules=[module1])
        app2 = KotInjectionCore(modules=[module2])
    """

    def __init__(self, modules: Optional[List[KotInjectionModule]] = None):
        """Initialize an isolated container instance.

        Args:
            modules: List of DI modules to load initially (optional)

        Example::

            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())

            app = KotInjectionCore(modules=[module])
        """
        self._container: KotInjectionContainer = KotInjectionContainer()
        self._closed: bool = False

        # Load modules if specified
        if modules:
            self.load_modules(modules)

    def _ensure_not_closed(self) -> None:
        """Ensure the container is not closed.

        This helper method eliminates code duplication for closed state checks.

        Raises:
            ContainerClosedError: When the container has been closed
        """
        if self._closed:
            raise ContainerClosedError("This container is already closed")

    @property
    def get(self) -> KotInjectionContainer:
        """Container property for getting dependencies.

        This property returns the internal container, which supports
        the subscript syntax `get[Type]()` for dependency retrieval.

        Returns:
            KotInjectionContainer: The DI container for dependency resolution

        Raises:
            ContainerClosedError: When the container has been closed

        Example::

            app = KotInjectionCore(modules=[my_module])
            service = app.get[MyService]()
        """
        self._ensure_not_closed()
        return self._container

    def load_modules(self, modules: List[KotInjectionModule]):
        """Load additional modules into the container.

        This method allows dynamically adding new dependency definitions
        to the running container.

        Args:
            modules: List of KotInjectionModule instances to load

        Raises:
            ContainerClosedError: When the container has been closed
            DuplicateDefinitionError: When a module contains a type already registered

        Example::

            new_module = KotInjectionModule()
            with new_module:
                new_module.single[CacheService](lambda: CacheService())

            app.load_modules([new_module])
        """
        self._ensure_not_closed()
        self._container.load_modules(modules)

    def unload_modules(self, modules: List[KotInjectionModule]):
        """Unload modules from the container.

        This method removes dependency definitions that were loaded
        from the specified modules.

        Args:
            modules: List of KotInjectionModule instances to unload

        Raises:
            ContainerClosedError: When the container has been closed

        Example::

            app.unload_modules([old_module])
        """
        self._ensure_not_closed()
        self._container.unload_modules(modules)

    def close(self) -> None:
        """Close the container and clean up resources.

        After closing, the container cannot be used for:
        - Retrieving dependencies via get[Type]()
        - Loading or unloading modules

        This method is idempotent - calling it multiple times has no effect.

        Note:
            Future versions may add disposal of singleton instances
            (e.g., calling close() on database connections).

        Example::

            app = KotInjectionCore(modules=[module])
            # ... use the container ...
            app.close()  # Cleanup
        """
        if not self._closed:
            self._closed = True
            # Future: dispose singleton instances here

    @property
    def is_closed(self) -> bool:
        """Check whether the container has been closed.

        Returns:
            True if close() has been called, False otherwise

        Example::

            app = KotInjectionCore(modules=[module])
            print(app.is_closed)  # False
            app.close()
            print(app.is_closed)  # True
        """
        return self._closed

    def __enter__(self) -> 'KotInjectionCore':
        """Enter context manager.

        Returns:
            The KotInjectionCore instance itself

        Example::

            with KotInjectionCore(modules=[module]) as app:
                service = app.get[MyService]()
            # close() is called automatically
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager and close the container.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised

        Returns:
            False (exceptions are not suppressed)
        """
        self.close()
        return False
