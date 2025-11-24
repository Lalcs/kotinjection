"""
Test Configuration and Utilities

Common base classes and helper functions for KotInjection tests
"""

import unittest
from typing import Type, List

from kotinjection import KotInjection, KotInjectionModule


class KotInjectionTestCase(unittest.TestCase):
    """
    Base test case class for KotInjection tests.

    Automatically resets the global container before and after each test.
    Uses KotInjection.stop() for proper cleanup.
    """

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()


def create_simple_module(*service_classes: Type) -> KotInjectionModule:
    """
    Create a simple module with singleton registrations for the given classes.

    Each class is registered with a factory that simply instantiates it.
    Classes must have no dependencies (no-arg constructor).

    Args:
        *service_classes: Classes to register

    Returns:
        A KotInjectionModule with the registrations

    Example:
        >>> module = create_simple_module(Database, CacheService)
        >>> KotInjection.start(modules=[module])
    """
    module = KotInjectionModule()
    with module:
        for cls in service_classes:
            # Use default arg to capture the class in the lambda
            module.single[cls](lambda c=cls: c())
    return module


def create_module_with_dependencies(
    registrations: List[tuple]
) -> KotInjectionModule:
    """
    Create a module with complex registrations including dependencies.

    Args:
        registrations: List of tuples (interface, factory_callable)

    Returns:
        A KotInjectionModule with the registrations

    Example:
        >>> module = create_module_with_dependencies([
        ...     (Database, lambda: Database()),
        ...     (Repository, lambda: Repository(module.get())),
        ... ])
    """
    module = KotInjectionModule()
    with module:
        for interface, factory in registrations:
            module.single[interface](factory)
    return module
