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

from typing import List

from .get_proxy import KotInjectionGetProxy
from .inject_proxy import KotInjectionInjectProxy
from .global_context import GlobalContext
from .module import KotInjectionModule


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
