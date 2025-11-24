"""
Performance Tests

Tests for performance characteristics of KotInjection.
Verifies that the library performs well under load.
"""

import unittest
import time
from typing import List

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.core import KotInjectionCore


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


class TestLargeModuleLoading(unittest.TestCase):
    """Test performance with large numbers of definitions."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_load_many_definitions(self):
        """Can load 100+ definitions efficiently."""
        module = KotInjectionModule()

        # Create 100 unique classes dynamically
        classes = []
        for i in range(100):
            cls = type(f"Service{i}", (), {"__init__": lambda self: None})
            classes.append(cls)

        with module:
            for cls in classes:
                module.single[cls](lambda c=cls: c())

        start = time.perf_counter()
        KotInjection.start(modules=[module])
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0, "Loading 100 definitions should be fast")

    def test_load_many_modules(self):
        """Can load many modules efficiently."""
        modules: List[KotInjectionModule] = []

        for i in range(50):
            module = KotInjectionModule()
            cls = type(f"ModuleService{i}", (), {"__init__": lambda self: None})
            with module:
                module.single[cls](lambda c=cls: c())
            modules.append(module)

        start = time.perf_counter()
        KotInjection.start(modules=modules)
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0, "Loading 50 modules should be fast")


class TestResolutionPerformance(unittest.TestCase):
    """Test dependency resolution performance."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_singleton_resolution_speed(self):
        """Singleton resolution is fast after first access."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        # First resolution (creates instance)
        _ = KotInjection.get[Database]()

        # Time subsequent resolutions
        start = time.perf_counter()
        for _ in range(1000):
            _ = KotInjection.get[Database]()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 0.1, "1000 singleton lookups should be very fast")

    def test_factory_resolution_speed(self):
        """Factory resolution is reasonably fast."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        KotInjection.start(modules=[module])

        start = time.perf_counter()
        for _ in range(1000):
            _ = KotInjection.get[Database]()
        elapsed = time.perf_counter() - start

        self.assertLess(elapsed, 1.0, "1000 factory resolutions should be reasonably fast")


class TestDeepNestingPerformance(unittest.TestCase):
    """Test performance with deeply nested dependencies."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_deep_nesting_resolution(self):
        """Deep dependency chains resolve efficiently."""

        class Level1:
            pass

        class Level2:
            def __init__(self, l1: Level1):
                self.l1 = l1

        class Level3:
            def __init__(self, l2: Level2):
                self.l2 = l2

        class Level4:
            def __init__(self, l3: Level3):
                self.l3 = l3

        class Level5:
            def __init__(self, l4: Level4):
                self.l4 = l4

        module = KotInjectionModule()
        with module:
            module.single[Level1](lambda: Level1())
            module.single[Level2](lambda: Level2(l1=module.get()))
            module.single[Level3](lambda: Level3(l2=module.get()))
            module.single[Level4](lambda: Level4(l3=module.get()))
            module.single[Level5](lambda: Level5(l4=module.get()))

        KotInjection.start(modules=[module])

        start = time.perf_counter()
        l5 = KotInjection.get[Level5]()
        elapsed = time.perf_counter() - start

        self.assertIsNotNone(l5.l4.l3.l2.l1)
        self.assertLess(elapsed, 0.1, "5-level deep resolution should be fast")


class TestIsolatedContainerPerformance(unittest.TestCase):
    """Test performance of isolated containers."""

    def test_create_many_isolated_containers(self):
        """Can create many isolated containers efficiently."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        containers: List[KotInjectionCore] = []

        start = time.perf_counter()
        for _ in range(100):
            app = KotInjectionCore(modules=[module])
            containers.append(app)
        elapsed = time.perf_counter() - start

        # Cleanup
        for app in containers:
            app.close()

        self.assertLess(elapsed, 1.0, "Creating 100 containers should be fast")

    def test_isolated_container_resolution_speed(self):
        """Isolated container resolution is as fast as global."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])

        # First resolution
        _ = app.get[Database]()

        # Time subsequent resolutions
        start = time.perf_counter()
        for _ in range(1000):
            _ = app.get[Database]()
        elapsed = time.perf_counter() - start

        app.close()

        self.assertLess(elapsed, 0.1, "1000 isolated singleton lookups should be very fast")


class TestMemoryEfficiency(unittest.TestCase):
    """Test memory efficiency (basic checks)."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_unload_releases_definitions(self):
        """Unloading modules releases their definitions."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        # Access to create singleton
        db1 = KotInjection.get[Database]()

        # Unload
        KotInjection.unload_modules([module])

        # Module can be reloaded with new instances
        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        KotInjection.load_modules([module2])

        db2 = KotInjection.get[Database]()

        # Different instances
        self.assertIsNot(db1, db2)


if __name__ == '__main__':
    unittest.main()
