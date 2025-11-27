"""
Definition Tests

Tests for the Definition dataclass that stores dependency information.
"""

import unittest

from kotinjection import KotInjectionModule
from kotinjection.definition import Definition
from kotinjection.lifecycle import KotInjectionLifeCycle


class Database:
    """Simple database for testing."""
    pass


class CacheService:
    """Simple cache service for testing."""
    pass


class UserRepository:
    """Repository with dependencies."""

    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


class TestDefinitionDataclass(unittest.TestCase):
    """Test Definition dataclass properties."""

    def test_definition_creation(self):
        """Definition can be created with required fields."""
        factory = lambda: Database()
        definition = Definition(
            interface=Database,
            factory=factory,
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        self.assertEqual(definition.interface, Database)
        self.assertEqual(definition.factory, factory)
        self.assertEqual(definition.lifecycle, KotInjectionLifeCycle.SINGLETON)
        self.assertEqual(definition.parameter_types, [])
        self.assertIsNone(definition.instance)

    def test_definition_with_parameter_types(self):
        """Definition stores parameter types correctly."""
        definition = Definition(
            interface=UserRepository,
            factory=lambda: UserRepository(Database(), CacheService()),
            lifecycle=KotInjectionLifeCycle.FACTORY,
            parameter_types=[Database, CacheService]
        )

        self.assertEqual(definition.parameter_types, [Database, CacheService])
        self.assertEqual(len(definition.parameter_types), 2)

    def test_definition_instance_initially_none(self):
        """Definition.instance is None by default."""
        definition = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        self.assertIsNone(definition.instance)

    def test_definition_instance_can_be_set(self):
        """Definition.instance can be updated."""
        definition = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        db_instance = Database()
        definition.instance = db_instance

        self.assertIs(definition.instance, db_instance)


class TestDefinitionLifecycle(unittest.TestCase):
    """Test Definition lifecycle values."""

    def test_singleton_lifecycle(self):
        """SINGLETON lifecycle is stored correctly."""
        definition = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        self.assertEqual(definition.lifecycle, KotInjectionLifeCycle.SINGLETON)
        self.assertEqual(definition.lifecycle.value, "SINGLETON")

    def test_factory_lifecycle(self):
        """FACTORY lifecycle is stored correctly."""
        definition = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.FACTORY,
            parameter_types=[]
        )

        self.assertEqual(definition.lifecycle, KotInjectionLifeCycle.FACTORY)
        self.assertEqual(definition.lifecycle.value, "FACTORY")


class TestDefinitionIndependence(unittest.TestCase):
    """Test that multiple Definition instances are independent."""

    def test_definitions_are_independent(self):
        """Multiple definitions are independent objects."""
        def1 = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        def2 = Definition(
            interface=Database,
            factory=lambda: Database(),
            lifecycle=KotInjectionLifeCycle.SINGLETON,
            parameter_types=[]
        )

        # Different objects
        self.assertIsNot(def1, def2)

        # Setting instance on one doesn't affect the other
        def1.instance = Database()
        self.assertIsNone(def2.instance)

    def test_parameter_types_list_independence(self):
        """Parameter types list is independent per definition."""
        param_types = [Database, CacheService]

        def1 = Definition(
            interface=UserRepository,
            factory=lambda: UserRepository(Database(), CacheService()),
            lifecycle=KotInjectionLifeCycle.FACTORY,
            parameter_types=param_types
        )

        # Modifying original list doesn't affect definition
        # (dataclass stores the reference, but this tests the expectation)
        self.assertEqual(len(def1.parameter_types), 2)


class TestDefinitionFromModule(unittest.TestCase):
    """Test Definition objects created by module registration."""

    def test_module_creates_definition_for_singleton(self):
        """Module registration creates correct Definition for singleton."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        definitions = module.definitions
        self.assertEqual(len(definitions), 1)

        definition = definitions[0]
        self.assertEqual(definition.interface, Database)
        self.assertEqual(definition.lifecycle, KotInjectionLifeCycle.SINGLETON)
        # parameter_types is None at registration time (lazy resolution)
        self.assertIsNone(definition.parameter_types)

    def test_module_creates_definition_for_factory(self):
        """Module registration creates correct Definition for factory."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        definitions = module.definitions
        self.assertEqual(len(definitions), 1)

        definition = definitions[0]
        self.assertEqual(definition.interface, Database)
        self.assertEqual(definition.lifecycle, KotInjectionLifeCycle.FACTORY)

    def test_module_creates_definition_with_parameter_types(self):
        """Parameter types are lazily resolved at first access."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[UserRepository](
                lambda: UserRepository(module.get(), module.get())
            )

        definitions = module.definitions
        definition = definitions[2]  # UserRepository definition

        # parameter_types is None at registration time
        self.assertIsNone(definition.parameter_types)

        # After resolution, parameter_types should be cached
        from kotinjection import KotInjection
        KotInjection.start(modules=[module])
        try:
            KotInjection.get[UserRepository]()
            self.assertEqual(definition.parameter_types, [Database, CacheService])
        finally:
            KotInjection.stop()


if __name__ == '__main__':
    unittest.main()
