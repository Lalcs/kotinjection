"""
Context Module

This module provides the KotInjectionContext abstract interface
for context management (similar to Koin's KoinContext).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .core import KotInjectionCore
    from .module import KotInjectionModule


class KotInjectionContext(ABC):
    """Abstract interface for KotInjection context management.

    Defines the contract for context implementations that manage
    KotInjectionCore instances. Similar to Koin's KoinContext interface.

    This interface allows for different context strategies:
        - GlobalContext: Default singleton context for application-wide DI
        - Custom contexts: For testing, multi-tenancy, or library isolation

    Example::

        class CustomContext(KotInjectionContext):
            def __init__(self):
                self._app = None

            def get(self) -> KotInjectionCore:
                if self._app is None:
                    raise NotInitializedError("Not started")
                return self._app

            # ... implement other methods ...
    """

    @abstractmethod
    def get(self) -> 'KotInjectionCore':
        """Get the current KotInjectionCore instance.

        Returns:
            The active KotInjectionCore instance

        Raises:
            NotInitializedError: If context is not started
        """
        pass

    @abstractmethod
    def get_or_null(self) -> Optional['KotInjectionCore']:
        """Get the current KotInjectionCore instance or None.

        Returns:
            The active KotInjectionCore instance, or None if not started
        """
        pass

    @abstractmethod
    def start(self, modules: List['KotInjectionModule']) -> 'KotInjectionCore':
        """Start the context with given modules.

        Args:
            modules: List of KotInjectionModule instances to load

        Returns:
            The created KotInjectionCore instance

        Raises:
            AlreadyStartedError: If context is already started
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the context and release resources.

        This method is idempotent - calling it multiple times has no effect.
        """
        pass

    @abstractmethod
    def load_modules(self, modules: List['KotInjectionModule']) -> None:
        """Load additional modules into the running context.

        Args:
            modules: List of KotInjectionModule instances to load

        Raises:
            NotInitializedError: If context is not started
            DuplicateDefinitionError: If module contains duplicate types
        """
        pass

    @abstractmethod
    def unload_modules(self, modules: List['KotInjectionModule']) -> None:
        """Unload modules from the running context.

        Args:
            modules: List of KotInjectionModule instances to unload

        Raises:
            NotInitializedError: If context is not started
        """
        pass
