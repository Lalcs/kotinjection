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
    parameter_types: List[Type]  # Pre-parsed parameter types
    instance: Optional[Any] = None
