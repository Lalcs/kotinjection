"""
GetProxy Tests

Tests for the KotInjectionGetProxy class that enables
the KotInjection.get[Type]() syntax.
"""

import unittest

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.get_proxy import KotInjectionGetProxy
from kotinjection.exceptions import NotInitializedError


class Database:
    """Simple database for testing."""
    pass


class UserRepository:
    """Repository with database dependency."""

    def __init__(self, db: Database):
        self.db = db


class TestGetProxyDirectInstantiation(unittest.TestCase):
    """Test direct instantiation and usage of KotInjectionGetProxy."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_proxy_with_none_app_raises_error(self):
        """Proxy raises NotInitializedError when app is None."""
        proxy = KotInjectionGetProxy(lambda: None)

        with self.assertRaises(NotInitializedError) as ctx:
            proxy[Database]()

        self.assertIn("start()", str(ctx.exception))

    def test_proxy_with_valid_app_returns_callable(self):
        """Proxy returns callable when app is initialized."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        proxy = KotInjection.get
        getter = proxy[Database]

        self.assertTrue(callable(getter))
        db = getter()
        self.assertIsInstance(db, Database)

    def test_proxy_getitem_returns_different_callables_for_different_types(self):
        """Proxy returns different callables for different types."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[UserRepository](
                lambda: UserRepository(db=module.get())
            )

        KotInjection.start(modules=[module])

        getter_db = KotInjection.get[Database]
        getter_repo = KotInjection.get[UserRepository]

        self.assertIsNot(getter_db, getter_repo)

        db = getter_db()
        repo = getter_repo()

        self.assertIsInstance(db, Database)
        self.assertIsInstance(repo, UserRepository)


class TestGetProxySubscriptSyntax(unittest.TestCase):
    """Test the subscript syntax via KotInjection.get[Type]()."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_subscript_syntax_basic(self):
        """Basic subscript syntax works correctly."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)

    def test_subscript_syntax_with_dependencies(self):
        """Subscript syntax works with dependencies."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[UserRepository](
                lambda: UserRepository(db=module.get())
            )

        KotInjection.start(modules=[module])

        repo = KotInjection.get[UserRepository]()
        self.assertIsInstance(repo, UserRepository)
        self.assertIsInstance(repo.db, Database)

    def test_subscript_syntax_before_start_raises_error(self):
        """Subscript syntax before start() raises NotInitializedError."""
        with self.assertRaises(NotInitializedError):
            KotInjection.get[Database]()

    def test_subscript_syntax_returns_same_singleton(self):
        """Multiple calls with subscript syntax return same singleton."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        db1 = KotInjection.get[Database]()
        db2 = KotInjection.get[Database]()

        self.assertIs(db1, db2)


class TestGetProxyErrorHandling(unittest.TestCase):
    """Test error handling in GetProxy."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_unregistered_type_raises_definition_not_found(self):
        """Accessing unregistered type raises DefinitionNotFoundError."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        from kotinjection.exceptions import DefinitionNotFoundError
        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.get[UserRepository]()


class TestGetProxyClassAttribute(unittest.TestCase):
    """Test that get is a class attribute on KotInjection."""

    def test_get_is_class_attribute(self):
        """KotInjection.get is a class attribute (not instance)."""
        self.assertTrue(hasattr(KotInjection, 'get'))
        self.assertIsInstance(KotInjection.get, KotInjectionGetProxy)

    def test_get_persists_across_start_calls(self):
        """KotInjection.get persists across multiple start() calls."""
        proxy_before = KotInjection.get

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        proxy_after = KotInjection.get

        # Should be the same proxy instance
        self.assertIs(proxy_before, proxy_after)

        KotInjection.stop()


if __name__ == '__main__':
    unittest.main()
