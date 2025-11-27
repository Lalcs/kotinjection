"""
InjectDescriptor

This module provides a descriptor for lazy dependency injection as class attributes.
It enables Koin-style `inject` syntax where dependencies are resolved on first access.

The descriptor is used as a class attribute and resolves the dependency when
accessed on an instance:

    class MyService:
        repository = KotInjection.inject[UserRepository]

        def action(self):
            return self.repository.fetch_data()  # Resolved here

This pattern is similar to Koin's `by inject()` delegate in Kotlin.
"""

from typing import Callable, Generic, Optional, Type, TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from .container import KotInjectionContainer

T = TypeVar('T')


class InjectDescriptor(Generic[T]):
    """
    Descriptor for lazy dependency injection.

    This class implements Python's descriptor protocol to provide lazy
    dependency resolution. When used as a class attribute, the dependency
    is resolved only when accessed on an instance.

    Attributes:
        interface: The type to inject
        get_container: A callable that returns the DI container

    Example::

        class MyService:
            # Creates an InjectDescriptor
            repository = KotInjection.inject[UserRepository]

            def action(self):
                # Dependency resolved on first access
                return self.repository.fetch_data()
    """

    def __init__(
        self,
        interface: Type[T],
        get_container: Callable[[], 'KotInjectionContainer']
    ):
        """
        Initialize the inject descriptor.

        Args:
            interface: The type to inject
            get_container: A callable that returns the container to resolve from
        """
        self.interface = interface
        self.get_container = get_container
        self._attr_name: Optional[str] = None

    def __set_name__(self, owner: Type, name: str) -> None:
        """
        Called when descriptor is assigned to a class attribute.

        Args:
            owner: The class that owns this descriptor
            name: The attribute name this descriptor is assigned to
        """
        self._attr_name = name

    def __get__(self, obj: Optional[object], objtype: Optional[Type] = None) -> T:
        """
        Resolve dependency when accessed on an instance.

        When accessed on a class (obj is None), returns the descriptor itself.
        When accessed on an instance, resolves and caches the dependency.

        Args:
            obj: The instance accessing the attribute (None if class access)
            objtype: The class type

        Returns:
            The resolved dependency instance, or self if accessed on class
        """
        if obj is None:
            # Class-level access: MyClass.attribute
            return self  # type: ignore

        # Instance-level access: resolve and cache in instance __dict__
        if self._attr_name is not None and self._attr_name in obj.__dict__:
            # Already cached - return cached instance
            return obj.__dict__[self._attr_name]

        # Resolve from container
        container = self.get_container()
        instance = container.get(self.interface)

        # Cache in instance __dict__ for future access
        if self._attr_name is not None:
            obj.__dict__[self._attr_name] = instance

        return instance

    def __set__(self, obj: object, value: T) -> None:
        """
        Prevent setting the descriptor value.

        Injected dependencies are read-only to maintain consistency
        with the DI container's lifecycle management.

        Args:
            obj: The instance
            value: The value being assigned

        Raises:
            AttributeError: Always raised - inject descriptors are read-only
        """
        raise AttributeError(
            f"Cannot set inject descriptor for '{self.interface.__name__}'. "
            "Injected dependencies are read-only."
        )

    def __repr__(self) -> str:
        """Return a string representation of the descriptor."""
        return f"InjectDescriptor[{self.interface.__name__}]"
