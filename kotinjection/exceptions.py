"""
KotInjection Exceptions

Custom exception hierarchy for KotInjection DI framework
"""


class KotInjectionError(Exception):
    """
    Base exception for all KotInjection errors.

    All KotInjection-specific exceptions inherit from this class.
    You can catch this to handle any KotInjection error generically.

    Example:
        >>> try:
        ...     service = KotInjection.get[MyService]()
        ... except KotInjectionError as e:
        ...     print(f"DI error: {e}")
    """

    pass


class AlreadyStartedError(KotInjectionError):
    """
    Raised when KotInjection.start() is called while already started.

    This error occurs when trying to start the global container
    without stopping the existing one first.

    Similar to Koin's KoinAppAlreadyStartedException.

    Common causes:
        - Calling ``KotInjection.start()`` multiple times
        - Forgetting to call ``KotInjection.stop()`` before restarting
        - Test teardown not properly cleaning up the container

    Solution:
        Call ``stop()`` before starting again::

            KotInjection.stop()
            KotInjection.start(modules=[new_module])

        Or use ``load_modules()`` to add modules dynamically::

            KotInjection.load_modules([additional_module])
    """

    pass


class NotInitializedError(KotInjectionError):
    """
    Raised when KotInjection global container is not initialized.

    This error occurs when trying to use the global API before calling
    ``KotInjection.start()``.

    Common causes:
        - Forgetting to call ``KotInjection.start(modules=[...])``
        - Calling ``KotInjection.get[Type]()`` before initialization
        - Accessing the container before application startup

    Solution:
        Initialize KotInjection before using the global API::

            module = KotInjectionModule()
            with module:
                module.single[MyService](lambda: MyService())

            KotInjection.start(modules=[module])  # Initialize first!
            service = KotInjection.get[MyService]()  # Now this works
    """

    pass


class ContainerClosedError(KotInjectionError):
    """
    Raised when attempting to use a closed container.

    This error occurs when calling ``load_modules()`` or ``unload_modules()``
    on a ``KotInjectionCore`` that has been closed.

    Common causes:
        - Using a container after calling ``app.close()``
        - Using a container after exiting a ``with`` block

    Solution:
        Create a new ``KotInjectionCore`` instance instead of reusing
        a closed one::

            with KotInjectionCore(modules=[module]) as app:
                service = app.get[MyService]()  # OK
            # Container is now closed

            # Create a new one if needed
            app2 = KotInjectionCore(modules=[module])
    """

    pass


class DuplicateDefinitionError(KotInjectionError):
    """
    Raised when the same type is registered multiple times.

    This error occurs when loading modules that contain definitions
    for the same interface type.

    Common causes:
        - Registering the same type in multiple modules
        - Loading the same module twice
        - Accidentally creating duplicate registrations

    Solution:
        1. Use a single module for each type
        2. Check for duplicate registrations
        3. Use ``unload_modules()`` before re-registering::

            # Avoid duplicates - register in one module only
            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())
                # module.single[Database](...)  # Don't do this!
    """

    pass


class DefinitionNotFoundError(KotInjectionError):
    """
    Raised when a requested type is not registered in the container.

    This error occurs when calling ``get[Type]()`` for a type that
    has not been registered in any loaded module.

    Common causes:
        - Forgetting to register the type in a module
        - Typo in the type name
        - Module containing the type not loaded
        - Type registered with a different interface

    Solution:
        Register the type in a module before using it::

            module = KotInjectionModule()
            with module:
                module.single[MyService](lambda: MyService())

            KotInjection.start(modules=[module])
            # Now MyService is available
            service = KotInjection.get[MyService]()

    Note:
        The error message includes a list of registered types
        to help identify available dependencies.
    """

    pass


class CircularDependencyError(KotInjectionError):
    """
    Raised when circular dependency is detected during resolution.

    This error occurs when type A depends on type B, and type B
    (directly or indirectly) depends on type A.

    Example of circular dependency::

        class ServiceA:
            def __init__(self, b: ServiceB): ...

        class ServiceB:
            def __init__(self, a: ServiceA): ...  # Circular!

    Solution:
        1. Refactor to remove the circular dependency
        2. Use lazy initialization or dependency inversion
        3. Extract common functionality to a third service::

            # Break the cycle with an interface
            class ServiceAInterface(ABC):
                pass

            class ServiceA(ServiceAInterface):
                def __init__(self, b: ServiceB): ...

            class ServiceB:
                def __init__(self, a: ServiceAInterface): ...
    """

    pass


class TypeInferenceError(KotInjectionError):
    """
    Raised when type inference fails during registration or resolution.

    This error occurs when KotInjection cannot determine the types
    needed for dependency injection.

    Common causes:
        - Missing type hints on ``__init__`` parameters
        - Using built-in types or C extensions without accessible signatures
        - Factory returning a different type than registered
        - Using ``None`` as a type parameter

    Solution:
        Ensure all ``__init__`` parameters have type hints::

            # Good - all parameters have type hints
            class UserRepository:
                def __init__(self, db: Database, cache: CacheService):
                    self.db = db
                    self.cache = cache

            # Bad - missing type hints
            class UserRepository:
                def __init__(self, db, cache):  # TypeInferenceError!
                    self.db = db
                    self.cache = cache
    """

    pass


class ResolutionContextError(KotInjectionError):
    """
    Raised when resolution context is invalid or misused.

    This error occurs when ``module.get()`` is called incorrectly
    during dependency resolution.

    Common causes:
        - Calling ``module.get()`` outside a factory function
        - Calling ``module.get()`` more times than there are parameters
        - Using type inference in an unsupported context

    Solution:
        Use ``module.get()`` only inside factory lambdas, and ensure
        the number of calls matches the number of parameters::

            class Service:
                def __init__(self, db: Database, cache: CacheService):
                    pass

            module = KotInjectionModule()
            with module:
                module.single[Database](lambda: Database())
                module.single[CacheService](lambda: CacheService())
                # Two get() calls for two parameters
                module.single[Service](
                    lambda: Service(module.get(), module.get())
                )
    """

    pass
