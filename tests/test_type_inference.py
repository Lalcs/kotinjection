"""
Type Inference Error Tests

Tests for TypeInferenceError exception handling
"""

import sys
import os
import unittest

# Add tests directory to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kotinjection import KotInjection, KotInjectionModule
from kotinjection.exceptions import TypeInferenceError

from conftest import KotInjectionTestCase
from fixtures import Database, ServiceWithoutHint, ServiceWithPartialHints


class TestTypeInferenceError(KotInjectionTestCase):
    """Tests for TypeInferenceError"""

    def test_missing_type_hint_raises_error(self):
        """TypeInferenceError raised for parameters without type hints at resolution time"""
        module = KotInjectionModule()
        with module:
            # Registration succeeds (lazy type inference)
            module.single[ServiceWithoutHint](lambda: ServiceWithoutHint(None))

        KotInjection.start(modules=[module])

        # Error occurs at resolution time
        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ServiceWithoutHint]()

        self.assertIn("Missing type hint", str(ctx.exception))
        self.assertIn("dependency", str(ctx.exception))

    def test_partial_type_hints_raises_error(self):
        """Error when some parameters lack type hints at resolution time"""
        module = KotInjectionModule()
        with module:
            # Registration succeeds (lazy type inference)
            module.single[ServiceWithPartialHints](
                lambda: ServiceWithPartialHints(None, None)
            )

        KotInjection.start(modules=[module])

        # Error occurs at resolution time
        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ServiceWithPartialHints]()

        self.assertIn("cache", str(ctx.exception))

    def test_none_interface_resolves_successfully(self):
        """NoneType can be registered and resolved (edge case)"""
        # Note: This is an edge case. NoneType has no typed parameters
        # so it resolves successfully with lazy type inference.
        module = KotInjectionModule()
        with module:
            module.single[type(None)](lambda: None)

        KotInjection.start(modules=[module])

        # NoneType can be resolved since it has no typed dependencies
        result = KotInjection.get[type(None)]()
        self.assertIsNone(result)

    def test_error_message_includes_class_name(self):
        """Error message includes class name at resolution time"""
        module = KotInjectionModule()
        with module:
            # Registration succeeds (lazy type inference)
            module.single[ServiceWithoutHint](lambda: ServiceWithoutHint(None))

        KotInjection.start(modules=[module])

        # Error occurs at resolution time
        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ServiceWithoutHint]()

        self.assertIn("ServiceWithoutHint", str(ctx.exception))

    def test_factory_return_type_validation(self):
        """Factory return type is validated correctly"""

        class WrongService:
            pass

        module = KotInjectionModule()
        with module:
            module.single[Database](lambda: Database())
            # Register Database but return WrongService
            module.single[WrongService](lambda: WrongService())

        KotInjection.start(modules=[module])

        # This should work - correct return type
        db = KotInjection.get[Database]()
        self.assertIsInstance(db, Database)

    def test_factory_return_type_mismatch_raises_error(self):
        """Error when factory return type doesn't match"""

        class ExpectedService:
            pass

        class ActualService:
            pass

        module = KotInjectionModule()
        with module:
            # Factory returns ActualService, but registered as ExpectedService
            module.single[ExpectedService](lambda: ActualService())

        KotInjection.start(modules=[module])

        with self.assertRaises(TypeInferenceError) as ctx:
            KotInjection.get[ExpectedService]()

        self.assertIn("ExpectedService", str(ctx.exception))
        self.assertIn("ActualService", str(ctx.exception))


class TestTypeInferenceWithBuiltinTypes(KotInjectionTestCase):
    """Tests for type inference with built-in types"""

    def test_simple_class_without_init(self):
        """Type inference for class without explicit __init__"""

        class SimpleService:
            def do_something(self):
                return "done"

        module = KotInjectionModule()
        with module:
            module.single[SimpleService](lambda: SimpleService())

        KotInjection.start(modules=[module])

        service = KotInjection.get[SimpleService]()
        self.assertEqual(service.do_something(), "done")


if __name__ == '__main__':
    unittest.main()
