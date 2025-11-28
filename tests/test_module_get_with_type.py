"""Tests for module.get[Type]() syntax.

This module tests the explicit type resolution feature that allows
dependencies to be resolved during DryRun, avoiding issues with
third-party libraries that cannot handle DryRunPlaceholder.
"""

import unittest
from kotinjection import KotInjection, KotInjectionModule
from tests.conftest import KotInjectionTestCase


class TestModuleGetWithType(KotInjectionTestCase):
    """Tests for explicit type resolution in factories."""

    def test_get_with_type_basic(self):
        """module.get[Type]() should resolve dependency correctly."""
        class Config:
            value = "test_value"

        class Service:
            def __init__(self, config: Config):
                self.config = config

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            module.single[Service](lambda: Service(module.get[Config]()))

        KotInjection.start(modules=[module])
        service = KotInjection.get[Service]()
        self.assertIsInstance(service, Service)
        self.assertIsInstance(service.config, Config)
        self.assertEqual(service.config.value, "test_value")

    def test_get_with_type_in_dry_run(self):
        """module.get[Type]() should return actual instance during DryRun."""
        class Config:
            DATABASE_URI = "postgresql://localhost/db"

        class Engine:
            pass

        def create_engine(url: str) -> Engine:
            """Simulates third-party library that requires actual string."""
            if not isinstance(url, str):
                raise TypeError(f"url must be string, got {type(url)}")
            return Engine()

        class DatabaseClient:
            def __init__(self, config: Config):
                # This would fail during DryRun if config was DryRunPlaceholder
                self.engine = create_engine(config.DATABASE_URI)

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            # Use get[Config]() to avoid DryRun error
            module.single[DatabaseClient](
                lambda: DatabaseClient(module.get[Config]())
            )

        # Should not raise - get[Type]() resolves actual instance
        KotInjection.start(modules=[module])
        db = KotInjection.get[DatabaseClient]()
        self.assertIsInstance(db, DatabaseClient)
        self.assertIsInstance(db.engine, Engine)

    def test_get_with_type_eager_init(self):
        """module.get[Type]() should work with created_at_start=True."""
        class Config:
            DATABASE_URI = "postgresql://localhost/db"

        class Engine:
            pass

        def create_engine(url: str) -> Engine:
            if not isinstance(url, str):
                raise TypeError(f"url must be string, got {type(url)}")
            return Engine()

        class DatabaseClient:
            def __init__(self, config: Config):
                self.engine = create_engine(config.DATABASE_URI)

        module = KotInjectionModule(created_at_start=True)
        with module:
            module.single[Config](lambda: Config())
            module.single[DatabaseClient](
                lambda: DatabaseClient(module.get[Config]())
            )

        # Should not raise during eager initialization
        KotInjection.start(modules=[module])
        db = KotInjection.get[DatabaseClient]()
        self.assertIsInstance(db, DatabaseClient)
        self.assertIsInstance(db.engine, Engine)

    def test_mixed_get_styles(self):
        """Mix of get[Type]() and get() should work correctly."""
        class Config:
            value = "test"

        class Database:
            pass

        class Service:
            def __init__(self, config: Config, db: Database):
                # Use config immediately (needs actual instance)
                self.config_value = config.value
                self.db = db

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            module.single[Database](lambda: Database())
            module.single[Service](lambda: Service(
                module.get[Config](),  # Explicit type
                module.get()           # Type inference
            ))

        KotInjection.start(modules=[module])
        service = KotInjection.get[Service]()
        self.assertEqual(service.config_value, "test")
        self.assertIsInstance(service.db, Database)

    def test_get_with_type_index_increment(self):
        """get[Type]() should increment index for consistency with get()."""
        class A:
            pass

        class B:
            pass

        class C:
            pass

        class Service:
            def __init__(self, a: A, b: B, c: C):
                self.a = a
                self.b = b
                self.c = c

        module = KotInjectionModule()
        with module:
            module.single[A](lambda: A())
            module.single[B](lambda: B())
            module.single[C](lambda: C())
            module.single[Service](lambda: Service(
                module.get[A](),  # index=0
                module.get(),     # index=1 → B
                module.get[C]()   # index=2
            ))

        KotInjection.start(modules=[module])
        service = KotInjection.get[Service]()
        self.assertIsInstance(service.a, A)
        self.assertIsInstance(service.b, B)
        self.assertIsInstance(service.c, C)

    def test_abstract_interface_with_typed_get(self):
        """Abstract interface with get[Type]() should work."""
        from abc import ABC, abstractmethod

        class Config:
            DATABASE_URI = "postgresql://localhost/db"

        class IDatabaseClient(ABC):
            @abstractmethod
            def query(self):
                pass

        class Engine:
            pass

        def create_engine(url: str) -> Engine:
            if not isinstance(url, str):
                raise TypeError(f"url must be string")
            return Engine()

        class DatabaseClient(IDatabaseClient):
            def __init__(self, config: Config):
                self.engine = create_engine(config.DATABASE_URI)

            def query(self):
                return "result"

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            module.single[IDatabaseClient](
                lambda: DatabaseClient(module.get[Config]())
            )

        KotInjection.start(modules=[module])
        db = KotInjection.get[IDatabaseClient]()
        self.assertIsInstance(db, DatabaseClient)
        self.assertEqual(db.query(), "result")

    def test_multiple_typed_gets(self):
        """Multiple get[Type]() calls should work correctly."""
        class ConfigA:
            value = "A"

        class ConfigB:
            value = "B"

        class Service:
            def __init__(self, a: ConfigA, b: ConfigB):
                self.a_value = a.value
                self.b_value = b.value

        module = KotInjectionModule()
        with module:
            module.single[ConfigA](lambda: ConfigA())
            module.single[ConfigB](lambda: ConfigB())
            module.single[Service](lambda: Service(
                module.get[ConfigA](),
                module.get[ConfigB]()
            ))

        KotInjection.start(modules=[module])
        service = KotInjection.get[Service]()
        self.assertEqual(service.a_value, "A")
        self.assertEqual(service.b_value, "B")

    def test_get_with_type_factory_scope(self):
        """get[Type]() should work with factory scope."""
        class Config:
            DATABASE_URI = "postgresql://localhost/db"

        class Engine:
            pass

        call_count = 0

        def create_engine(url: str) -> Engine:
            nonlocal call_count
            call_count += 1
            if not isinstance(url, str):
                raise TypeError(f"url must be string")
            return Engine()

        class DatabaseClient:
            def __init__(self, config: Config):
                self.engine = create_engine(config.DATABASE_URI)

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            module.factory[DatabaseClient](
                lambda: DatabaseClient(module.get[Config]())
            )

        KotInjection.start(modules=[module])

        # Each get should create new instance
        db1 = KotInjection.get[DatabaseClient]()
        db2 = KotInjection.get[DatabaseClient]()
        self.assertIsNot(db1, db2)
        # Factory is called at least twice (may have DryRun calls too)
        self.assertGreaterEqual(call_count, 2)


class TestModuleGetWithTypeErrors(KotInjectionTestCase):
    """Tests for error handling in get[Type]()."""

    def test_get_with_type_outside_factory_raises(self):
        """get[Type]() outside factory should raise ResolutionContextError."""
        from kotinjection.exceptions import ResolutionContextError

        module = KotInjectionModule()
        with module:
            module.single[str](lambda: "test")

        KotInjection.start(modules=[module])

        # Calling get[Type]() directly (not in factory) should raise
        with self.assertRaises(ResolutionContextError):
            module.get[str]()


if __name__ == '__main__':
    unittest.main()
