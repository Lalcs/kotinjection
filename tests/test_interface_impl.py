"""
Interface and Implementation Separation Tests

Tests for registering interfaces and resolving their implementations.
This enables Clean Architecture patterns where code depends on abstractions.
"""

import sys
import os
import unittest
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule, KotInjectionCore
from conftest import KotInjectionTestCase


class IDatabase(ABC):
    """Abstract database interface."""

    @abstractmethod
    def connect(self) -> str:
        pass


class IRepository(ABC):
    """Abstract repository interface."""

    @abstractmethod
    def get_data(self) -> str:
        pass


class IService(ABC):
    """Abstract service interface."""

    @abstractmethod
    def process(self) -> str:
        pass


class PostgresDatabase(IDatabase):
    """PostgreSQL implementation of IDatabase."""

    def connect(self) -> str:
        return "Connected to PostgreSQL"


class MySQLDatabase(IDatabase):
    """MySQL implementation of IDatabase."""

    def connect(self) -> str:
        return "Connected to MySQL"


class UserRepository(IRepository):
    """Implementation of IRepository with database dependency."""

    def __init__(self, db: IDatabase):
        self.db = db

    def get_data(self) -> str:
        return f"Repository using: {self.db.connect()}"


class UserService(IService):
    """Implementation of IService with repository dependency."""

    def __init__(self, repo: IRepository):
        self.repo = repo

    def process(self) -> str:
        return f"Service processing: {self.repo.get_data()}"


class TestInterfaceImplementation(KotInjectionTestCase):
    """Tests for interface-implementation separation."""

    def test_interface_with_implementation(self):
        """Interface registered with concrete implementation resolves correctly."""
        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: PostgresDatabase())

        KotInjection.start(modules=[module])

        db = KotInjection.get[IDatabase]()
        self.assertIsInstance(db, PostgresDatabase)
        self.assertEqual(db.connect(), "Connected to PostgreSQL")

    def test_interface_chain_with_type_inference(self):
        """Chain of interfaces with type inference works correctly."""
        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: PostgresDatabase())
            module.single[IRepository](lambda: UserRepository(db=module.get()))

        KotInjection.start(modules=[module])

        repo = KotInjection.get[IRepository]()
        self.assertIsInstance(repo, UserRepository)
        self.assertIsInstance(repo.db, PostgresDatabase)
        self.assertEqual(repo.get_data(), "Repository using: Connected to PostgreSQL")

    def test_multi_level_interface_chain(self):
        """Multiple levels of interface dependencies resolve correctly."""
        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: PostgresDatabase())
            module.single[IRepository](lambda: UserRepository(db=module.get()))
            module.single[IService](lambda: UserService(repo=module.get()))

        KotInjection.start(modules=[module])

        service = KotInjection.get[IService]()
        self.assertIsInstance(service, UserService)
        self.assertIsInstance(service.repo, UserRepository)
        self.assertIsInstance(service.repo.db, PostgresDatabase)
        self.assertEqual(
            service.process(),
            "Service processing: Repository using: Connected to PostgreSQL"
        )

    def test_swap_implementation(self):
        """Different implementations can be swapped for the same interface."""
        # First configuration: PostgreSQL
        module1 = KotInjectionModule()
        with module1:
            module1.single[IDatabase](lambda: PostgresDatabase())

        KotInjection.start(modules=[module1])
        db1 = KotInjection.get[IDatabase]()
        self.assertIsInstance(db1, PostgresDatabase)
        KotInjection.stop()

        # Second configuration: MySQL
        module2 = KotInjectionModule()
        with module2:
            module2.single[IDatabase](lambda: MySQLDatabase())

        KotInjection.start(modules=[module2])
        db2 = KotInjection.get[IDatabase]()
        self.assertIsInstance(db2, MySQLDatabase)

    def test_factory_interface(self):
        """Factory lifecycle works with interface registration."""
        call_count = 0

        class CountingDatabase(IDatabase):
            def __init__(self):
                nonlocal call_count
                call_count += 1
                self.id = call_count

            def connect(self) -> str:
                return f"DB instance {self.id}"

        module = KotInjectionModule()
        with module:
            module.factory[IDatabase](lambda: CountingDatabase())

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[IDatabase]()
        db2 = KotInjection.get[IDatabase]()

        # Each get() returns a new instance (factory behavior)
        self.assertNotEqual(db1.id, db2.id)
        # Note: Factory always runs dry-run to support different implementations
        # First resolution: 1 dry-run + 1 actual = 2 calls
        # Second resolution: 1 dry-run + 1 actual = 2 calls
        # Total: 4 calls
        self.assertEqual(call_count, 4)

    def test_singleton_interface(self):
        """Singleton lifecycle works with interface registration."""
        call_count = 0

        class CountingDatabase(IDatabase):
            def __init__(self):
                nonlocal call_count
                call_count += 1
                self.id = call_count

            def connect(self) -> str:
                return f"DB instance {self.id}"

        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: CountingDatabase())

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[IDatabase]()
        db2 = KotInjection.get[IDatabase]()

        # Same instance returned (singleton behavior)
        self.assertEqual(db1.id, db2.id)
        # Note: First resolution includes 1 dry-run + 1 actual = 2 calls
        # Second resolution uses cached instance = 0 calls
        # Total: 2 calls
        self.assertEqual(call_count, 2)


