"""
Lifecycle Management Tests

Tests for KotInjection lifecycle management:
- Double start prevention (AlreadyStartedError)
- stop() method
- is_started() method
- KotInjectionContext interface
- GlobalContext implementation
"""

import unittest
from abc import ABC

from kotinjection import (
    AlreadyStartedError,
    DefinitionNotFoundError,
    GlobalContext,
    KotInjection,
    KotInjectionContext,
    KotInjectionCore,
    KotInjectionModule,
    NotInitializedError,
)


class Database:
    """Test dependency"""
    pass


class CacheService:
    """Test dependency"""
    pass


class TestDoubleStartPrevention(unittest.TestCase):
    """Tests for double start prevention"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()

    def test_double_start_raises_error(self):
        """Double start raises AlreadyStartedError"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        with self.assertRaises(AlreadyStartedError) as ctx:
            KotInjection.start(modules=[module])

        self.assertIn("already started", str(ctx.exception))

    def test_double_start_error_message_suggests_stop(self):
        """Error message suggests calling stop()"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        with self.assertRaises(AlreadyStartedError) as ctx:
            KotInjection.start(modules=[module])

        self.assertIn("stop()", str(ctx.exception))


class TestStopMethod(unittest.TestCase):
    """Tests for stop() method"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()

    def test_stop_allows_restart(self):
        """stop() allows clean restart"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        KotInjection.start(modules=[module1])
        db1 = KotInjection.get[Database]()

        KotInjection.stop()

        # Create new module for fresh singleton
        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        # Can start again without error
        KotInjection.start(modules=[module2])
        db2 = KotInjection.get[Database]()

        # New instance after restart (with fresh module)
        self.assertIsNotNone(db2)
        self.assertIsNot(db1, db2)

    def test_stop_is_idempotent(self):
        """stop() can be called multiple times safely"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        # Multiple stop() calls should not raise
        KotInjection.stop()
        KotInjection.stop()
        KotInjection.stop()

    def test_stop_without_start(self):
        """stop() without start is safe"""
        # Should not raise any exception
        KotInjection.stop()

    def test_stop_prevents_get(self):
        """stop() prevents further get() calls"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])
        KotInjection.stop()

        with self.assertRaises(NotInitializedError):
            KotInjection.get[Database]()

    def test_restart_with_different_modules(self):
        """Can restart with different modules"""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[CacheService](lambda: CacheService())

        # Start with module1
        KotInjection.start(modules=[module1])
        db = KotInjection.get[Database]()
        self.assertIsNotNone(db)

        KotInjection.stop()

        # Restart with module2
        KotInjection.start(modules=[module2])

        # Old type no longer available
        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[Database]()

        # New type available
        cache = KotInjection.get[CacheService]()
        self.assertIsNotNone(cache)


class TestIsStartedMethod(unittest.TestCase):
    """Tests for is_started() method"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()

    def test_is_started_before_start(self):
        """is_started() returns False before start"""
        self.assertFalse(KotInjection.is_started())

    def test_is_started_after_start(self):
        """is_started() returns True after start"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])
        self.assertTrue(KotInjection.is_started())

    def test_is_started_after_stop(self):
        """is_started() returns False after stop"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])
        KotInjection.stop()

        self.assertFalse(KotInjection.is_started())


class TestKotInjectionContextInterface(unittest.TestCase):
    """Tests for KotInjectionContext interface"""

    def test_context_is_abstract(self):
        """KotInjectionContext is an abstract class"""
        self.assertTrue(issubclass(KotInjectionContext, ABC))

    def test_context_has_required_methods(self):
        """KotInjectionContext defines required abstract methods"""
        abstract_methods = KotInjectionContext.__abstractmethods__
        expected_methods = {
            'get',
            'get_or_null',
            'start',
            'stop',
            'load_modules',
            'unload_modules',
        }
        self.assertEqual(abstract_methods, expected_methods)

    def test_global_context_implements_interface(self):
        """GlobalContext implements KotInjectionContext"""
        self.assertTrue(issubclass(GlobalContext, KotInjectionContext))


class TestGlobalContext(unittest.TestCase):
    """Tests for GlobalContext implementation"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()

    def test_global_context_is_singleton(self):
        """GlobalContext is a singleton"""
        ctx1 = GlobalContext()
        ctx2 = GlobalContext()
        self.assertIs(ctx1, ctx2)

    def test_global_context_is_singleton(self):
        """GlobalContext() returns the singleton"""
        ctx1 = GlobalContext()
        ctx2 = GlobalContext()
        ctx3 = GlobalContext()
        self.assertIs(ctx1, ctx2)
        self.assertIs(ctx2, ctx3)

    def test_global_context_get_raises_when_not_started(self):
        """GlobalContext.get() raises NotInitializedError when not started"""
        context = GlobalContext()
        with self.assertRaises(NotInitializedError):
            context.get()

    def test_global_context_get_or_null_returns_none_when_not_started(self):
        """GlobalContext.get_or_null() returns None when not started"""
        context = GlobalContext()
        self.assertIsNone(context.get_or_null())

    def test_global_context_start_returns_core(self):
        """GlobalContext.start() returns KotInjectionCore instance"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        context = GlobalContext()
        result = context.start(modules=[module])

        self.assertIsInstance(result, KotInjectionCore)

    def test_global_context_get_returns_core_after_start(self):
        """GlobalContext.get() returns the core after start"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        context = GlobalContext()
        started = context.start(modules=[module])
        retrieved = context.get()

        self.assertIs(started, retrieved)


class TestLoadModulesAfterStop(unittest.TestCase):
    """Tests for load_modules/unload_modules after stop"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Reset global container after each test"""
        KotInjection.stop()

    def test_load_modules_after_stop_raises(self):
        """load_modules() after stop raises NotInitializedError"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])
        KotInjection.stop()

        new_module = KotInjectionModule()
        with new_module:
            new_module.single[CacheService](lambda: CacheService())

        with self.assertRaises(NotInitializedError):
            KotInjection.load_modules([new_module])

    def test_unload_modules_after_stop_raises(self):
        """unload_modules() after stop raises NotInitializedError"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])
        KotInjection.stop()

        with self.assertRaises(NotInitializedError):
            KotInjection.unload_modules([module])


if __name__ == '__main__':
    unittest.main()
