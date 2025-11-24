"""
Thread Safety Tests

Tests for thread-safe operation of KotInjection using ContextVar.
Verifies that multiple threads can resolve dependencies independently
without interference.
"""

import unittest
import threading
import concurrent.futures
from typing import List

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.core import KotInjectionCore


class Database:
    """Simple database class for testing."""

    def __init__(self):
        self.thread_id = threading.current_thread().ident


class UserRepository:
    """Repository with database dependency."""

    def __init__(self, db: Database):
        self.db = db
        self.thread_id = threading.current_thread().ident


class TestThreadSafetyContextVar(unittest.TestCase):
    """Test ContextVar isolation between threads."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_contextvar_isolation_multiple_threads(self):
        """Multiple threads have isolated resolution contexts."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())
            module.factory[UserRepository](
                lambda: UserRepository(db=module.get())
            )

        KotInjection.start(modules=[module])

        results: List[int] = []
        errors: List[Exception] = []

        def resolve_in_thread():
            try:
                repo = KotInjection.get[UserRepository]()
                results.append(repo.thread_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=resolve_in_thread) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

    def test_contextvar_isolation_with_concurrent_futures(self):
        """Thread pool executor maintains context isolation."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        KotInjection.start(modules=[module])

        def resolve():
            db = KotInjection.get[Database]()
            return db.thread_id

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(resolve) for _ in range(20)]
            results = [f.result() for f in futures]

        self.assertEqual(len(results), 20)


class TestThreadSafetySingleton(unittest.TestCase):
    """Test singleton behavior in multi-threaded environment."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_singleton_same_instance_across_threads(self):
        """Singleton returns same instance from all threads."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        results: List[Database] = []
        lock = threading.Lock()

        def resolve_in_thread():
            db = KotInjection.get[Database]()
            with lock:
                results.append(db)

        threads = [threading.Thread(target=resolve_in_thread) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(results), 10)
        first = results[0]
        for db in results[1:]:
            self.assertIs(db, first, "Singleton should return same instance")


class TestThreadSafetyIsolatedContainer(unittest.TestCase):
    """Test isolated container thread safety."""

    def test_isolated_container_thread_safety(self):
        """Isolated container works correctly with multiple threads."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])

        results: List[int] = []
        errors: List[Exception] = []
        lock = threading.Lock()

        def resolve_in_thread():
            try:
                db = app.get[Database]()
                with lock:
                    results.append(db.thread_id)
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=resolve_in_thread) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        app.close()

        self.assertEqual(len(errors), 0, f"Errors occurred: {errors}")
        self.assertEqual(len(results), 10)

    def test_multiple_isolated_containers_thread_safety(self):
        """Multiple isolated containers can be used from different threads."""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        app1 = KotInjectionCore(modules=[module1])
        app2 = KotInjectionCore(modules=[module2])

        results1: List[Database] = []
        results2: List[Database] = []
        lock = threading.Lock()

        def resolve_from_app1():
            db = app1.get[Database]()
            with lock:
                results1.append(db)

        def resolve_from_app2():
            db = app2.get[Database]()
            with lock:
                results2.append(db)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=resolve_from_app1))
            threads.append(threading.Thread(target=resolve_from_app2))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        app1.close()
        app2.close()

        self.assertEqual(len(results1), 5)
        self.assertEqual(len(results2), 5)
        self.assertIsNot(results1[0], results2[0], "Different containers should have different singletons")


class TestThreadSafetyClosedContainer(unittest.TestCase):
    """Test closed container behavior in multi-threaded environment."""

    def test_closed_container_get_raises_error(self):
        """Closed container raises error when accessed from any thread."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])
        app.close()

        errors: List[Exception] = []
        lock = threading.Lock()

        def try_resolve():
            try:
                app.get[Database]()
            except Exception as e:
                with lock:
                    errors.append(e)

        threads = [threading.Thread(target=try_resolve) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 5)
        from kotinjection.exceptions import ContainerClosedError
        for e in errors:
            self.assertIsInstance(e, ContainerClosedError)


if __name__ == '__main__':
    unittest.main()
