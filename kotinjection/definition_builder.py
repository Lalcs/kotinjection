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

import ast
import inspect
import typing
from typing import Type, TypeVar, Callable, List, Optional, Dict, Any, TYPE_CHECKING, Union

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

        # Try to resolve type hints using typing.get_type_hints()
        # This handles forward references (string annotations) and PEP 563
        resolved_hints = DefinitionBuilder._resolve_type_hints(cls)

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

            # Get resolved type from hints, fallback to raw annotation
            param_type = resolved_hints.get(param_name, param.annotation)

            # If still a string, attempt manual resolution
            if isinstance(param_type, str):
                param_type = DefinitionBuilder._resolve_string_annotation(
                    cls, param_name, param_type
                )

            parameter_types.append(param_type)

        return parameter_types

    @staticmethod
    def _resolve_type_hints(cls: Type) -> Dict[str, Any]:
        """Resolve type hints for a class using typing.get_type_hints().

        This method attempts to resolve forward references (string annotations)
        to actual types. It handles various failure scenarios gracefully by
        returning an empty dict, allowing fallback to manual resolution.

        Args:
            cls: The class to resolve type hints for

        Returns:
            Dictionary mapping parameter names to resolved types.
            Returns empty dict if resolution fails.
        """
        try:
            # include_extras=True preserves Annotated[] metadata (Python 3.11+)
            hints = typing.get_type_hints(cls.__init__, include_extras=True)
            return hints
        except NameError:
            # Type not found in scope - common with local classes
            return {}
        except RecursionError:
            # Circular import or self-referencing type
            return {}
        except TypeError:
            # PEP 604 | operator used with a type that doesn't support it
            # (e.g., multiprocessing.Queue which is a method, not a class)
            # Fall back to manual string annotation resolution
            return {}
        except Exception:
            # Any other error - fall back to raw annotations
            return {}

    @staticmethod
    def _resolve_string_annotation(
        cls: Type,
        param_name: str,
        annotation: str
    ) -> Type:
        """Attempt to resolve a string annotation to an actual type.

        This is a fallback mechanism when typing.get_type_hints() fails.
        It tries to find the type in the class's module namespace.

        Args:
            cls: The class containing the annotation
            param_name: The parameter name (for error messages)
            annotation: The string annotation to resolve

        Returns:
            The resolved type

        Raises:
            TypeInferenceError: When the string annotation cannot be resolved
        """
        # Try to get the module's namespace
        module = inspect.getmodule(cls)
        if module is None:
            raise TypeInferenceError(
                f"Cannot resolve forward reference '{annotation}' for parameter "
                f"'{param_name}' in {cls.__name__}.__init__. "
                f"The class's module could not be determined. "
                f"Hint: Define the referenced type before using it, or use "
                f"explicit imports."
            )

        # Build namespace from module's globals
        namespace: Dict[str, Any] = {}
        if hasattr(module, '__dict__'):
            namespace.update(module.__dict__)

        # Also check class's own namespace (for nested classes)
        if hasattr(cls, '__dict__'):
            namespace.update(cls.__dict__)

        # Add typing constructs to namespace for Union conversion
        if 'Union' not in namespace:
            namespace['Union'] = Union
        if 'Optional' not in namespace:
            namespace['Optional'] = Optional

        # Convert PEP 604 union syntax (X | Y) to Union[X, Y] before evaluation
        # This is necessary because some types (like multiprocessing.Queue)
        # don't support the | operator
        converted_annotation = DefinitionBuilder._convert_union_syntax(annotation)

        # Try to evaluate the annotation in the namespace
        try:
            resolved_type = eval(converted_annotation, namespace)
            return resolved_type
        except NameError:
            raise TypeInferenceError(
                f"Cannot resolve forward reference '{annotation}' for parameter "
                f"'{param_name}' in {cls.__name__}.__init__. "
                f"The type '{annotation}' was not found in the module's namespace. "
                f"Hint: Ensure '{annotation}' is defined and imported before "
                f"the dependency is resolved."
            )
        except SyntaxError as e:
            raise TypeInferenceError(
                f"Invalid forward reference '{annotation}' for parameter "
                f"'{param_name}' in {cls.__name__}.__init__: {e}. "
                f"Ensure the annotation is a valid Python type expression."
            ) from e
        except Exception as e:
            raise TypeInferenceError(
                f"Failed to resolve forward reference '{annotation}' for parameter "
                f"'{param_name}' in {cls.__name__}.__init__: {e}."
            ) from e

    @staticmethod
    def _convert_union_syntax(annotation: str) -> str:
        """Convert PEP 604 union syntax (X | Y) to typing.Union[X, Y].

        This method uses the ast module to safely parse and transform
        pipe-style union syntax to the traditional Union[] syntax.
        This is necessary because some types (like multiprocessing.Queue)
        are methods/functions that don't support the | operator.

        Args:
            annotation: The annotation string to convert

        Returns:
            The converted annotation string using Union[] syntax.
            Returns the original if no conversion is needed or parsing fails.

        Example::

            >>> DefinitionBuilder._convert_union_syntax('int | str')
            'Union[int, str]'
            >>> DefinitionBuilder._convert_union_syntax('multiprocessing.Queue | None')
            'Union[multiprocessing.Queue, None]'
        """
        # Quick check: if no pipe operator, return as-is
        if '|' not in annotation:
            return annotation

        try:
            tree = ast.parse(annotation, mode='eval')
        except SyntaxError:
            # Invalid syntax - return original and let eval() handle the error
            return annotation

        class UnionTransformer(ast.NodeTransformer):
            """Transform BinOp(|) nodes to Subscript(Union[...]) nodes."""

            def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
                if isinstance(node.op, ast.BitOr):
                    # Collect all types in the union chain BEFORE transforming children
                    # This ensures X | Y | Z becomes Union[X, Y, Z] not Union[Union[X, Y], Z]
                    types = DefinitionBuilder._collect_union_types(node)
                    # Now transform each collected type (for nested unions inside generics)
                    transformed_types = [self.visit(t) for t in types]
                    return ast.Subscript(
                        value=ast.Name(id='Union', ctx=ast.Load()),
                        slice=ast.Tuple(elts=transformed_types, ctx=ast.Load()),
                        ctx=ast.Load()
                    )
                # For non-BitOr BinOp, use default behavior
                self.generic_visit(node)
                return node

        transformer = UnionTransformer()
        new_tree = transformer.visit(tree)
        ast.fix_missing_locations(new_tree)

        return ast.unparse(new_tree.body)

    @staticmethod
    def _collect_union_types(node: ast.BinOp) -> List[ast.AST]:
        """Collect all types from a chain of | operators.

        Recursively traverses nested BinOp nodes with BitOr operators
        to flatten the union chain into a list.

        Args:
            node: The BinOp AST node to collect types from

        Returns:
            List of AST nodes representing the types in the union

        Example::

            For 'int | str | None', returns AST nodes for [int, str, None]
        """
        types: List[ast.AST] = []

        def collect(n: ast.AST) -> None:
            if isinstance(n, ast.BinOp) and isinstance(n.op, ast.BitOr):
                collect(n.left)
                collect(n.right)
            else:
                types.append(n)

        collect(node)
        return types