class TestFactoryWithDifferentImplementations(KotInjectionTestCase):
    """Tests for Factory returning different implementations."""

    def test_factory_returns_different_implementations_based_on_condition(self):
        """Factory can return different implementations based on runtime condition."""
        call_counter = [0]  # Use list to allow modification in nested function

        class DatabaseA(IDatabase):
            def __init__(self):
                pass

            def connect(self) -> str:
                return "DatabaseA"

        class DatabaseB(IDatabase):
            def __init__(self):
                pass

            def connect(self) -> str:
                return "DatabaseB"

        def create_database():
            call_counter[0] += 1
            if call_counter[0] % 2 == 1:
                return DatabaseA()
            else:
                return DatabaseB()

        module = KotInjectionModule()
        with module:
            module.factory[IDatabase](create_database)

        KotInjection.start(modules=[module])

        # First call: returns DatabaseA (call 1 for dry-run, call 2 for actual)
        # Due to dry-run, actual call counter is 2, so DatabaseB is returned for actual
        # But the next dry-run will be call 3, so DatabaseA for dry-run, call 4 for actual = DatabaseB
        db1 = KotInjection.get[IDatabase]()
        db2 = KotInjection.get[IDatabase]()

        # Both should be valid IDatabase implementations
        self.assertIsInstance(db1, IDatabase)
        self.assertIsInstance(db2, IDatabase)

    def test_factory_with_same_parameter_signatures(self):
        """Factory returning different implementations must have same constructor signature."""
        # Note: When Factory returns different implementations, they MUST have
        # the same constructor parameter types. This is because dry-run determines
        # the parameter types, and the actual call uses those types.

        class ServiceImplA(IService):
            def __init__(self, db: IDatabase):
                self.db = db

            def process(self) -> str:
                return f"ServiceImplA with {self.db.connect()}"

        class ServiceImplB(IService):
            def __init__(self, db: IDatabase):
                self.db = db

            def process(self) -> str:
                return f"ServiceImplB with {self.db.connect()}"

        call_counter = [0]

        def create_service():
            call_counter[0] += 1
            # Both implementations have the same signature: (db: IDatabase)
            if call_counter[0] % 2 == 1:
                return ServiceImplA(db=module.get())
            else:
                return ServiceImplB(db=module.get())

        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: PostgresDatabase())
            module.factory[IService](create_service)

        KotInjection.start(modules=[module])

        # Both resolutions work because signatures match
        service1 = KotInjection.get[IService]()
        service2 = KotInjection.get[IService]()

        # Both should be valid IService implementations
        self.assertIsInstance(service1, IService)
        self.assertIsInstance(service2, IService)


class TestInterfaceWithIsolatedContainer(unittest.TestCase):
    """Tests for interface-implementation with isolated containers."""

    def test_isolated_container_with_interface(self):
        """Isolated container works with interface registration."""
        module = KotInjectionModule()
        with module:
            module.single[IDatabase](lambda: PostgresDatabase())
            module.single[IRepository](lambda: UserRepository(db=module.get()))

        app = KotInjectionCore()
        app.load_modules([module])

        repo = app.get[IRepository]()
        self.assertIsInstance(repo, UserRepository)
        self.assertIsInstance(repo.db, PostgresDatabase)

        app.close()

    def test_different_implementations_per_container(self):
        """Different isolated containers can have different implementations."""
        postgres_module = KotInjectionModule()
        with postgres_module:
            postgres_module.single[IDatabase](lambda: PostgresDatabase())

        mysql_module = KotInjectionModule()
        with mysql_module:
            mysql_module.single[IDatabase](lambda: MySQLDatabase())

        app1 = KotInjectionCore()
        app1.load_modules([postgres_module])

        app2 = KotInjectionCore()
        app2.load_modules([mysql_module])

        db1 = app1.get[IDatabase]()
        db2 = app2.get[IDatabase]()

        self.assertIsInstance(db1, PostgresDatabase)
        self.assertIsInstance(db2, MySQLDatabase)

        app1.close()
        app2.close()


class TestDryRunPlaceholder(unittest.TestCase):
    """Tests for DryRunPlaceholder behavior."""

    def test_placeholder_accepts_any_method(self):
        """DryRunPlaceholder accepts any method call."""
        from kotinjection.dry_run_placeholder import DryRunPlaceholder

        placeholder = DryRunPlaceholder()

        # Should not raise
        result = placeholder.any_method()
        self.assertIsInstance(result, DryRunPlaceholder)

        result = placeholder.chain().another().method()
        self.assertIsInstance(result, DryRunPlaceholder)

    def test_placeholder_accepts_any_attribute(self):
        """DryRunPlaceholder accepts any attribute access."""
        from kotinjection.dry_run_placeholder import DryRunPlaceholder

        placeholder = DryRunPlaceholder()

        # Should not raise
        result = placeholder.any_attribute
        self.assertIsInstance(result, DryRunPlaceholder)

    def test_placeholder_is_truthy(self):
        """DryRunPlaceholder evaluates to True in boolean context."""
        from kotinjection.dry_run_placeholder import DryRunPlaceholder

        placeholder = DryRunPlaceholder()
        self.assertTrue(placeholder)


if __name__ == '__main__':
    unittest.main()
