"""
InjectProxy

This module provides a proxy object that enables the KotInjection.inject[Type]
syntax for lazy dependency injection as class attributes.

The proxy is used as a class attribute on KotInjection, allowing subscript
access that returns InjectDescriptor instances:

    class MyService:
        repository = KotInjection.inject[UserRepository]

This is similar to Koin's `by inject()` pattern in Kotlin.
"""

from typing import Callable, Optional, Type, TypeVar, TYPE_CHECKING

from .inject_descriptor import InjectDescriptor
from .exceptions import NotInitializedError, ContainerClosedError

if TYPE_CHECKING:
    from .core import KotInjectionCore

T = TypeVar('T')


class KotInjectionInjectProxy:
    """
    Proxy object supporting KotInjection.inject[Type] syntax.

    This class enables subscript access at the class level for lazy
    dependency injection. It returns InjectDescriptor instances that
    resolve dependencies on first access.

    Attributes:
        _get_app: Function that returns the current KotInjectionCore instance

    Example::

        # The proxy is used internally like this:
        KotInjection.inject = KotInjectionInjectProxy(
            lambda: KotInjection._context.get_or_null()
        )

        # Users can then do:
        class MyService:
            repository = KotInjection.inject[UserRepository]
    """

    def __init__(self, get_app_func: Callable[[], Optional['KotInjectionCore']]):
        """
        Initialize the proxy with an app getter function.

        Args:
            get_app_func: A callable that returns the current KotInjectionCore
                instance, or None if not initialized
        """
        self._get_app = get_app_func

    def __getitem__(self, interface: Type[T]) -> InjectDescriptor[T]:
        """
        Enable subscript access for lazy dependency injection.

        This method is called when using the syntax inject[Type].
        It returns an InjectDescriptor that resolves the dependency
        on first instance attribute access.

        Args:
            interface: The type to inject

        Returns:
            An InjectDescriptor that will resolve the dependency on access

        Example::

            class MyService:
                # This creates an InjectDescriptor
                repository = KotInjection.inject[UserRepository]

                def action(self):
                    # Dependency resolved here on first access
                    return self.repository.fetch_data()
        """
        get_app = self._get_app

        def get_container():
            app = get_app()
            if app is None:
                raise NotInitializedError(
                    f"KotInjection.start() must be called before accessing "
                    f"injected dependency '{interface.__name__}'"
                )
            return app._container

        return InjectDescriptor(interface, get_container)


def create_inject(app: 'KotInjectionCore') -> 'IsolatedInjectProxy':
    """
    Create an inject proxy for an isolated container.

    Use this function to create inject proxies for KotInjectionCore
    instances (isolated containers) that are separate from the global
    KotInjection container.

    Args:
        app: The KotInjectionCore instance to inject from

    Returns:
        An IsolatedInjectProxy bound to the specified container

    Example::

        from kotinjection import KotInjectionCore, create_inject

        # Create isolated container
        library_app = KotInjectionCore(modules=[library_module])
        library_inject = create_inject(library_app)

        class MyLibraryService:
            repository = library_inject[MyRepository]

            def action(self):
                return self.repository.fetch_data()
    """
    return IsolatedInjectProxy(app)


class IsolatedInjectProxy:
    """
    Inject proxy for isolated containers (KotInjectionCore instances).

    This class is similar to KotInjectionInjectProxy but is bound to
    a specific KotInjectionCore instance rather than the global container.
    """

    def __init__(self, app: 'KotInjectionCore'):
        """
        Initialize the proxy with a specific container.

        Args:
            app: The KotInjectionCore instance to inject from
        """
        self._app = app

    def __getitem__(self, interface: Type[T]) -> InjectDescriptor[T]:
        """
        Enable subscript access for lazy dependency injection.

        Args:
            interface: The type to inject

        Returns:
            An InjectDescriptor that will resolve the dependency on access
        """
        app = self._app

        def get_container():
            if app.is_closed:
                raise ContainerClosedError(
                    f"Cannot inject '{interface.__name__}' from a closed container"
                )
            return app._container

        return InjectDescriptor(interface, get_container)
