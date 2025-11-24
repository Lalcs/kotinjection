"""
KotInjectionComponent

Base class for components using an isolated container instance
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .core import KotInjectionCore
    from .container import KotInjectionContainer


class IsolatedKotInjectionComponent(ABC):
    """
    Base class for components using an isolated container instance

    By inheriting this class and overriding the `get_app()` method,
    custom components can use an isolated DI container instance.

    Example:
        ```python
        # Define a library-specific container
        library_app = KotInjectionCore(modules=[library_module])

        # Base class for library components
        class LibraryComponent(IsolatedKotInjectionComponent):
            def get_app(self) -> KotInjectionCore:
                return library_app

        # Actual service class
        class MyLibraryService(LibraryComponent):
            def __init__(self):
                # Get dependencies from the isolated container
                self.repository = self.get[MyRepository]()

            def do_something(self):
                return self.repository.fetch_data()

        # Usage example
        service = MyLibraryService()
        result = service.do_something()
        ```

    Note:
        - Library development: Does not conflict with host application's DI
        - Test isolation: Each test case uses an isolated DI container
        - Multi-tenancy: Create isolated components for each tenant
    """

    @abstractmethod
    def get_app(self) -> 'KotInjectionCore':
        """
        Return the KotInjectionCore instance used by this component

        Returns:
            The KotInjectionCore instance to use
        """
        return NotImplemented

    @property
    def get(self) -> 'KotInjectionContainer':
        """
        Return the container for retrieving dependencies

        Returns:
            The isolated container instance

        Example:
            ```python
            class MyService(IsolatedKotInjectionComponent):
                def __init__(self):
                    # Get dependencies using get[Type]() syntax
                    self.repository = self.get[Repository]()
            ```
        """
        return self.get_app().get
