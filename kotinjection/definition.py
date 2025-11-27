"""
Definition

Data class representing dependency definitions
"""

from dataclasses import dataclass
from typing import Type, Callable, List, Optional, Any

from .lifecycle import KotInjectionLifeCycle


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
