"""
InjectDescriptor Tests

Tests for lazy dependency injection via KotInjection.inject[Type] syntax.
"""

import sys
import os
import unittest

# Add tests directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conftest import KotInjectionTestCase
from kotinjection import (
    KotInjection,
    KotInjectionCore,
    KotInjectionModule,
    NotInitializedError,
    ContainerClosedError,
    InjectDescriptor,
    create_inject,
)


# Test fixtures
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


class TestInjectDescriptor(KotInjectionTestCase):
    """Test KotInjection.inject[Type] descriptor"""

    def test_inject_resolves_dependency_on_access(self):
        """Dependency is resolved on attribute access"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service = MyService()
        self.assertIsInstance(service.db, Database)
        self.assertEqual(service.db.name, "TestDB")

    def test_inject_raises_error_before_start(self):
        """Raises NotInitializedError when accessed before start()"""
        KotInjection.stop()

        class MyService:
            db = KotInjection.inject[Database]

        service = MyService()
        with self.assertRaises(NotInitializedError) as ctx:
            _ = service.db

        self.assertIn("Database", str(ctx.exception))

    def test_inject_singleton_returns_same_instance(self):
        """Singleton registration returns the same instance"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service1 = MyService()
        service2 = MyService()

        # Same instance because it's a singleton
        self.assertIs(service1.db, service2.db)

    def test_inject_factory_returns_different_instances_per_service(self):
        """Factory registration returns different instances per service"""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service1 = MyService()
        service2 = MyService()

        # Different service instances have different DB instances
        self.assertIsNot(service1.db, service2.db)

    def test_inject_caches_in_instance_dict(self):
        """Resolved dependency is cached per instance"""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service = MyService()
        db1 = service.db
        db2 = service.db

        # Same DB instance within the same service instance (cached)
        self.assertIs(db1, db2)

    def test_inject_is_readonly(self):
        """Injected attributes are read-only"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service = MyService()
        with self.assertRaises(AttributeError):
            service.db = Database()

    def test_inject_with_dependencies(self):
        """Types with dependencies can also be injected"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[UserRepository](
                lambda: UserRepository(module.get(), module.get())
            )

        KotInjection.start(modules=[module])

        class MyService:
            repo = KotInjection.inject[UserRepository]

        service = MyService()
        self.assertIsInstance(service.repo, UserRepository)
        self.assertIsInstance(service.repo.db, Database)
        self.assertIsInstance(service.repo.cache, CacheService)

    def test_class_access_returns_descriptor(self):
        """Class-level access returns the descriptor itself"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        # Access from class
        self.assertIsInstance(MyService.db, InjectDescriptor)

    def test_inject_descriptor_repr(self):
        """Descriptor has proper string representation"""

        class MyService:
            db = KotInjection.inject[Database]

        descriptor = MyService.db
        self.assertEqual(repr(descriptor), "InjectDescriptor[Database]")

    def test_multiple_inject_attributes(self):
        """Multiple inject attributes can be defined"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]
            cache = KotInjection.inject[CacheService]

        service = MyService()
        self.assertIsInstance(service.db, Database)
        self.assertIsInstance(service.cache, CacheService)


class TestCreateInject(KotInjectionTestCase):
    """Test create_inject for isolated containers"""

    def test_create_inject_with_isolated_container(self):
        """Inject works with isolated containers"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])
        app_inject = create_inject(app)

        class MyService:
            db = app_inject[Database]

        service = MyService()
        self.assertIsInstance(service.db, Database)

        app.close()

    def test_create_inject_closed_container_raises_error(self):
        """Raises ContainerClosedError when injecting from closed container"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])
        app_inject = create_inject(app)

        class MyService:
            db = app_inject[Database]

        app.close()

        service = MyService()
        with self.assertRaises(ContainerClosedError):
            _ = service.db

    def test_isolated_containers_are_independent(self):
        """Isolated containers are independent from each other"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        app1 = KotInjectionCore(modules=[module1])
        app2 = KotInjectionCore(modules=[module2])

        inject1 = create_inject(app1)
        inject2 = create_inject(app2)

        class Service1:
            db = inject1[Database]

        class Service2:
            db = inject2[Database]

        s1 = Service1()
        s2 = Service2()

        # Instances from different containers are different
        self.assertIsNot(s1.db, s2.db)

        app1.close()
        app2.close()

    def test_global_and_isolated_containers_are_independent(self):
        """Global and isolated containers are independent"""
        global_module = KotInjectionModule()
        with global_module:
            global_module.single[Database](lambda: Database())

        isolated_module = KotInjectionModule()
        with isolated_module:
            isolated_module.single[Database](lambda: Database())

        KotInjection.start(modules=[global_module])
        app = KotInjectionCore(modules=[isolated_module])
        app_inject = create_inject(app)

        class GlobalService:
            db = KotInjection.inject[Database]

        class IsolatedService:
            db = app_inject[Database]

        global_service = GlobalService()
        isolated_service = IsolatedService()

        # Instances from different containers are different
        self.assertIsNot(global_service.db, isolated_service.db)

        app.close()


class TestInjectDescriptorEdgeCases(KotInjectionTestCase):
    """Edge cases and special scenarios"""

    def test_class_definition_before_start_is_allowed(self):
        """Class definition is allowed before start()"""
        # KotInjection.stop() is called in setUp

        # No error during class definition
        class MyService:
            db = KotInjection.inject[Database]

        # Class is defined successfully
        self.assertTrue(hasattr(MyService, 'db'))
        self.assertIsInstance(MyService.db, InjectDescriptor)

    def test_inject_works_after_restart(self):
        """Inject works correctly after stop/start"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        class MyService:
            db = KotInjection.inject[Database]

        service1 = MyService()
        db1 = service1.db
        self.assertIsInstance(db1, Database)

        KotInjection.stop()
        KotInjection.start(modules=[module])

        # Verify it works after restart with a new service instance
        service2 = MyService()
        db2 = service2.db
        self.assertIsInstance(db2, Database)

    def test_inheritance_with_inject(self):
        """Inject works with class inheritance"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())

        KotInjection.start(modules=[module])

        class BaseService:
            db = KotInjection.inject[Database]

        class DerivedService(BaseService):
            cache = KotInjection.inject[CacheService]

        service = DerivedService()
        self.assertIsInstance(service.db, Database)
        self.assertIsInstance(service.cache, CacheService)


if __name__ == '__main__':
    unittest.main()
