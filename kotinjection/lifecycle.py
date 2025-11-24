"""
KotInjectionLifeCycle Enum

Defines the lifecycle of dependencies
"""

from enum import Enum


class KotInjectionLifeCycle(Enum):
    """Lifecycle of dependencies"""
    SINGLETON = "SINGLETON"
    FACTORY = "FACTORY"
