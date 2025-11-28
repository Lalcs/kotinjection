"""
Tests for module.single[Interface](ImplementationType) syntax.

This tests the ability to register dependencies by passing a type directly
instead of a factory function, enabling automatic dependency resolution.
"""

import sys
import os
import unittest
from abc import ABC, abstractmethod

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import (
    KotInjectionModule,
    KotInjection,
)

from conftest import KotInjectionTestCase


# Test classes without dependencies
class Database:
    def __init__(self):
        self.name = "TestDB"


class CacheService:
    def __init__(self):
        self.cache = {}


# Test classes with dependencies
class UserRepository:
    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


class RequestHandler:
    def __init__(self, repo: UserRepository):
        self.repo = repo


# Interface/Implementation pattern
class IDatabase(ABC):
    @abstractmethod
    def connect(self) -> str:
        pass


class PostgresDatabase(IDatabase):
    def __init__(self):
        self.name = "PostgreSQL"

    def connect(self) -> str:
        return f"Connected to {self.name}"


class MySQLDatabase(IDatabase):
    def __init__(self):
        self.name = "MySQL"

    def connect(self) -> str:
        return f"Connected to {self.name}"


class TestSingleTypeRegistration(KotInjectionTestCase):
    """Tests for module.single[Type](ImplType) syntax."""

    def test_single_type_without_dependencies(self):
        """Can register a type without dependencies."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database)

        KotInjection.start(modules=[module])

        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)
        self.assertEqual(db.name, "TestDB")

    def test_single_type_returns_same_instance(self):
        """Singleton type registration returns same instance."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database)

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[Database]()
        db2 = KotInjection.get[Database]()

        self.assertIs(db1, db2)

    def test_single_type_with_dependencies(self):
        """Can register a type with dependencies that are auto-resolved."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database)
            module.single[CacheService](CacheService)
            module.single[UserRepository](UserRepository)

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo, UserRepository)
        self.assertIsInstance(repo.db, Database)
        self.assertIsInstance(repo.cache, CacheService)

    def test_single_type_with_nested_dependencies(self):
        """Can resolve nested dependency chains."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database)
            module.single[CacheService](CacheService)
            module.single[UserRepository](UserRepository)
            module.single[RequestHandler](RequestHandler)

        KotInjection.start(modules=[module])

        handler = KotInjection.get[RequestHandler]()
        self.assertIsInstance(handler, RequestHandler)
        self.assertIsInstance(handler.repo, UserRepository)
        self.assertIsInstance(handler.repo.db, Database)

    def test_single_interface_with_implementation(self):
        """Can register interface with implementation type."""
        module = KotInjectionModule()
        with module:
            module.single[IDatabase](PostgresDatabase)

        KotInjection.start(modules=[module])

        db = KotInjection.get[IDatabase]()
        self.assertIsInstance(db, PostgresDatabase)
        self.assertEqual(db.connect(), "Connected to PostgreSQL")

    def test_single_type_with_created_at_start(self):
        """Can use created_at_start with type registration."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database, created_at_start=True)

        KotInjection.start(modules=[module])

        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)


class TestFactoryTypeRegistration(KotInjectionTestCase):
    """Tests for module.factory[Type](ImplType) syntax."""

    def test_factory_type_without_dependencies(self):
        """Can register factory type without dependencies."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](Database)

        KotInjection.start(modules=[module])

        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)

    def test_factory_type_returns_different_instances(self):
        """Factory type registration returns different instances."""
        module = KotInjectionModule()
        with module:
            module.factory[Database](Database)

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[Database]()
        db2 = KotInjection.get[Database]()

        self.assertIsNot(db1, db2)

    def test_factory_type_with_dependencies(self):
        """Factory type can resolve dependencies."""
        module = KotInjectionModule()
        with module:
            module.single[Database](Database)
            module.single[CacheService](CacheService)
            module.factory[UserRepository](UserRepository)

        KotInjection.start(modules=[module])

        repo1 = KotInjection.get[UserRepository]()
        repo2 = KotInjection.get[UserRepository]()

        # Different instances
        self.assertIsNot(repo1, repo2)
        # But same singleton dependencies
        self.assertIs(repo1.db, repo2.db)
        self.assertIs(repo1.cache, repo2.cache)


class TestMixedRegistration(KotInjectionTestCase):
    """Tests for mixing type and lambda registration."""

    def test_mixed_type_and_lambda_registration(self):
        """Can mix type registration with lambda registration."""
        module = KotInjectionModule()
        with module:
            # Lambda style
            module.single[Database](lambda: Database())
            # Type style
            module.single[CacheService](CacheService)
            # Type style with dependencies
            module.single[UserRepository](UserRepository)

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo.db, Database)
        self.assertIsInstance(repo.cache, CacheService)


if __name__ == '__main__':
    unittest.main()
