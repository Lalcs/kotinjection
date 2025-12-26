"""
Scope

Runtime scope instance for managing scoped dependencies.
Each Scope instance maintains its own cache of scoped dependency instances.
"""

from typing import TYPE_CHECKING, Type, TypeVar, Dict, Any, Optional

from .definition import ScopeQualifier
from .scope_get_proxy import ScopeGetProxy

if TYPE_CHECKING:
    from .container import KotInjectionContainer

T = TypeVar('T')


class Scope:
    """Runtime scope instance for resolving scoped dependencies.

    A Scope represents a single instance of a scope definition (e.g., one HTTP request).
    Dependencies registered with `scoped[]` within the matching scope definition
    are cached per Scope instance.

    Attributes:
        scope_id: Unique identifier for this scope instance
        scope_qualifier: The scope qualifier (name or type) this scope matches
        _instances: Cache of scoped dependency instances
        _container: Reference to the parent container
        _closed: Whether this scope has been closed

    Example::

        # Create a scope
        with KotInjection.create_scope("request", "req-123") as scope:
            ctx = scope.get[RequestContext]()  # Created and cached
            ctx2 = scope.get[RequestContext]()  # Same instance
        # Scope closed, instances released
    """

    def __init__(
        self,
        scope_id: str,
        scope_qualifier: ScopeQualifier,
        container: 'KotInjectionContainer'
    ):
        """Initialize a new scope instance.

        Args:
            scope_id: Unique identifier for this scope instance
            scope_qualifier: The scope qualifier (string name or Type)
            container: The parent container for resolving dependencies
        """
        self.scope_id = scope_id
        self.scope_qualifier = scope_qualifier
        self._container = container
        self._instances: Dict[Type, Any] = {}
        self._closed = False

    def _ensure_not_closed(self) -> None:
        """Ensure the scope is not closed.

        Raises:
            RuntimeError: When the scope has been closed
        """
        if self._closed:
            raise RuntimeError(
                f"Scope '{self.scope_id}' has been closed. "
                "Cannot resolve dependencies from a closed scope."
            )

    @property
    def get(self) -> ScopeGetProxy:
        """Get proxy for resolving dependencies within this scope.

        Supports subscript syntax: scope.get[Type]()

        Returns:
            ScopeGetProxy for dependency resolution

        Example::

            with KotInjection.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        self._ensure_not_closed()
        return ScopeGetProxy(self)

    def resolve(self, interface: Type[T]) -> T:
        """Resolve a dependency within this scope.

        For SCOPED dependencies matching this scope's qualifier:
        - Returns cached instance if already created in this scope
        - Creates new instance and caches it if not yet created

        For SINGLETON and FACTORY dependencies:
        - Delegates to the parent container

        Args:
            interface: The type to resolve

        Returns:
            The resolved dependency instance

        Raises:
            DefinitionNotFoundError: When the type is not registered
            RuntimeError: When trying to resolve a scoped dependency
                from the wrong scope
        """
        self._ensure_not_closed()
        return self._container.resolve_in_scope(interface, self)

    def get_cached_instance(self, interface: Type[T]) -> Optional[T]:
        """Get a cached instance from this scope if it exists.

        Args:
            interface: The type to look up

        Returns:
            The cached instance or None if not cached
        """
        return self._instances.get(interface)

    def cache_instance(self, interface: Type[T], instance: T) -> None:
        """Cache an instance in this scope.

        Args:
            interface: The type to cache under
            instance: The instance to cache
        """
        self._instances[interface] = instance

    def close(self) -> None:
        """Close this scope and release all cached instances.

        After closing, the scope cannot be used to resolve dependencies.
        This method is idempotent.
        """
        if not self._closed:
            self._closed = True
            self._instances.clear()

    @property
    def is_closed(self) -> bool:
        """Check whether this scope has been closed.

        Returns:
            True if close() has been called, False otherwise
        """
        return self._closed

    def __enter__(self) -> 'Scope':
        """Enter context manager.

        Returns:
            The Scope instance itself
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager and close the scope.

        Returns:
            False (exceptions are not suppressed)
        """
        self.close()
        return False
