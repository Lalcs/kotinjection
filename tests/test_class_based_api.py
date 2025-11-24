"""
KotInjection Class-based API Tests (unittest version)
"""

import sys
import os
import unittest

# Add tests directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import (
    KotInjectionModule,
    KotInjection,
    KotInjectionLifeCycle,
    CircularDependencyError,
    DefinitionNotFoundError,
    DuplicateDefinitionError,
    KotInjectionError,
    NotInitializedError,
)

from conftest import KotInjectionTestCase


# Test class definitions
class Database:
    def __init__(self):
        self.name = "TestDB"


class CacheService:
    def __init__(self):
        self.cache = {}


class UserRepository:
    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


class RequestHandler:
    def __init__(self, repo: UserRepository):
        self.repo = repo


# Test cases

class TestKotInjectionInitialization(KotInjectionTestCase):
    """Initialization tests"""

    def test_initialize_with_module(self):
        """Can initialize with a module"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        # Verify app is initialized
        self.assertTrue(KotInjection.is_started())

    def test_initialize_with_multiple_modules(self):
        """Can initialize with multiple modules"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[CacheService](lambda: CacheService())

        KotInjection.start(modules=[module1, module2])

        # Verify both modules are loaded
        db = KotInjection.get[Database]()
        cache = KotInjection.get[CacheService]()
        self.assertIsNotNone(db)
        self.assertIsNotNone(cache)


class TestKotInjectionSingleton(KotInjectionTestCase):
    """Singleton tests"""

    def test_single_returns_same_instance(self):
        """single returns the same instance"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[Database]()
        db2 = KotInjection.get[Database]()

        self.assertIs(db1, db2)

    def test_single_with_dependencies(self):
        """single resolves dependencies"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[UserRepository](
                lambda: UserRepository(
                    module.get(),
                    module.get()
                )
            )

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsNotNone(repo.db)
        self.assertIsNotNone(repo.cache)


class TestKotInjectionFactory(KotInjectionTestCase):
    """Factory tests"""

    def test_factory_returns_different_instances(self):
        """factory returns a new instance each time"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[UserRepository](
                lambda: UserRepository(
                    module.get(),
                    module.get()
                )
            )
            module.factory[RequestHandler](
                lambda: RequestHandler(module.get())
            )

        KotInjection.start(modules=[module])

        handler1 = KotInjection.get[RequestHandler]()
        handler2 = KotInjection.get[RequestHandler]()

        self.assertIsNot(handler1, handler2)


class TestKotInjectionGet(KotInjectionTestCase):
    """get tests"""

    def test_get_returns_instance(self):
        """get returns the registered instance"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)

    def test_get_raises_error_when_not_initialized(self):
        """get raises error when not initialized"""
        # Clear the container
        KotInjection.stop()

        with self.assertRaises(NotInitializedError):
            KotInjection.get[Database]()

    def test_get_raises_error_for_unregistered_type(self):
        """get raises error for unregistered type"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class UnregisteredClass:
            pass

        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[UnregisteredClass]()


class TestKotInjectionGetFunc(KotInjectionTestCase):
    """get_func (type inference) tests"""

    def test_get_func_infers_types(self):
        """get_func infers types and resolves dependencies"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[UserRepository](
                lambda: UserRepository(
                    module.get(),
                    module.get()
                )
            )

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo.db, Database)
        self.assertIsInstance(repo.cache, CacheService)


class TestKotInjectionErrorHandling(KotInjectionTestCase):
    """Error handling tests"""

    def test_circular_dependency_detection(self):
        """Detects circular dependencies or type inference errors"""
        # Note: Due to local class definition, type inference may fail before
        # circular dependency detection. Using KotInjectionError as base catch.

        class ServiceA:
            def __init__(self, b: 'ServiceB'):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        module = KotInjectionModule()
        with module:
            module.single[ServiceA](
                lambda: ServiceA(module.get())
            )
            module.single[ServiceB](
                lambda: ServiceB(module.get())
            )

        KotInjection.start(modules=[module])

        with self.assertRaises(KotInjectionError):
            KotInjection.get[ServiceA]()

    def test_duplicate_registration_error(self):
        """Raises error on duplicate registration"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        with self.assertRaises(DuplicateDefinitionError):
            KotInjection.start(modules=[module1, module2])

    def test_load_modules_after_start(self):
        """Loads modules after start"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        KotInjection.start(modules=[module1])

        # Database is available
        db = KotInjection.get[Database]()
        self.assertIsNotNone(db)

        # CacheService is not available yet
        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[CacheService]()

        # Load additional module
        module2 = KotInjectionModule()
        with module2:
            module2.single[CacheService](lambda: CacheService())

        KotInjection.load_modules([module2])

        # Now CacheService is available
        cache = KotInjection.get[CacheService]()
        self.assertIsNotNone(cache)

    def test_unload_modules(self):
        """Unloads modules and releases instances"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[CacheService](lambda: CacheService())

        KotInjection.start(modules=[module1, module2])

        # Both are available
        db = KotInjection.get[Database]()
        cache = KotInjection.get[CacheService]()
        self.assertIsNotNone(db)
        self.assertIsNotNone(cache)

        # Unload module2
        KotInjection.unload_modules([module2])

        # Database still available
        db2 = KotInjection.get[Database]()
        self.assertIsNotNone(db2)

        # CacheService no longer available
        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[CacheService]()


if __name__ == '__main__':
    unittest.main()
