"""
Forward Reference (String Annotation) Tests

Tests for handling forward references and PEP 563 (from __future__ import annotations).
"""

from __future__ import annotations  # PEP 563: All annotations become strings

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule, KotInjectionCore
from kotinjection.exceptions import TypeInferenceError

from conftest import KotInjectionTestCase


# Test Fixtures
class Database:
    """Database fixture class."""

    def __init__(self):
        self.name = "TestDB"


class CacheService:
    """Cache service fixture class."""

    def __init__(self):
        self.data = {}


class UserRepository:
    """Repository with forward reference dependency."""

    def __init__(self, db: Database):  # Forward reference due to PEP 563
        self.db = db


class ServiceWithMultipleDeps:
    """Service with multiple forward reference dependencies."""

    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


# Classes for nested dependency tests (module-level for type resolution)
class Level1:
    """Base level dependency."""
    pass


class Level2:
    """Middle level dependency."""

    def __init__(self, l1: Level1):
        self.l1 = l1


class Level3:
    """Top level dependency with nested dependencies."""

    def __init__(self, l2: Level2):
        self.l2 = l2


# Classes for index-based resolution tests
class Config:
    """Configuration class."""
    pass


class ServiceWithTwoDeps:
    """Service with two dependencies for index-based resolution."""

    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db


# Classes for quoted annotation tests (module-level)
class LocalDatabase:
    """Database for quoted annotation test."""
    pass


class LocalService:
    """Service with explicitly quoted forward reference."""

    def __init__(self, db: 'LocalDatabase'):  # Explicit quoted annotation
        self.db = db


class TestPEP563ForwardReferences(KotInjectionTestCase):
    """Tests for PEP 563 support."""

    def test_simple_forward_reference_resolves(self):
        """Forward reference in single dependency resolves correctly."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[UserRepository](lambda: UserRepository(db=module.get()))

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo, UserRepository)
        self.assertIsInstance(repo.db, Database)

    def test_multiple_forward_references_resolve(self):
        """Multiple forward references resolve correctly."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[CacheService](lambda: CacheService())
            module.single[ServiceWithMultipleDeps](
                lambda: ServiceWithMultipleDeps(db=module.get(), cache=module.get())
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithMultipleDeps]()
        self.assertIsInstance(service.db, Database)
        self.assertIsInstance(service.cache, CacheService)

    def test_factory_with_forward_reference(self):
        """Factory lifecycle works with forward references."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.factory[UserRepository](lambda: UserRepository(db=module.get()))

        KotInjection.start(modules=[module])

        repo1 = KotInjection.get[UserRepository]()
        repo2 = KotInjection.get[UserRepository]()

        self.assertIsNot(repo1, repo2)
        self.assertIs(repo1.db, repo2.db)


class TestQuotedForwardReferences(KotInjectionTestCase):
    """Tests for explicit quoted annotations (without PEP 563)."""

    def test_quoted_forward_reference_resolves(self):
        """Quoted forward reference resolves correctly."""
        # Note: Even with PEP 563, explicit quotes work the same way
        # Using module-level LocalDatabase and LocalService classes

        module = KotInjectionModule()
        with module:
            module.single[LocalDatabase](lambda: LocalDatabase())
            module.single[LocalService](lambda: LocalService(db=module.get()))

        KotInjection.start(modules=[module])

        service = KotInjection.get[LocalService]()
        self.assertIsInstance(service.db, LocalDatabase)


class TestNestedDependencies(KotInjectionTestCase):
    """Tests for nested forward references."""

    def test_three_level_dependency_chain(self):
        """Three-level dependency chain resolves correctly."""
        # Using module-level Level1, Level2, Level3 classes

        module = KotInjectionModule()
        with module:
            module.single[Level1](lambda: Level1())
            module.single[Level2](lambda: Level2(l1=module.get()))
            module.single[Level3](lambda: Level3(l2=module.get()))

        KotInjection.start(modules=[module])

        level3 = KotInjection.get[Level3]()
        self.assertIsInstance(level3.l2.l1, Level1)


class TestIsolatedContainer(unittest.TestCase):
    """Tests with isolated containers."""

    def test_isolated_container_resolves_forward_references(self):
        """Isolated container resolves forward references."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[UserRepository](lambda: UserRepository(db=module.get()))

        with KotInjectionCore(modules=[module]) as app:
            repo = app.get[UserRepository]()
            self.assertIsInstance(repo.db, Database)


class TestEagerInitializationWithForwardRef(KotInjectionTestCase):
    """Tests for eager initialization with forward references."""

    def test_eager_init_with_forward_reference(self):
        """Eager initialization works with forward references."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database(), created_at_start=True)
            module.single[UserRepository](
                lambda: UserRepository(db=module.get()),
                created_at_start=True
            )

        KotInjection.start(modules=[module])

        # Both should already be created
        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo.db, Database)


class TestIndexBasedResolutionWithForwardRef(KotInjectionTestCase):
    """Tests for index-based resolution with forward references."""

    def test_index_based_get_with_forward_reference(self):
        """Index-based module.get(index) works with forward references."""
        # Using module-level Config, ServiceWithTwoDeps, Database classes

        module = KotInjectionModule()
        with module:
            module.single[Config](lambda: Config())
            module.single[Database](lambda: Database())
            # Use index-based resolution: config is index 0, db is index 1
            module.single[ServiceWithTwoDeps](
                lambda: ServiceWithTwoDeps(
                    config=module.get(0),
                    db=module.get(1)
                )
            )

        KotInjection.start(modules=[module])

        service = KotInjection.get[ServiceWithTwoDeps]()
        self.assertIsInstance(service.config, Config)
        self.assertIsInstance(service.db, Database)


if __name__ == '__main__':
    unittest.main()
