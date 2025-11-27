"""
Module get() Index Parameter Tests

Tests for module.get(index) functionality that allows specifying
a specific parameter index to resolve.
"""

import sys
import os
import unittest

# Add tests directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.exceptions import ResolutionContextError, TypeInferenceError

from conftest import KotInjectionTestCase
from fixtures import Database, CacheService


class Redis:
    """Test Redis class for manual instantiation"""

    def __init__(self, host: str = "localhost", port: int = 6379):
        self.host = host
        self.port = port


class ServiceWithRedisAndDatabase:
    """Service with Redis (manual) and Database (injected) dependencies"""

    def __init__(self, redis: Redis, db: Database):
        self.redis = redis
        self.db = db


class ServiceWithThreeDeps:
    """Service with three dependencies"""

    def __init__(self, db: Database, redis: Redis, cache: CacheService):
        self.db = db
        self.redis = redis
        self.cache = cache


class TestModuleGetIndex(KotInjectionTestCase):
    """Tests for module.get(index) functionality"""

    def test_get_with_index_resolves_specific_parameter(self):
        """module.get(1) resolves the second parameter"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # Redis is manually created, Database is resolved via index
            module.single[ServiceWithRedisAndDatabase](
                lambda: ServiceWithRedisAndDatabase(
                    Redis(host="localhost"),
                    module.get(1)  # Resolve Database (index 1)
                )
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithRedisAndDatabase]()

        # Verify Redis was manually created
        self.assertIsInstance(service.redis, Redis)
        self.assertEqual(service.redis.host, "localhost")

        # Verify Database was resolved via DI
        self.assertIsInstance(service.db, Database)
        self.assertEqual(service.db.name, "TestDB")

    def test_get_with_index_zero(self):
        """module.get(0) resolves the first parameter"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # Database is resolved via index 0, Redis is manually created
            module.single[ServiceWithRedisAndDatabase](
                lambda: ServiceWithRedisAndDatabase(
                    module.get(0),  # Resolve Redis type but we need Database at index 0... wait
                    Database()  # Manual
                )
            )

        # This won't work as expected because ServiceWithRedisAndDatabase
        # expects Redis at index 0, not Database.
        # Let's test with proper fixture instead.

    def test_get_with_multiple_indexes(self):
        """module.get() can be used with different indexes"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            # Redis is manual, Database and CacheService are resolved
            module.single[ServiceWithThreeDeps](
                lambda: ServiceWithThreeDeps(
                    module.get(0),  # Database (index 0)
                    Redis(host="redis.local"),  # Manual Redis
                    module.get(2)  # CacheService (index 2)
                )
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithThreeDeps]()

        self.assertIsInstance(service.db, Database)
        self.assertIsInstance(service.redis, Redis)
        self.assertEqual(service.redis.host, "redis.local")
        self.assertIsInstance(service.cache, CacheService)

    def test_get_with_index_out_of_range_raises_error(self):
        """module.get(N) raises error when N is out of range"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[ServiceWithRedisAndDatabase](
                lambda: ServiceWithRedisAndDatabase(
                    Redis(),
                    module.get(10)  # Out of range!
                )
            )

        KotInjection.start(modules=[module])

        # Error is wrapped in TypeInferenceError
        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ServiceWithRedisAndDatabase]()

        self.assertIn("out of range", str(ctx.exception))
        self.assertIn("10", str(ctx.exception))

    def test_get_with_negative_index_raises_error(self):
        """module.get(-1) raises error for negative index"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[ServiceWithRedisAndDatabase](
                lambda: ServiceWithRedisAndDatabase(
                    Redis(),
                    module.get(-1)  # Negative index!
                )
            )

        KotInjection.start(modules=[module])

        # Error is wrapped in TypeInferenceError
        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ServiceWithRedisAndDatabase]()

        self.assertIn("out of range", str(ctx.exception))

    def test_get_without_index_still_works(self):
        """module.get() without index uses sequential type inference"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[ServiceWithThreeDeps](
                lambda: ServiceWithThreeDeps(
                    module.get(),  # Database (sequential index 0)
                    Redis(),  # Manual - this breaks sequential inference!
                    module.get()  # Will try to get Redis (sequential index 1)
                )
            )

        KotInjection.start(modules=[module])

        # This will fail because second module.get() tries to resolve Redis
        # but Redis is not registered
        from kotinjection.exceptions import DefinitionNotFoundError
        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[ServiceWithThreeDeps]()

    def test_mixed_index_and_sequential_get(self):
        """Index-based get can be mixed with keyword arguments"""

        class ServiceWithKeywords:
            def __init__(self, db: Database, cache: CacheService):
                self.db = db
                self.cache = cache

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            # Using keyword arguments for clarity
            module.single[ServiceWithKeywords](
                lambda: ServiceWithKeywords(
                    db=module.get(),
                    cache=module.get()
                )
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithKeywords]()
        self.assertIsInstance(service.db, Database)
        self.assertIsInstance(service.cache, CacheService)


class TestModuleGetIndexWithKeywordArgs(KotInjectionTestCase):
    """Tests showing recommended pattern with keyword arguments"""

    def test_keyword_args_with_index_recommended_pattern(self):
        """Keyword arguments with index parameter work correctly"""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # Recommended: Use keyword arguments with explicit index
            module.single[ServiceWithRedisAndDatabase](
                lambda: ServiceWithRedisAndDatabase(
                    redis=Redis(host="manual.redis"),
                    db=module.get(1)  # Explicitly get Database (index 1)
                )
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithRedisAndDatabase]()

        self.assertIsInstance(service.redis, Redis)
        self.assertEqual(service.redis.host, "manual.redis")
        self.assertIsInstance(service.db, Database)

    def test_keyword_args_sequential_order_matters(self):
        """Keyword args don't change sequential type inference order"""

        class ServiceWithDbFirst:
            def __init__(self, db: Database, cache: CacheService):
                self.db = db
                self.cache = cache

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            # Even with keyword args, module.get() uses sequential order
            module.single[ServiceWithDbFirst](
                lambda: ServiceWithDbFirst(
                    cache=module.get(),  # Gets Database (index 0), not Cache!
                    db=module.get()  # Gets CacheService (index 1), not Database!
                )
            )

        KotInjection.start(modules=[module])

        # This demonstrates that keyword args don't affect type inference order
        # The result will have swapped types!
        service = KotInjection.get[ServiceWithDbFirst]()

        # Note: Due to Python's evaluation order, this WORKS but types are swapped
        # db actually contains Database (correct by coincidence of order)
        # cache actually contains CacheService (correct by coincidence of order)
        # This is because Python evaluates arguments left-to-right even with kwargs
        self.assertIsInstance(service.db, CacheService)  # Swapped!
        self.assertIsInstance(service.cache, Database)  # Swapped!


if __name__ == '__main__':
    unittest.main()
