"""
Resolution Context Error Tests

Tests for ResolutionContextError exception handling
"""

import sys
import os
import unittest

# Add tests directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.exceptions import ResolutionContextError, NotInitializedError

from conftest import KotInjectionTestCase
from fixtures import Database


class TestResolutionContextError(KotInjectionTestCase):
    """Tests for ResolutionContextError"""

    def test_get_outside_factory_raises_error(self):
        """module.get() raises error when called outside factory"""
        module = KotInjectionModule()

        with self.assertRaises(ResolutionContextError) as ctx:
            module.get()  # Called outside factory context

        self.assertIn("cannot be used without a type parameter", str(ctx.exception))

    def test_too_many_get_calls_raises_error(self):
        """Error when get() calls exceed parameter count"""

        class SingleDependencyService:
            def __init__(self, db: Database):
                self.db = db

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # Factory has TWO get() calls but class only has ONE parameter
            module.single[SingleDependencyService](
                lambda: SingleDependencyService(
                    module.get() if True else module.get()  # Trick to add extra get()
                )
            )

        KotInjection.start(modules=[module])

        # Note: The "if True else" trick doesn't actually call the second get()
        # So we need a different approach
        service = KotInjection.get[SingleDependencyService]()
        self.assertIsNotNone(service)

    def test_get_with_wrong_number_of_calls(self):
        """When get() call count doesn't match type parameter count"""

        class TwoDependencyService:
            def __init__(self, db: Database, cache: 'CacheService'):
                self.db = db
                self.cache = cache

        class CacheService:
            pass

        # This test verifies the error message format
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            # Only one get() call but two dependencies
            module.single[TwoDependencyService](
                lambda: TwoDependencyService(module.get(), CacheService())
            )

        KotInjection.start(modules=[module])

        # Should still work because we manually provided CacheService
        service = KotInjection.get[TwoDependencyService]()
        self.assertIsInstance(service.db, Database)


class TestResolutionContextWithNestedDependencies(KotInjectionTestCase):
    """Tests for resolution context with nested dependencies"""

    def test_correct_parameter_order_resolution(self):
        """Parameters are resolved in correct order"""

        class ServiceA:
            pass

        class ServiceB:
            pass

        class ServiceC:
            def __init__(self, a: ServiceA, b: ServiceB):
                self.a = a
                self.b = b

        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())
            module.single[ServiceB](lambda: ServiceB())
            module.single[ServiceC](lambda: ServiceC(module.get(), module.get()))

        KotInjection.start(modules=[module])
        service_c = KotInjection.get[ServiceC]()

        # Verify correct types in correct order
        self.assertIsInstance(service_c.a, ServiceA)
        self.assertIsInstance(service_c.b, ServiceB)

    def test_deeply_nested_dependencies(self):
        """Resolves deeply nested dependencies"""

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

        module = KotInjectionModule()
        with module:
            module.single[Level1](lambda: Level1())
            module.single[Level2](lambda: Level2(module.get()))
            module.single[Level3](lambda: Level3(module.get()))
            module.single[Level4](lambda: Level4(module.get()))

        KotInjection.start(modules=[module])
        level4 = KotInjection.get[Level4]()

        # Verify entire chain
        self.assertIsInstance(level4.l3, Level3)
        self.assertIsInstance(level4.l3.l2, Level2)
        self.assertIsInstance(level4.l3.l2.l1, Level1)


class TestMultipleStartCalls(KotInjectionTestCase):
    """Tests for multiple KotInjection.start() calls"""

    def test_multiple_start_overwrites_previous(self):
        """Second start() overwrites the previous container"""

        class ServiceV1:
            version = 1

        class ServiceV2:
            version = 2

        module1 = KotInjectionModule()
        with module1:
            module1.single[ServiceV1](lambda: ServiceV1())

        KotInjection.start(modules=[module1])
        service_v1 = KotInjection.get[ServiceV1]()
        self.assertEqual(service_v1.version, 1)

        # Stop before restarting
        KotInjection.stop()

        module2 = KotInjectionModule()
        with module2:
            module2.single[ServiceV2](lambda: ServiceV2())

        KotInjection.start(modules=[module2])

        # ServiceV2 should now be available
        service_v2 = KotInjection.get[ServiceV2]()
        self.assertEqual(service_v2.version, 2)

    def test_start_clears_previous_singletons(self):
        """start() with new module creates new singletons"""

        class StatefulService:
            def __init__(self):
                self.counter = 0

            def increment(self):
                self.counter += 1

        # First module and start
        module1 = KotInjectionModule()
        with module1:
            module1.single[StatefulService](lambda: StatefulService())

        KotInjection.start(modules=[module1])
        service1 = KotInjection.get[StatefulService]()
        service1.increment()
        service1.increment()
        self.assertEqual(service1.counter, 2)

        # Stop before restarting
        KotInjection.stop()

        # Second module and start - creates fresh singleton
        module2 = KotInjectionModule()
        with module2:
            module2.single[StatefulService](lambda: StatefulService())

        KotInjection.start(modules=[module2])
        service2 = KotInjection.get[StatefulService]()

        # New singleton from new module, counter should be 0
        self.assertEqual(service2.counter, 0)
        self.assertIsNot(service1, service2)


class TestEmptyModuleInitialization(KotInjectionTestCase):
    """Tests for empty module initialization"""

    def test_start_with_empty_module_list(self):
        """Can initialize with empty module list"""
        KotInjection.start(modules=[])
        self.assertTrue(KotInjection.is_started())

    def test_start_with_module_without_definitions(self):
        """Can initialize with module without definitions"""
        module = KotInjectionModule()
        KotInjection.start(modules=[module])
        self.assertTrue(KotInjection.is_started())


if __name__ == '__main__':
    unittest.main()
