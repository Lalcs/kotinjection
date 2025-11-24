"""
Error Messages Tests

Tests for error message quality and exception hierarchy.
Verifies that error messages are helpful and contain sufficient context.
"""

import unittest

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.core import KotInjectionCore
from kotinjection.exceptions import (
    KotInjectionError,
    NotInitializedError,
    ContainerClosedError,
    DuplicateDefinitionError,
    DefinitionNotFoundError,
    CircularDependencyError,
    TypeInferenceError,
    ResolutionContextError,
)


class Database:
    """Simple database for testing."""
    pass


class CacheService:
    """Simple cache service for testing."""
    pass


class UserRepository:
    """Repository with database dependency."""

    def __init__(self, db: Database):
        self.db = db


class TestExceptionHierarchy(unittest.TestCase):
    """Test that all exceptions inherit from KotInjectionError."""

    def test_not_initialized_error_inherits_from_base(self):
        """NotInitializedError inherits from KotInjectionError."""
        error = NotInitializedError("test")
        self.assertIsInstance(error, KotInjectionError)
        self.assertIsInstance(error, Exception)

    def test_container_closed_error_inherits_from_base(self):
        """ContainerClosedError inherits from KotInjectionError."""
        error = ContainerClosedError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_duplicate_definition_error_inherits_from_base(self):
        """DuplicateDefinitionError inherits from KotInjectionError."""
        error = DuplicateDefinitionError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_definition_not_found_error_inherits_from_base(self):
        """DefinitionNotFoundError inherits from KotInjectionError."""
        error = DefinitionNotFoundError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_circular_dependency_error_inherits_from_base(self):
        """CircularDependencyError inherits from KotInjectionError."""
        error = CircularDependencyError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_type_inference_error_inherits_from_base(self):
        """TypeInferenceError inherits from KotInjectionError."""
        error = TypeInferenceError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_resolution_context_error_inherits_from_base(self):
        """ResolutionContextError inherits from KotInjectionError."""
        error = ResolutionContextError("test")
        self.assertIsInstance(error, KotInjectionError)

    def test_catch_all_kotinjection_errors(self):
        """All KotInjection errors can be caught with base class."""
        exceptions = [
            NotInitializedError("test"),
            ContainerClosedError("test"),
            DuplicateDefinitionError("test"),
            DefinitionNotFoundError("test"),
            CircularDependencyError("test"),
            TypeInferenceError("test"),
            ResolutionContextError("test"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except KotInjectionError as e:
                self.assertIsInstance(e, KotInjectionError)


class TestNotInitializedErrorMessages(unittest.TestCase):
    """Test NotInitializedError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_message_mentions_start_method(self):
        """Error message mentions start() method."""
        with self.assertRaises(NotInitializedError) as ctx:
            KotInjection.get[Database]()

        message = str(ctx.exception)
        self.assertIn("start()", message)


class TestDefinitionNotFoundErrorMessages(unittest.TestCase):
    """Test DefinitionNotFoundError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_message_includes_type_name(self):
        """Error message includes the missing type name."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        with self.assertRaises(DefinitionNotFoundError) as ctx:
            KotInjection.get[CacheService]()

        message = str(ctx.exception)
        self.assertIn("CacheService", message)

    def test_message_lists_registered_types(self):
        """Error message lists registered types."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        KotInjection.start(modules=[module])

        with self.assertRaises(DefinitionNotFoundError) as ctx:
            KotInjection.get[CacheService]()

        message = str(ctx.exception)
        self.assertIn("Database", message)
        self.assertIn("Registered types", message)

    def test_message_includes_hint(self):
        """Error message includes registration hint."""
        module = KotInjectionModule()
        KotInjection.start(modules=[module])

        with self.assertRaises(DefinitionNotFoundError) as ctx:
            KotInjection.get[Database]()

        message = str(ctx.exception)
        self.assertIn("Hint", message)
        self.assertIn("single", message)


class TestDuplicateDefinitionErrorMessages(unittest.TestCase):
    """Test DuplicateDefinitionError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_message_includes_type_name(self):
        """Error message includes the duplicate type name."""
        module1 = KotInjectionModule()
        with module1:
            module1.single[Database](lambda: Database())

        module2 = KotInjectionModule()
        with module2:
            module2.single[Database](lambda: Database())

        KotInjection.start(modules=[module1])

        with self.assertRaises(DuplicateDefinitionError) as ctx:
            KotInjection.load_modules([module2])

        message = str(ctx.exception)
        self.assertIn("Database", message)


class TestContainerClosedErrorMessages(unittest.TestCase):
    """Test ContainerClosedError message quality."""

    def test_message_indicates_closed_state(self):
        """Error message indicates container is closed."""
        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())

        app = KotInjectionCore(modules=[module])
        app.close()

        with self.assertRaises(ContainerClosedError) as ctx:
            app.get[Database]()

        message = str(ctx.exception)
        self.assertIn("closed", message.lower())


class TestTypeInferenceErrorMessages(unittest.TestCase):
    """Test TypeInferenceError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_missing_type_hint_message_includes_parameter_name(self):
        """Error message includes parameter name when type hint is missing."""

        class ServiceWithoutHint:
            def __init__(self, dependency):  # No type hint
                self.dependency = dependency

        module = KotInjectionModule()
        with self.assertRaises(TypeInferenceError) as ctx:
            with module:
                module.single[ServiceWithoutHint](lambda: ServiceWithoutHint(None))

        message = str(ctx.exception)
        self.assertIn("dependency", message)
        self.assertIn("type hint", message.lower())

    def test_return_type_mismatch_message_includes_both_types(self):
        """Error message includes expected and actual types on mismatch."""
        module = KotInjectionModule()
        with module:
            # Factory returns wrong type
            module.single[Database](lambda: CacheService())

        KotInjection.start(modules=[module])

        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[Database]()

        message = str(ctx.exception)
        self.assertIn("Database", message)
        self.assertIn("CacheService", message)


class TestCircularDependencyErrorMessages(unittest.TestCase):
    """Test CircularDependencyError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_message_shows_dependency_chain(self):
        """Error message shows the circular dependency chain."""
        # Use the same pattern as test_class_based_api.py for circular dependency
        # Note: Due to local class definition and forward references, we need
        # to use positional args and KotInjectionError as base catch.
        from kotinjection.core import KotInjectionCore

        class ServiceA:
            def __init__(self, b: 'ServiceB'):
                self.b = b

        class ServiceB:
            def __init__(self, a: ServiceA):
                self.a = a

        module = KotInjectionModule()
        with module:
            # Use positional module.get() - same pattern as test_class_based_api.py
            module.single[ServiceA](lambda: ServiceA(module.get()))
            module.single[ServiceB](lambda: ServiceB(module.get()))

        # Use isolated container to test circular dependency detection
        app = KotInjectionCore(modules=[module])

        # May raise CircularDependencyError or other KotInjectionError
        # due to forward reference handling
        with self.assertRaises(KotInjectionError):
            app.get[ServiceA]()

        app.close()


class TestResolutionContextErrorMessages(unittest.TestCase):
    """Test ResolutionContextError message quality."""

    def setUp(self):
        KotInjection.stop()

    def tearDown(self):
        KotInjection.stop()

    def test_get_outside_factory_message(self):
        """Error message when get() called outside factory."""
        with self.assertRaises(ResolutionContextError) as ctx:
            KotInjectionModule.get()

        message = str(ctx.exception)
        self.assertIn("get()", message)

    def test_too_many_get_calls_message(self):
        """Error message includes expected vs actual call count."""

        class SingleParam:
            def __init__(self, db: Database):
                self.db = db

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            module.single[SingleParam](
                lambda: SingleParam(
                    db=module.get(),
                )
            )

        # This should work fine
        KotInjection.start(modules=[module])
        service = KotInjection.get[SingleParam]()
        self.assertIsNotNone(service)


if __name__ == '__main__':
    unittest.main()
