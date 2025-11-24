"""
Context Isolation Tests

Verifies behavior of isolated container instances
"""

import unittest
from kotinjection import (
    KotInjectionModule,
    KotInjection,
    KotInjectionCore,
    IsolatedKotInjectionComponent,
    ContainerClosedError,
    DefinitionNotFoundError,
)


# Test class definitions

class ServiceA:
    """Test service A"""
    def __init__(self):
        self.name = "ServiceA"
        self.counter = 0

    def increment(self):
        self.counter += 1
        return self.counter


class ServiceB:
    """Test service B"""
    def __init__(self):
        self.name = "ServiceB"
        self.data = []

    def add_data(self, item):
        self.data.append(item)
        return len(self.data)


class Repository:
    """Test repository"""
    def __init__(self):
        self.records = []

    def save(self, record):
        self.records.append(record)


class LibraryService:
    """Library-specific service"""
    def __init__(self, repo: Repository):
        self.repo = repo
        self.lib_name = "MyLibrary"


# Test cases

class TestKotInjectionCoreBasics(unittest.TestCase):
    """Basic functionality tests for KotInjectionCore"""

    def test_create_app_without_modules(self):
        """Can create app without modules"""
        app = KotInjectionCore()
        self.assertIsNotNone(app)
        self.assertFalse(app.is_closed)

    def test_create_app_with_modules(self):
        """Can create app with specified modules"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        app = KotInjectionCore(modules=[module])
        self.assertIsNotNone(app)
        service = app.get[ServiceA]()
        self.assertEqual(service.name, "ServiceA")

    def test_KotInjectionCore_function(self):
        """Can create using KotInjectionCore() function"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        app = KotInjectionCore(modules=[module])
        self.assertIsNotNone(app)
        service = app.get[ServiceA]()
        self.assertEqual(service.name, "ServiceA")

    def test_app_close(self):
        """Can close app"""
        app = KotInjectionCore()
        self.assertFalse(app.is_closed)

        app.close()
        self.assertTrue(app.is_closed)

    def test_app_context_manager(self):
        """Can use as context manager"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        with KotInjectionCore(modules=[module]) as app:
            self.assertFalse(app.is_closed)
            service = app.get[ServiceA]()
            self.assertEqual(service.name, "ServiceA")

        # Closed after exiting context
        self.assertTrue(app.is_closed)


class TestMultipleIsolatedContainers(unittest.TestCase):
    """Tests for multiple isolated containers running simultaneously"""

    def test_two_apps_have_independent_singletons(self):
        """Two apps have independent singletons"""
        # App 1
        module1 = KotInjectionModule()
        with module1:
            module1.single[ServiceA](lambda: ServiceA())

        app1 = KotInjectionCore(modules=[module1])

        # App 2
        module2 = KotInjectionModule()
        with module2:
            module2.single[ServiceA](lambda: ServiceA())

        app2 = KotInjectionCore(modules=[module2])

        # Get service from both
        service1 = app1.get[ServiceA]()
        service2 = app2.get[ServiceA]()

        # Verify they are different instances
        self.assertIsNot(service1, service2)

        # Verify states are independent
        service1.increment()
        service1.increment()
        self.assertEqual(service1.counter, 2)
        self.assertEqual(service2.counter, 0)

    def test_multiple_apps_with_different_modules(self):
        """Multiple apps with different modules"""
        # App 1: ServiceA only
        module1 = KotInjectionModule()
        with module1:
            module1.single[ServiceA](lambda: ServiceA())

        app1 = KotInjectionCore(modules=[module1])

        # App 2: ServiceB only
        module2 = KotInjectionModule()
        with module2:
            module2.single[ServiceB](lambda: ServiceB())

        app2 = KotInjectionCore(modules=[module2])

        # Can get ServiceA from app1
        service_a = app1.get[ServiceA]()
        self.assertEqual(service_a.name, "ServiceA")

        # Can get ServiceB from app2
        service_b = app2.get[ServiceB]()
        self.assertEqual(service_b.name, "ServiceB")

        # app1 cannot get ServiceB (not registered)
        with self.assertRaises(DefinitionNotFoundError):
            app1.get[ServiceB]()

        # app2 cannot get ServiceA (not registered)
        with self.assertRaises(DefinitionNotFoundError):
            app2.get[ServiceA]()


class TestIsolationFromGlobalContainer(unittest.TestCase):
    """Tests for isolation from global container"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Clean up after each test"""
        KotInjection.stop()

    def test_app_does_not_affect_global_container(self):
        """Isolated app does not affect global container"""
        # Initialize global container
        global_module = KotInjectionModule()
        with global_module:
            global_module.single[ServiceA](lambda: ServiceA())

        KotInjection.start(modules=[global_module])
        global_service = KotInjection.get[ServiceA]()

        # Create isolated app
        app_module = KotInjectionModule()
        with app_module:
            app_module.single[ServiceA](lambda: ServiceA())

        app = KotInjectionCore(modules=[app_module])
        app_service = app.get[ServiceA]()

        # Verify they are different instances
        self.assertIsNot(global_service, app_service)

        # Verify states are independent
        global_service.increment()
        app_service.increment()
        app_service.increment()

        self.assertEqual(global_service.counter, 1)
        self.assertEqual(app_service.counter, 2)

    def test_global_container_does_not_affect_app(self):
        """Global container does not affect isolated app"""
        # Create isolated app first
        app_module = KotInjectionModule()
        with app_module:
            app_module.single[ServiceB](lambda: ServiceB())

        app = KotInjectionCore(modules=[app_module])
        app_service = app.get[ServiceB]()
        app_service.add_data("app_data")

        # Then initialize global container
        global_module = KotInjectionModule()
        with global_module:
            global_module.single[ServiceB](lambda: ServiceB())

        KotInjection.start(modules=[global_module])
        global_service = KotInjection.get[ServiceB]()

        # App service is not affected
        self.assertEqual(len(app_service.data), 1)
        self.assertIn("app_data", app_service.data)

        # Global service is a new instance
        self.assertEqual(len(global_service.data), 0)
        self.assertIsNot(app_service, global_service)


