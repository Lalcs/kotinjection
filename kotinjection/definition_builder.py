"""
DefinitionBuilder

This module provides the base class for definition builders that support
the type parameter syntax (e.g., single[Type], factory[Type]).

The DefinitionBuilder performs:
- Type parameter extraction via __getitem__
- Constructor parameter type analysis for type inference
- Definition creation and registration

This class is extended by SingletonBuilder and FactoryBuilder to provide
the specific lifecycle behaviors.
"""

import inspect
from typing import Type, TypeVar, Callable, List, Optional, TYPE_CHECKING

from .exceptions import TypeInferenceError
from .lifecycle import KotInjectionLifeCycle
from .definition import Definition

if TYPE_CHECKING:
    from .module import KotInjectionModule

T = TypeVar('T')


class DefinitionBuilder:
    """Base class for definition builders supporting type parameters.

    This class implements the subscript syntax (builder[Type]) that enables
    Koin-style dependency registration. It handles:

    - Type parameter extraction via __getitem__
    - Constructor signature analysis for type inference
    - Definition creation with pre-analyzed type information

    Attributes:
        module: The KotInjectionModule to register definitions to
        lifecycle: The lifecycle (SINGLETON or FACTORY) for created definitions

    Note:
        This class is not used directly. Use SingletonBuilder or FactoryBuilder
        via module.single or module.factory instead.
    """

    def __init__(self, module: 'KotInjectionModule', lifecycle: KotInjectionLifeCycle):
        """Initialize the builder with a module and lifecycle.

        Args:
            module: The KotInjectionModule to register definitions to
            lifecycle: The lifecycle type (SINGLETON or FACTORY)
        """
        self.module = module
        self.lifecycle = lifecycle

    def __getitem__(self, interface: Type[T]) -> Callable[..., None]:
        """Enable subscript syntax: builder[Type](factory).

        This method enables the Koin-style syntax for dependency registration.
        When called with a type parameter, it returns a registration function
        that accepts a factory callable.

        Args:
            interface: The type to register

        Returns:
            A registration function that accepts a factory callable

        Example::

            # This syntax:
            module.single[Database](lambda: Database())

            # With eager initialization:
            module.single[Database](lambda: Database(), created_at_start=True)

            # Is equivalent to:
            register = module.single[Database]
            register(lambda: Database())
        """

        def register(
            factory: Callable[[], T],
            created_at_start: Optional[bool] = None
        ) -> None:
            # Determine effective created_at_start value:
            # - If explicitly specified at definition level, use that
            # - Otherwise, inherit from module's default
            # - Only applies to SINGLETON lifecycle
            effective_created_at_start = (
                created_at_start if created_at_start is not None
                else self.module._created_at_start
            ) if self.lifecycle == KotInjectionLifeCycle.SINGLETON else False

            # No pre-analysis - parameter types will be resolved lazily
            # at resolution time by executing the factory in dry-run mode
            definition = Definition(
                interface=interface,
                factory=factory,
                lifecycle=self.lifecycle,
                created_at_start=effective_created_at_start,
                # parameter_types will be populated during first resolution
            )
            self.module.add_definition(definition)

        return register

    @staticmethod
    def _get_parameter_types(cls: Type) -> List[Type]:
        """Extract parameter types from a class constructor.

        Analyzes the __init__ method signature to extract type hints
        for all parameters. This information is used for type inference
        when resolving dependencies.

        Args:
            cls: The class to analyze

        Returns:
            List of parameter types from the class constructor,
            excluding 'self', *args, and **kwargs

        Raises:
            TypeInferenceError: When type hints are missing, inspection fails,
                or the class is not inspectable (e.g., built-in types)

        Note:
            This analysis is performed at registration time, not resolution time,
            for better performance during dependency resolution.
        """
        if cls is None:
            raise TypeInferenceError(
                "Cannot analyze parameter types: class is None. "
                "Ensure the type parameter is correctly specified."
            )

        try:
            sig = inspect.signature(cls.__init__)
        except ValueError as e:
            raise TypeInferenceError(
                f"Cannot inspect {cls.__name__}.__init__: {e}. "
                f"This may occur with built-in types or C extension classes."
            ) from e
        except TypeError as e:
            raise TypeInferenceError(
                f"Cannot get signature for {cls.__name__}.__init__: {e}. "
                f"Ensure {cls.__name__} is a class with a valid constructor."
            ) from e

        parameter_types = []
        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            # Skip *args and **kwargs (VAR_POSITIONAL and VAR_KEYWORD)
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue

            if param.annotation == inspect.Parameter.empty:
                raise TypeInferenceError(
                    f"Missing type hint for parameter '{param_name}' in {cls.__name__}.__init__. "
                    f"Type inference requires type hints for all parameters."
                )

            parameter_types.append(param.annotation)

        return parameter_types
