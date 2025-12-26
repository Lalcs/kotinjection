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

from typing import List, TypeVar, Optional, Type, Union, TYPE_CHECKING

from .container import KotInjectionContainer
from .definition import ScopeQualifier
from .exceptions import ContainerClosedError
from .module import KotInjectionModule

if TYPE_CHECKING:
    from .scope import Scope

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
        to the running container. After loading, any singleton definitions
        marked with `created_at_start=True` will be eagerly initialized.

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
        self._container.eager_initialize()

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

    @property
    def create_scope(self) -> 'CreateScopeProxy':
        """Create a new scope for resolving scoped dependencies.

        Supports both string and type-based scope qualifiers:
        - app.create_scope("request", "req-123")
        - app.create_scope[UserSession]("session-123")

        Returns:
            CreateScopeProxy for scope creation

        Raises:
            ContainerClosedError: When the container has been closed

        Example::

            with app.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        self._ensure_not_closed()
        return CreateScopeProxy(self._container)


class CreateScopeProxy:
    """Proxy for create_scope that supports both call and subscript syntax.

    Enables:
    - app.create_scope("scope_name", "scope_id")
    - app.create_scope[ScopeType]("scope_id")
    """

    def __init__(self, container: KotInjectionContainer):
        """Initialize the proxy with a container reference.

        Args:
            container: The container to create scopes from
        """
        self._container = container

    def __call__(self, scope_qualifier: str, scope_id: str) -> 'Scope':
        """Create a scope with a string qualifier.

        Args:
            scope_qualifier: The string name for the scope
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance

        Example::

            with app.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        return self._container.create_scope(scope_qualifier, scope_id)

    def __getitem__(self, scope_type: Type[T]) -> '_TypedCreateScope[T]':
        """Get a typed scope creator for a type-based scope.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            A callable that creates the scope with just a scope_id

        Example::

            with app.create_scope[UserSession]("session-1") as scope:
                data = scope.get[SessionData]()
        """
        return _TypedCreateScope(self._container, scope_type)


class _TypedCreateScope:
    """Helper for type-based scope creation."""

    def __init__(self, container: KotInjectionContainer, scope_type: Type):
        self._container = container
        self._scope_type = scope_type

    def __call__(self, scope_id: str) -> 'Scope':
        """Create the scope with the given ID.

        Args:
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance
        """
        return self._container.create_scope(self._scope_type, scope_id)
