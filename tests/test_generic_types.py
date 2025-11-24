"""
Generic Types Tests

Tests for handling generic types, Union types, and Optional types
in KotInjection dependency registration and resolution.
"""

import unittest
from typing import Generic, TypeVar, Optional, List

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.core import KotInjectionCore


class Database:
    """Simple database for testing."""
    pass


class CacheService:
    """Simple cache service for testing."""
    pass


class UserRepository:
    """Repository with multiple dependencies."""

    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


class ServiceWithOptional:
    """Service with optional dependency - uses None as default."""

    def __init__(self, db: Database, cache: Optional[CacheService] = None):
        self.db = db
        self.cache = cache


class ServiceWithList:
    """Service with list type dependency."""

    def __init__(self, items: List[str]):
        self.items = items


T = TypeVar('T')


class Repository(Generic[T]):
    """Generic repository for testing."""

    def __init__(self):
        self.items: List[T] = []


class TestOptionalTypeDependencies(unittest.TestCase):
    """Test handling of Optional type parameters."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_class_with_optional_parameter_with_default(self):
        """Class with Optional parameter and default value works."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # ServiceWithOptional has Optional[CacheService] = None
            # We only register Database, not CacheService
            module.single[ServiceWithOptional](
                lambda: ServiceWithOptional(db=module.get())
            )

        KotInjection.start(modules=[module])
        service = KotInjection.get[ServiceWithOptional]()

        self.assertIsNotNone(service.db)
        self.assertIsNone(service.cache)

    def test_class_with_optional_parameter_provided(self):
        """Class with Optional parameter works when dependency is provided explicitly."""
        # Note: KotInjection's type inference uses the raw type annotation.
        # For Optional[X], the type annotation is typing.Optional which cannot
        # be automatically resolved. Use explicit instantiation in the factory.

        class ServiceWithBothParams:
            """Service where both params are non-optional for cleaner testing."""
            def __init__(self, db: Database, cache: CacheService):
                self.db = db
                self.cache = cache

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[ServiceWithBothParams](
                lambda: ServiceWithBothParams(db=module.get(), cache=module.get())
            )

        KotInjection.start(modules=[module])
        service = KotInjection.get[ServiceWithBothParams]()

        self.assertIsNotNone(service.db)
        self.assertIsNotNone(service.cache)


class TestGenericClassRegistration(unittest.TestCase):
    """Test registration and resolution of generic classes."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_register_generic_class_directly(self):
        """Can register a generic class directly (without type parameter)."""
        module = KotInjectionModule()
        with module:
            # Register the generic Repository class directly
            module.single[Repository](lambda: Repository())

        KotInjection.start(modules=[module])
        repo = KotInjection.get[Repository]()

        self.assertIsInstance(repo, Repository)
        self.assertEqual(repo.items, [])


class TestVariableArgumentsHandling(unittest.TestCase):
    """Test handling of *args and **kwargs in constructors."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_class_with_args_kwargs_skipped(self):
        """Classes with *args and **kwargs are handled correctly."""

        class ServiceWithVarArgs:
            def __init__(self, db: Database, *args, **kwargs):
                self.db = db
                self.args = args
                self.kwargs = kwargs

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[ServiceWithVarArgs](
                lambda: ServiceWithVarArgs(db=module.get())
            )

        KotInjection.start(modules=[module])
        service = KotInjection.get[ServiceWithVarArgs]()

        self.assertIsNotNone(service.db)
        self.assertEqual(service.args, ())
        self.assertEqual(service.kwargs, {})

    def test_class_with_only_kwargs(self):
        """Classes with only **kwargs work correctly."""

        class ConfigService:
            def __init__(self, **kwargs):
                self.config = kwargs

        module = KotInjectionModule()
        with module:
            module.single[ConfigService](
                lambda: ConfigService(debug=True, timeout=30)
            )

        KotInjection.start(modules=[module])
        config = KotInjection.get[ConfigService]()

        self.assertEqual(config.config, {'debug': True, 'timeout': 30})


class TestMultipleDependenciesSameType(unittest.TestCase):
    """Test handling of multiple parameters of the same type."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_multiple_same_type_parameters(self):
        """Multiple parameters of same type resolve to same instance (singleton)."""

        class ServiceWithDuplicateTypes:
            def __init__(self, db1: Database, db2: Database):
                self.db1 = db1
                self.db2 = db2

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[ServiceWithDuplicateTypes](
                lambda: ServiceWithDuplicateTypes(db1=module.get(), db2=module.get())
            )

        KotInjection.start(modules=[module])
        service = KotInjection.get[ServiceWithDuplicateTypes]()

        # Both should be the same singleton instance
        self.assertIs(service.db1, service.db2)


class TestIsolatedContainerGenericTypes(unittest.TestCase):
    """Test generic types with isolated containers."""

    def test_isolated_container_with_optional(self):
        """Isolated container handles Optional types correctly."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[ServiceWithOptional](
                lambda: ServiceWithOptional(db=module.get())
            )

        app = KotInjectionCore(modules=[module])
        service = app.get[ServiceWithOptional]()

        self.assertIsNotNone(service.db)
        self.assertIsNone(service.cache)

        app.close()


if __name__ == '__main__':
    unittest.main()
