"""
Eager Initialization Tests

Tests for the created_at_start feature that enables eager initialization
of singleton dependencies at start() time.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.core import KotInjectionCore
from conftest import KotInjectionTestCase


class TestDefinitionLevelEagerInit(KotInjectionTestCase):
    """Tests for definition-level created_at_start=True."""

    def test_eager_init_at_definition_level(self):
        """Singleton with created_at_start=True is initialized at start()."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database(), created_at_start=True)

        # Before start, no calls
        self.assertEqual(call_count, 0)

        # start() triggers eager initialization
        KotInjection.start(modules=[module])

        # dry-run + actual = 2 calls
        self.assertEqual(call_count, 2)

        # get() returns cached instance (no additional calls)
        db = KotInjection.get[Database]()
        self.assertEqual(call_count, 2)
        self.assertIsInstance(db, Database)

    def test_lazy_init_by_default(self):
        """Singleton without created_at_start is lazy initialized."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())  # No created_at_start

        KotInjection.start(modules=[module])

        # No initialization at start time
        self.assertEqual(call_count, 0)

        # First get() triggers initialization
        db = KotInjection.get[Database]()
        self.assertEqual(call_count, 2)  # dry-run + actual
        self.assertIsInstance(db, Database)

    def test_explicit_created_at_start_false(self):
        """Explicit created_at_start=False keeps lazy initialization."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database(), created_at_start=False)

        KotInjection.start(modules=[module])

        # No initialization at start time
        self.assertEqual(call_count, 0)


