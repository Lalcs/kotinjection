"""
Definition

Data class representing dependency definitions
"""

from dataclasses import dataclass, field
from typing import Type, Callable, List, Optional, Any, Union

from .lifecycle import KotInjectionLifeCycle


# Scope qualifier type: either a string name or a Type
ScopeQualifier = Union[str, Type]


@dataclass
class Definition:
    """Dependency definition"""
    interface: Type
    factory: Callable
    lifecycle: KotInjectionLifeCycle
    parameter_types: Optional[List[Type]] = None  # Lazily resolved parameter types
    implementation_type: Optional[Type] = None  # Cached implementation type
    instance: Optional[Any] = None
    created_at_start: bool = False  # Eager initialization flag
    scope_qualifier: Optional[ScopeQualifier] = None  # Scope qualifier for SCOPED lifecycle
