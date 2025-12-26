"""
Public API

This module provides the global API for KotInjection DI container.
It wraps a GlobalContext instance and exposes class methods
for managing the DI container lifecycle.

Example::

    from kotinjection import KotInjection, KotInjectionModule

    module = KotInjectionModule()
    with module:
        module.single[Database](lambda: Database())

    KotInjection.start(modules=[module])
    db = KotInjection.get[Database]()

    # Stop when done
    KotInjection.stop()
"""

from typing import List, Type, TypeVar, Callable, TYPE_CHECKING

from .get_proxy import KotInjectionGetProxy
from .inject_proxy import KotInjectionInjectProxy
from .global_context import GlobalContext
from .module import KotInjectionModule

if TYPE_CHECKING:
    from .scope import Scope

T = TypeVar('T')


class GlobalCreateScopeProxy:
    """Proxy for KotInjection.create_scope that supports both call and subscript syntax.

    Enables:
    - KotInjection.create_scope("scope_name", "scope_id")
    - KotInjection.create_scope[ScopeType]("scope_id")
    """

    def __init__(self, context_getter: Callable[[], GlobalContext]):
        """Initialize the proxy with a context getter function.

        Args:
            context_getter: A callable that returns the GlobalContext
        """
        self._context_getter = context_getter

    def __call__(self, scope_qualifier: str, scope_id: str) -> 'Scope':
        """Create a scope with a string qualifier.

        Args:
            scope_qualifier: The string name for the scope
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance

        Example::

            with KotInjection.create_scope("request", "req-1") as scope:
                ctx = scope.get[RequestContext]()
        """
        return self._context_getter().get().create_scope(scope_qualifier, scope_id)

    def __getitem__(self, scope_type: Type[T]) -> '_GlobalTypedCreateScope[T]':
        """Get a typed scope creator for a type-based scope.

        Args:
            scope_type: The type to use as scope qualifier

        Returns:
            A callable that creates the scope with just a scope_id

        Example::

            with KotInjection.create_scope[UserSession]("session-1") as scope:
                data = scope.get[SessionData]()
        """
        return _GlobalTypedCreateScope(self._context_getter, scope_type)


class _GlobalTypedCreateScope:
    """Helper for type-based scope creation in global API."""

    def __init__(self, context_getter: Callable[[], GlobalContext], scope_type: Type):
        self._context_getter = context_getter
        self._scope_type = scope_type

    def __call__(self, scope_id: str) -> 'Scope':
        """Create the scope with the given ID.

        Args:
            scope_id: Unique identifier for this scope instance

        Returns:
            A new Scope instance
        """
        return self._context_getter().get().create_scope[self._scope_type](scope_id)


class KotInjection:
    """KotInjection - Koin-like DI Container for Python

    This class provides a global DI container with Koin-style DSL syntax.
    It delegates to a GlobalContext instance internally.

    Attributes:
        get: Proxy object supporting get[Type]() syntax for dependency retrieval
        inject: Proxy object supporting inject[Type] syntax for lazy injection

    Example::

        # Define modules
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.factory[UserRepository](lambda: UserRepository(db=module.get()))

        # Start the container
        KotInjection.start(modules=[module])

        # Retrieve dependencies (eager)
        repo = KotInjection.get[UserRepository]()

        # Or use lazy injection as class attribute
        class MyService:
            db = KotInjection.inject[Database]

            def action(self):
                return self.db.query()  # Resolved on first access

        # Stop when done
        KotInjection.stop()
    """

    # Internal GlobalContext instance
    _context: GlobalContext = GlobalContext()

    # Proxy object supporting get[Type]() syntax (eager)
    get = KotInjectionGetProxy(lambda: KotInjection._context.get_or_null())

    # Proxy object supporting inject[Type] syntax (lazy)
    inject = KotInjectionInjectProxy(lambda: KotInjection._context.get_or_null())

    @classmethod
    def start(cls, modules: List[KotInjectionModule]) -> None:
        """Start KotInjection.

        Internally creates a KotInjectionCore instance and uses it
        as the global container.

        Args:
            modules: List of DI modules

        Raises:
            AlreadyStartedError: When KotInjection is already started.
                Call stop() before starting again.
        """
        cls._context.start(modules)

    @classmethod
    def stop(cls) -> None:
        """Stop KotInjection and release resources.

        This method stops the global container and resets it to
        an uninitialized state. After calling this method:
        - ``KotInjection.get[Type]()`` will raise ``NotInitializedError``
        - ``KotInjection.start()`` can be called again

        This method is idempotent - calling it multiple times has no effect.
        It's safe to call even if KotInjection was never started.

        Example::

            KotInjection.start(modules=[module])
            # ... use the container ...
            KotInjection.stop()  # Cleanup

            # Can start again with different modules
            KotInjection.start(modules=[new_module])
        """
        cls._context.stop()

    @classmethod
    def is_started(cls) -> bool:
        """Check whether KotInjection is started.

        Returns:
            True if start() has been called and stop() has not been called,
            False otherwise

        Example::

            print(KotInjection.is_started())  # False
            KotInjection.start(modules=[module])
            print(KotInjection.is_started())  # True
            KotInjection.stop()
            print(KotInjection.is_started())  # False
        """
        return cls._context.get_or_null() is not None

    @classmethod
    def load_modules(cls, modules: List[KotInjectionModule]) -> None:
        """Load additional modules after KotInjection has started.

        This method allows dynamically adding new dependency definitions
        to the running container.

        Args:
            modules: List of KotInjectionModule instances to load

        Raises:
            NotInitializedError: When KotInjection.start() has not been called
            DuplicateDefinitionError: When a module contains a type already registered

        Example::

            new_module = KotInjectionModule()
            with new_module:
                new_module.single[CacheService](lambda: CacheService())

            KotInjection.load_modules([new_module])
        """
        cls._context.load_modules(modules)

    @classmethod
    def unload_modules(cls, modules: List[KotInjectionModule]) -> None:
        """Unload modules from the global container.

        This method removes dependency definitions that were loaded
        from the specified modules.

        Args:
            modules: List of KotInjectionModule instances to unload

        Raises:
            NotInitializedError: When KotInjection.start() has not been called

        Example::

            KotInjection.unload_modules([old_module])
        """
        cls._context.unload_modules(modules)

    # Proxy object supporting create_scope("name", "id") and create_scope[Type]("id") syntax
    create_scope = GlobalCreateScopeProxy(lambda: KotInjection._context)
