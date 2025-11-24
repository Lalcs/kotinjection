"""
GetProxy

This module provides a proxy object that enables the KotInjection.get[Type]()
syntax for dependency retrieval at the class level.

The proxy is used as a class attribute on KotInjection, allowing subscript
access without requiring a metaclass. This enables the Koin-style syntax:

    service = KotInjection.get[MyService]()

Instead of:

    service = KotInjection.get(MyService)
"""

from typing import Callable, Optional, Type, TypeVar, TYPE_CHECKING

from .exceptions import NotInitializedError

if TYPE_CHECKING:
    from .core import KotInjectionCore

T = TypeVar('T')


class KotInjectionGetProxy:
    """Proxy object supporting KotInjection.get[Type]() syntax.

    This class enables subscript access at the class level for dependency
    retrieval without using a metaclass. It is used as a class attribute
    on KotInjection.

    The proxy holds a function that retrieves the current KotInjectionCore
    instance, allowing it to delegate to the active container.

    Attributes:
        _get_app: Function that returns the current KotInjectionCore instance

    Example::

        # The proxy is used internally like this:
        KotInjection.get = KotInjectionGetProxy(lambda: KotInjection._context.get_or_null())

        # Users can then do:
        service = KotInjection.get[MyService]()
    """

    def __init__(self, get_app_func: Callable[[], Optional['KotInjectionCore']]):
        """Initialize the proxy with an app getter function.

        Args:
            get_app_func: A callable that returns the current KotInjectionCore
                instance, or None if not initialized
        """
        self._get_app = get_app_func

    def __getitem__(self, interface: Type[T]) -> Callable[[], T]:
        """Enable subscript access for type-safe dependency retrieval.

        This method is called when using the syntax get[Type].
        It returns a callable that, when invoked, resolves and returns
        the dependency.

        Args:
            interface: The type to retrieve from the container

        Returns:
            A callable that returns an instance of the specified type

        Raises:
            NotInitializedError: When KotInjection.start() has not been called

        Example::

            # This expression:
            getter = KotInjection.get[MyService]

            # Returns a callable, and this:
            service = getter()

            # Is equivalent to:
            service = KotInjection.get[MyService]()
        """
        app = self._get_app()
        if app is None:
            raise NotInitializedError("KotInjection.start() must be called first")
        return app.get[interface]