class TestLibraryDevelopmentScenario(unittest.TestCase):
    """Tests for library development scenario"""

    def setUp(self):
        """Reset global container before each test"""
        KotInjection.stop()

    def tearDown(self):
        """Clean up after each test"""
        KotInjection.stop()

    def test_library_with_isolated_container(self):
        """Library has isolated container"""
        # Create library container first
        library_app = KotInjectionCore()

        # Library-specific module
        library_module = KotInjectionModule()
        with library_module:
            library_module.single[Repository](lambda: Repository())
            library_module.single[LibraryService](
                lambda: LibraryService(repo=library_module.get())
            )

        # Load module into library container
        library_app.load_modules([library_module])

        # Define library component class
        class LibraryComponent(IsolatedKotInjectionComponent):
            def get_app(self):
                return library_app

        # Library service class
        class MyLibraryAPI(LibraryComponent):
            def __init__(self):
                self.service = self.get[LibraryService]()

            def save_record(self, record):
                self.service.repo.save(record)
                return len(self.service.repo.records)

        # Host application module (different Repository)
        host_module = KotInjectionModule()
        with host_module:
            host_module.single[Repository](lambda: Repository())

        KotInjection.start(modules=[host_module])
        host_repo = KotInjection.get[Repository]()

        # Use library API
        api = MyLibraryAPI()
        count = api.save_record("library_record")
        self.assertEqual(count, 1)

        # Host app Repository is not affected
        self.assertEqual(len(host_repo.records), 0)

        # Library Repository has data saved
        library_service = library_app.get[LibraryService]()
        self.assertEqual(len(library_service.repo.records), 1)
        self.assertIn("library_record", library_service.repo.records)


