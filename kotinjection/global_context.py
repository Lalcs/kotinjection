"""
GlobalContext

Default global context implementation for KotInjection.
Similar to Koin's GlobalContext object.

This module provides:
    - GlobalContext: Singleton context holding the global KotInjectionCore

Example::

    from kotinjection.global_context import GlobalContext

    context = GlobalContext()  # Returns singleton instance
    context.start(modules=[my_module])
    app = context.get()
    context.stop()
"""

from typing import List, Optional

from .context import KotInjectionContext
from .core import KotInjectionCore
from .exceptions import AlreadyStartedError, NotInitializedError
from .module import KotInjectionModule


class GlobalContext(KotInjectionContext):
    """Default global context implementation.

    Singleton pattern that holds the global KotInjectionCore instance.
    Used by the KotInjection class for global API access.

    This class implements the singleton pattern to ensure only one
    global context exists. The KotInjection class delegates to this
    context for all lifecycle operations.

    Attributes:
        _app: The global KotInjectionCore instance (None if not started)

    Example::

        context = GlobalContext()
        context.start(modules=[module])

        # Get the container
        app = context.get()
        service = app.get[MyService]()

        # Stop and cleanup
        context.stop()
    """

    _instance: Optional['GlobalContext'] = None
    _app: Optional[KotInjectionCore]

    def __new__(cls) -> 'GlobalContext':
        """Ensure singleton instance.

        Returns:
            The single GlobalContext instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._app = None
        return cls._instance

    def __init__(self):
        """Initialize the global context.

        Note: Due to singleton pattern, this may be called multiple times
        but will not reinitialize the instance.
        """
        # Avoid re-initialization on subsequent __init__ calls
        pass

    def get(self) -> KotInjectionCore:
        """Get the current KotInjectionCore instance.

        Returns:
            The active KotInjectionCore instance

        Raises:
            NotInitializedError: If KotInjection is not started
        """
        if self._app is None:
            raise NotInitializedError(
                "KotInjection is not started. Call KotInjection.start() first."
            )
        return self._app

    def get_or_null(self) -> Optional[KotInjectionCore]:
        """Get the current KotInjectionCore instance or None.

        Returns:
            The active KotInjectionCore instance, or None if not started
        """
        return self._app

    def start(self, modules: List[KotInjectionModule]) -> KotInjectionCore:
        """Start the global context with given modules.

        Creates a new KotInjectionCore instance and stores it as the
        global container.

        Args:
            modules: List of KotInjectionModule instances to load

        Returns:
            The created KotInjectionCore instance

        Raises:
            AlreadyStartedError: If KotInjection is already started
        """
        if self._app is not None:
            raise AlreadyStartedError(
                "KotInjection is already started. "
                "Call KotInjection.stop() before starting again."
            )
        self._app = KotInjectionCore(modules=modules)
        return self._app

    def stop(self) -> None:
        """Stop the global context and release resources.

        Closes the current container and resets to uninitialized state.
        This method is idempotent - calling it multiple times has no effect.
        """
        if self._app is not None:
            self._app.close()
            self._app = None

    def load_modules(self, modules: List[KotInjectionModule]) -> None:
        """Load additional modules into the running context.

        Args:
            modules: List of KotInjectionModule instances to load

        Raises:
            NotInitializedError: If KotInjection is not started
            DuplicateDefinitionError: If module contains duplicate types
        """
        self.get().load_modules(modules)

    def unload_modules(self, modules: List[KotInjectionModule]) -> None:
        """Unload modules from the running context.

        Args:
            modules: List of KotInjectionModule instances to unload

        Raises:
            NotInitializedError: If KotInjection is not started
        """
        self.get().unload_modules(modules)
