"""
ResolutionContext

This module provides the context management for dependency resolution.
The ResolutionContext tracks:

- Currently resolving types (for circular dependency detection)
- Parameter types for type inference
- Current resolution index
- Active container reference

The context is stored in a ContextVar for thread-safety and is
automatically managed during dependency resolution.
"""

from contextvars import ContextVar
from typing import List, Optional, Set, Type, TYPE_CHECKING

from .exceptions import ResolutionContextError

if TYPE_CHECKING:
    from .container import KotInjectionContainer
    from .scope import Scope


class ResolutionContext:
    """Context for dependency resolution with type inference support.

    This class maintains the state needed during dependency resolution:

    - Tracks types currently being resolved (circular dependency detection)
    - Stores pre-analyzed parameter types for type inference
    - Manages the index for sequential get() calls in factories
    - Holds a reference to the active container

    Attributes:
        resolving: Set of types currently in the resolution chain
        parameter_types: List of constructor parameter types for type inference
        current_index: Current position in parameter_types for get() calls
        container: Reference to the container performing the resolution
        dry_run: Flag indicating dry-run mode for type discovery
        current_scope: Active scope for scoped dependency resolution

    Note:
        This class is used internally by KotInjectionContainer.
        Users should not need to interact with it directly.

    Example (internal usage)::

        ctx = ResolutionContext()
        ctx.parameter_types = [Database, CacheService]
        ctx.current_index = 0

        # First get() call returns Database
        param1 = ctx.get_next_parameter_type()  # Database

        # Second get() call returns CacheService
        param2 = ctx.get_next_parameter_type()  # CacheService
    """

    def __init__(self):
        """Initialize an empty resolution context.

        Creates a context with no types being resolved and empty
        parameter type list. The container reference is initially None.
        """
        self.resolving: Set[Type] = set()  # For circular dependency detection
        self.parameter_types: List[Type] = []  # Parameter types currently being resolved
        self.current_index: int = 0  # Call order of get()
        self.container: Optional['KotInjectionContainer'] = None  # Currently active container
        self.dry_run: bool = False  # Dry-run mode for type discovery
        self.current_scope: Optional['Scope'] = None  # Active scope for scoped resolution

    def get_next_parameter_type(self) -> Type:
        """Get the next parameter type and increment the index.

        This method implements the type inference mechanism for get() calls
        within factory functions. It returns parameter types in order based
        on the constructor signature that was pre-analyzed.

        Returns:
            The next parameter type to resolve

        Raises:
            ResolutionContextError: When get() is called more times than
                there are parameters in the constructor. This indicates
                a mismatch between the factory and the class signature.

        Example::

            # For a class: def __init__(self, db: Database, cache: Cache)
            ctx.parameter_types = [Database, Cache]

            ctx.get_next_parameter_type()  # Returns Database
            ctx.get_next_parameter_type()  # Returns Cache
            ctx.get_next_parameter_type()  # Raises ResolutionContextError
        """
        if self.current_index >= len(self.parameter_types):
            raise ResolutionContextError(
                f"Too many get() calls. Expected {len(self.parameter_types)} arguments, "
                f"but got at least {self.current_index + 1}."
            )

        param_type = self.parameter_types[self.current_index]
        self.current_index += 1
        return param_type


# Global resolution context for type inference during dependency resolution
_resolution_context: ContextVar[Optional[ResolutionContext]] = ContextVar(
    '_KOT_INJECTION_RESOLUTION_CONTEXT',
    default=None
)