class TestMultiTenantScenario(unittest.TestCase):
    """Tests for multi-tenant scenario"""

    def test_separate_containers_per_tenant(self):
        """Separate container per tenant"""
        # Tenant 1 container
        tenant1_module = KotInjectionModule()
        with tenant1_module:
            tenant1_module.single[ServiceB](lambda: ServiceB())

        tenant1_app = KotInjectionCore(modules=[tenant1_module])

        # Tenant 2 container
        tenant2_module = KotInjectionModule()
        with tenant2_module:
            tenant2_module.single[ServiceB](lambda: ServiceB())

        tenant2_app = KotInjectionCore(modules=[tenant2_module])

        # Use tenant 1 service
        tenant1_service = tenant1_app.get[ServiceB]()
        tenant1_service.add_data("tenant1_data1")
        tenant1_service.add_data("tenant1_data2")

        # Use tenant 2 service
        tenant2_service = tenant2_app.get[ServiceB]()
        tenant2_service.add_data("tenant2_data")

        # Data is completely isolated
        self.assertEqual(len(tenant1_service.data), 2)
        self.assertEqual(len(tenant2_service.data), 1)
        self.assertIn("tenant1_data1", tenant1_service.data)
        self.assertIn("tenant1_data2", tenant1_service.data)
        self.assertIn("tenant2_data", tenant2_service.data)
        self.assertNotIn("tenant2_data", tenant1_service.data)


class TestTestIsolationScenario(unittest.TestCase):
    """Tests for test isolation scenario"""

    def test_each_test_case_has_independent_container(self):
        """Each test case has independent container"""
        # Test case 1
        with KotInjectionCore() as test_app1:
            module1 = KotInjectionModule()
            with module1:
                module1.single[ServiceA](lambda: ServiceA())

            test_app1.load_modules([module1])
            service1 = test_app1.get[ServiceA]()
            service1.increment()
            service1.increment()

            self.assertEqual(service1.counter, 2)

        # Test case 2 (completely independent)
        with KotInjectionCore() as test_app2:
            module2 = KotInjectionModule()
            with module2:
                module2.single[ServiceA](lambda: ServiceA())

            test_app2.load_modules([module2])
            service2 = test_app2.get[ServiceA]()

            # New instance so counter is 0
            self.assertEqual(service2.counter, 0)

    def test_test_isolation_with_mock_services(self):
        """Test isolation with mock services"""
        # Production service definition
        class ProductionService:
            def get_data(self):
                return "production_data"

        # Mock service definition (inherits from production service)
        class MockService(ProductionService):
            def get_data(self):
                return "mock_data"

        # Test 1: Use production service
        module1 = KotInjectionModule()
        with module1:
            module1.single[ProductionService](lambda: ProductionService())

        with KotInjectionCore(modules=[module1]) as app1:
            service1 = app1.get[ProductionService]()
            self.assertEqual(service1.get_data(), "production_data")

        # Test 2: Use mock service (registered as subclass)
        module2 = KotInjectionModule()
        with module2:
            # Register mock as production service (MockService is subclass of ProductionService)
            module2.single[ProductionService](lambda: MockService())

        with KotInjectionCore(modules=[module2]) as app2:
            service2 = app2.get[ProductionService]()
            # MockService is subclass of ProductionService so passes type validation
            self.assertEqual(service2.get_data(), "mock_data")


class TestResourceCleanup(unittest.TestCase):
    """Tests for resource cleanup"""

    def test_close_prevents_further_usage(self):
        """Cannot use after close"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        app = KotInjectionCore(modules=[module])

        # Can use before close
        service = app.get[ServiceA]()
        self.assertIsNotNone(service)

        # Close
        app.close()
        self.assertTrue(app.is_closed)

        # Loading modules after close fails
        with self.assertRaises(ContainerClosedError):
            app.load_modules([module])

    def test_context_manager_automatically_closes(self):
        """Context manager automatically closes"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        with KotInjectionCore(modules=[module]) as app:
            self.assertFalse(app.is_closed)

        # Automatically closed after exiting with statement
        self.assertTrue(app.is_closed)

    def test_unload_modules_from_app(self):
        """Unloads modules from isolated app"""
        module = KotInjectionModule()
        with module:
            module.single[ServiceA](lambda: ServiceA())

        app = KotInjectionCore(modules=[module])

        # Available
        service = app.get[ServiceA]()
        self.assertIsNotNone(service)

        # Unload
        app.unload_modules([module])

        # No longer available
        with self.assertRaises(DefinitionNotFoundError):
            app.get[ServiceA]()


if __name__ == '__main__':
    unittest.main()