class TestModuleLevelEagerInit(KotInjectionTestCase):
    """Tests for module-level created_at_start=True."""

    def test_module_level_eager_init(self):
        """Module-level created_at_start applies to all singletons."""
        db_call_count = 0
        cache_call_count = 0

        class Database:
            def __init__(self):
                nonlocal db_call_count
                db_call_count += 1

        class CacheService:
            def __init__(self):
                nonlocal cache_call_count
                cache_call_count += 1

        module = KotInjectionModule(created_at_start=True)
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())

        KotInjection.start(modules=[module])

        # Both singletons are eagerly initialized
        self.assertEqual(db_call_count, 2)  # dry-run + actual
        self.assertEqual(cache_call_count, 2)  # dry-run + actual

    def test_module_level_default_is_lazy(self):
        """Module without created_at_start defaults to lazy."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()  # No created_at_start
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        # No initialization at start time
        self.assertEqual(call_count, 0)


class TestDefinitionOverridesModule(KotInjectionTestCase):
    """Tests for definition-level overriding module-level settings."""

    def test_definition_overrides_module_eager_to_lazy(self):
        """Definition-level created_at_start=False overrides module-level True."""
        eager_call_count = 0
        lazy_call_count = 0

        class EagerService:
            def __init__(self):
                nonlocal eager_call_count
                eager_call_count += 1

        class LazyService:
            def __init__(self):
                nonlocal lazy_call_count
                lazy_call_count += 1

        module = KotInjectionModule(created_at_start=True)  # Module: Eager
        with module:
            module.single[EagerService](lambda: EagerService())  # Inherits: Eager
            module.single[LazyService](lambda: LazyService(), created_at_start=False)  # Override: Lazy

        KotInjection.start(modules=[module])

        # EagerService is initialized
        self.assertEqual(eager_call_count, 2)

        # LazyService is NOT initialized
        self.assertEqual(lazy_call_count, 0)

    def test_definition_overrides_module_lazy_to_eager(self):
        """Definition-level created_at_start=True overrides module-level False (default)."""
        eager_call_count = 0
        lazy_call_count = 0

        class EagerService:
            def __init__(self):
                nonlocal eager_call_count
                eager_call_count += 1

        class LazyService:
            def __init__(self):
                nonlocal lazy_call_count
                lazy_call_count += 1

        module = KotInjectionModule()  # Module: Lazy (default)
        with module:
            module.single[EagerService](lambda: EagerService(), created_at_start=True)  # Override: Eager
            module.single[LazyService](lambda: LazyService())  # Inherits: Lazy

        KotInjection.start(modules=[module])

        # EagerService is initialized
        self.assertEqual(eager_call_count, 2)

        # LazyService is NOT initialized
        self.assertEqual(lazy_call_count, 0)


class TestFactoryIgnoresCreatedAtStart(KotInjectionTestCase):
    """Tests for Factory lifecycle ignoring created_at_start."""

    def test_factory_ignores_created_at_start_definition_level(self):
        """Factory ignores created_at_start at definition level."""
        call_count = 0

        class Service:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            # Even with created_at_start=True, factory should NOT be eager
            module.factory[Service](lambda: Service(), created_at_start=True)

        KotInjection.start(modules=[module])

        # Factory is NOT initialized at start time
        self.assertEqual(call_count, 0)

        # Each get() creates a new instance
        KotInjection.get[Service]()
        self.assertEqual(call_count, 2)  # dry-run + actual

    def test_factory_ignores_created_at_start_module_level(self):
        """Factory ignores module-level created_at_start."""
        singleton_count = 0
        factory_count = 0

        class SingletonService:
            def __init__(self):
                nonlocal singleton_count
                singleton_count += 1

        class FactoryService:
            def __init__(self):
                nonlocal factory_count
                factory_count += 1

        module = KotInjectionModule(created_at_start=True)  # Module: Eager
        with module:
            module.single[SingletonService](lambda: SingletonService())
            module.factory[FactoryService](lambda: FactoryService())

        KotInjection.start(modules=[module])

        # Singleton is eagerly initialized
        self.assertEqual(singleton_count, 2)

        # Factory is NOT eagerly initialized
        self.assertEqual(factory_count, 0)


class TestEagerInitWithDependencies(KotInjectionTestCase):
    """Tests for eager initialization with dependent services."""

    def test_eager_init_resolves_dependencies(self):
        """Eager init correctly resolves dependencies."""
        db_call_count = 0
        repo_call_count = 0

        class Database:
            def __init__(self):
                nonlocal db_call_count
                db_call_count += 1

        class Repository:
            def __init__(self, db: Database):
                nonlocal repo_call_count
                repo_call_count += 1
                self.db = db

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[Repository](
                lambda: Repository(db=module.get()),
                created_at_start=True
            )

        KotInjection.start(modules=[module])

        # Repository is eagerly initialized (resolves Database as dependency)
        self.assertGreater(repo_call_count, 0)
        self.assertGreater(db_call_count, 0)

        # Get the repository
        repo = KotInjection.get[Repository]()
        self.assertIsInstance(repo, Repository)
        self.assertIsInstance(repo.db, Database)


class TestEagerInitWithIsolatedContainer(unittest.TestCase):
    """Tests for eager initialization with isolated containers."""

    def test_isolated_container_eager_init(self):
        """Isolated container respects created_at_start."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database(), created_at_start=True)

        # Create isolated container
        app = KotInjectionCore(modules=[module])

        # Singleton is eagerly initialized
        self.assertEqual(call_count, 2)

        # get() returns cached instance
        db = app.get[Database]()
        self.assertEqual(call_count, 2)
        self.assertIsInstance(db, Database)

        app.close()

    def test_isolated_container_load_modules_eager_init(self):
        """load_modules triggers eager initialization."""
        call_count = 0

        class Database:
            def __init__(self):
                nonlocal call_count
                call_count += 1

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database(), created_at_start=True)

        # Create empty container first
        app = KotInjectionCore()
        self.assertEqual(call_count, 0)

        # load_modules triggers eager initialization
        app.load_modules([module])
        self.assertEqual(call_count, 2)

        app.close()


class TestMultipleModulesEagerInit(KotInjectionTestCase):
    """Tests for eager initialization with multiple modules."""

    def test_multiple_modules_mixed_eager_lazy(self):
        """Multiple modules with different eager/lazy settings."""
        eager_count = 0
        lazy_count = 0

        class EagerService:
            def __init__(self):
                nonlocal eager_count
                eager_count += 1

        class LazyService:
            def __init__(self):
                nonlocal lazy_count
                lazy_count += 1

        eager_module = KotInjectionModule(created_at_start=True)
        with eager_module:
            eager_module.single[EagerService](lambda: EagerService())

        lazy_module = KotInjectionModule()
        with lazy_module:
            lazy_module.single[LazyService](lambda: LazyService())

        KotInjection.start(modules=[eager_module, lazy_module])

        # EagerService is initialized
        self.assertEqual(eager_count, 2)

        # LazyService is NOT initialized
        self.assertEqual(lazy_count, 0)


if __name__ == '__main__':
    unittest.main()
