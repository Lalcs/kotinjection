"""
Tests for scoped dependency functionality.

Scoped dependencies are shared within the same scope instance
but separate across different scope instances.
"""

import unittest
from kotinjection import (
    KotInjection,
    KotInjectionCore,
    KotInjectionModule,
    DefinitionNotFoundError,
    ScopedResolutionError,
)
from tests.conftest import KotInjectionTestCase


class Database:
    """Global singleton dependency."""
    pass


class RequestContext:
    """Scoped dependency for request scope."""
    def __init__(self):
        self.request_id = id(self)


class UserSession:
    """Scoped dependency for session scope."""
    def __init__(self):
        self.session_id = id(self)


class SessionData:
    """Scoped dependency for type-based scope."""
    def __init__(self):
        self.data_id = id(self)


class TestScopedBasics(KotInjectionTestCase):
    """Basic scoped dependency tests."""

    def test_scoped_returns_same_instance_within_scope(self):
        """Scoped dependency returns same instance within the same scope."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope("request", "req-1") as scope:
            ctx1 = scope.get[RequestContext]()
            ctx2 = scope.get[RequestContext]()
            self.assertIs(ctx1, ctx2)

    def test_scoped_returns_different_instances_across_scopes(self):
        """Scoped dependency returns different instances across different scopes."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope("request", "req-1") as scope1:
            ctx1 = scope1.get[RequestContext]()

        with KotInjection.create_scope("request", "req-2") as scope2:
            ctx2 = scope2.get[RequestContext]()

        self.assertIsNot(ctx1, ctx2)

    def test_scope_close_releases_instances(self):
        """Closing a scope releases cached instances."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        scope = KotInjection.create_scope("request", "req-1")
        ctx = scope.get[RequestContext]()
        self.assertIsNotNone(ctx)

        scope.close()
        self.assertTrue(scope.is_closed)


class TestScopedWithGlobalDependencies(KotInjectionTestCase):
    """Tests for scoped dependencies interacting with global dependencies."""

    def test_scoped_can_resolve_singleton(self):
        """Scoped dependency can resolve singleton from parent container."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        # Singleton from global
        db = KotInjection.get[Database]()

        # Scoped can also access singleton
        with KotInjection.create_scope("request", "req-1") as scope:
            db_from_scope = scope.get[Database]()
            self.assertIs(db, db_from_scope)


class TestTypedScope(KotInjectionTestCase):
    """Tests for type-based scope qualifiers."""

    def test_type_based_scope_definition(self):
        """Type-based scope definition works correctly."""
        module = KotInjectionModule()
        with module:
            with module.scope[UserSession]:
                module.scoped[SessionData](lambda: SessionData())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope[UserSession]("session-1") as scope:
            data1 = scope.get[SessionData]()
            data2 = scope.get[SessionData]()
            self.assertIs(data1, data2)

    def test_type_based_scope_isolation(self):
        """Type-based scope provides proper isolation."""
        module = KotInjectionModule()
        with module:
            with module.scope[UserSession]:
                module.scoped[SessionData](lambda: SessionData())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope[UserSession]("session-1") as scope1:
            data1 = scope1.get[SessionData]()

        with KotInjection.create_scope[UserSession]("session-2") as scope2:
            data2 = scope2.get[SessionData]()

        self.assertIsNot(data1, data2)


class TestScopeErrors(KotInjectionTestCase):
    """Tests for scoped dependency error handling."""

    def test_scoped_outside_module_scope_raises_error(self):
        """Using scoped[] outside scope context raises error."""
        module = KotInjectionModule()
        with module:
            with self.assertRaises(Exception):  # ResolutionContextError
                module.scoped[RequestContext](lambda: RequestContext())

    def test_undefined_scope_raises_error(self):
        """Creating scope for undefined qualifier raises error."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        with self.assertRaises(DefinitionNotFoundError):
            KotInjection.create_scope("undefined_scope", "scope-1")

    def test_scope_qualifier_mismatch_raises_error(self):
        """Resolving scoped dependency from wrong scope raises error."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
            with module.scope("session"):
                module.scoped[UserSession](lambda: UserSession())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope("session", "session-1") as scope:
            # Try to resolve request-scoped dependency from session scope
            with self.assertRaises(ScopedResolutionError):
                scope.get[RequestContext]()


class TestScopedWithIsolatedContainer(KotInjectionTestCase):
    """Tests for scoped dependencies with isolated containers."""

    def test_isolated_container_scoped_basic(self):
        """Scoped dependencies work with isolated containers."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        with KotInjectionCore(modules=[module]) as app:
            with app.create_scope("request", "req-1") as scope:
                ctx1 = scope.get[RequestContext]()
                ctx2 = scope.get[RequestContext]()
                self.assertIs(ctx1, ctx2)

    def test_isolated_containers_have_independent_scopes(self):
        """Different isolated containers have independent scopes."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        with KotInjectionCore(modules=[module]) as app1:
            with app1.create_scope("request", "req-1") as scope1:
                ctx1 = scope1.get[RequestContext]()

        with KotInjectionCore(modules=[module]) as app2:
            with app2.create_scope("request", "req-1") as scope2:
                ctx2 = scope2.get[RequestContext]()

        # Even with same scope_id, different containers = different instances
        self.assertIsNot(ctx1, ctx2)


class TestMultipleScopes(KotInjectionTestCase):
    """Tests for multiple scopes in the same module."""

    def test_multiple_scopes_independent(self):
        """Multiple scope definitions are independent."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())
            with module.scope("session"):
                module.scoped[UserSession](lambda: UserSession())

        KotInjection.start(modules=[module])

        with KotInjection.create_scope("request", "req-1") as req_scope:
            ctx = req_scope.get[RequestContext]()
            self.assertIsInstance(ctx, RequestContext)

        with KotInjection.create_scope("session", "sess-1") as session_scope:
            session = session_scope.get[UserSession]()
            self.assertIsInstance(session, UserSession)


class TestScopeContextManager(KotInjectionTestCase):
    """Tests for scope context manager behavior."""

    def test_scope_context_manager_closes_on_exit(self):
        """Scope is closed when exiting context manager."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        scope = KotInjection.create_scope("request", "req-1")
        with scope:
            self.assertFalse(scope.is_closed)
        self.assertTrue(scope.is_closed)

    def test_closed_scope_raises_error(self):
        """Resolving from closed scope raises error."""
        module = KotInjectionModule()
        with module:
            with module.scope("request"):
                module.scoped[RequestContext](lambda: RequestContext())

        KotInjection.start(modules=[module])

        scope = KotInjection.create_scope("request", "req-1")
        scope.close()

        with self.assertRaises(RuntimeError):
            scope.get[RequestContext]()


if __name__ == '__main__':
    unittest.main()
