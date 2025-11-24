# KotInjection API Reference

Complete API Reference

---

## Table of Contents

- [Public API](#public-api)
  - [KotInjection](#kotinjection)
  - [KotInjectionCore](#kotinjectioncore)
  - [IsolatedKotInjectionComponent](#isolatedkotinjectioncomponent)
  - [KotInjectionModule](#kotinjectionmodule)
- [Lifecycle](#lifecycle)
  - [KotInjectionLifeCycle](#kotinjectionlifecycle)
- [Exceptions](#exceptions)
  - [KotInjectionError](#kotinjectionerror)
  - [TypeInferenceError](#typeinferenceerror)
- [Advanced Usage](#advanced-usage)

---

## Public API

### KotInjection

Class for managing the global DI container.

#### `KotInjection.start(modules: List[KotInjectionModule])`

**Description**: Initialize the global DI container.

**Parameters**:
- `modules` (List[KotInjectionModule]): List of modules to load

**Returns**: None

**Example**:
```python
from kotinjection import KotInjection, KotInjectionModule

module = KotInjectionModule()
with module:
    module.single[MyService](lambda: MyService())

KotInjection.start(modules=[module])
```

**Notes**:
- Raises `AlreadyStartedError` if container is already initialized
- Multiple modules can be passed
- Duplicate type registrations raise `DuplicateDefinitionError`

---

#### `KotInjection.get[Type]()`

**Description**: Retrieve a dependency by type from the global container.

**Type Parameters**:
- `Type`: The type to retrieve

**Returns**: Instance of the specified type

**Example**:
```python
service = KotInjection.get[MyService]()
repo = KotInjection.get[Repository]()
```

**Exceptions**:
- `NotInitializedError`: When the container is not initialized
- `DefinitionNotFoundError`: When the specified type is not registered
- `CircularDependencyError`: When circular dependency is detected

---

#### `KotInjection.stop()`

**Description**: Stop the global container and release resources.

**Returns**: None

**Example**:
```python
KotInjection.start(modules=[module])
# ... use the container ...
KotInjection.stop()
```

**Notes**:
- Idempotent - safe to call multiple times
- After stopping, `start()` can be called again

---

#### `KotInjection.is_started()`

**Description**: Check whether the global container is started.

**Returns**: bool - True if started

**Example**:
```python
print(KotInjection.is_started())  # False
KotInjection.start(modules=[module])
print(KotInjection.is_started())  # True
```

---

#### `KotInjection.load_modules(modules)`

**Description**: Load additional modules after the container has started.

**Parameters**:
- `modules` (List[KotInjectionModule]): List of modules to load

**Returns**: None

**Example**:
```python
KotInjection.load_modules([additional_module])
```

**Exceptions**:
- `NotInitializedError`: When `start()` has not been called
- `DuplicateDefinitionError`: When a duplicate type registration exists

---

#### `KotInjection.unload_modules(modules)`

**Description**: Unload modules from the global container.

**Parameters**:
- `modules` (List[KotInjectionModule]): List of modules to unload

**Returns**: None

**Example**:
```python
KotInjection.unload_modules([old_module])
```

**Exceptions**:
- `NotInitializedError`: When `start()` has not been called

---

### KotInjectionCore

Class representing an isolated DI container instance.

#### `KotInjectionCore(modules: Optional[List[KotInjectionModule]] = None)`

**Description**: Initialize an isolated container instance.

**Parameters**:
- `modules` (Optional[List[KotInjectionModule]]): List of DI modules (optional)

**Example**:
```python
from kotinjection import KotInjectionCore, KotInjectionModule

module = KotInjectionModule()
with module:
    module.single[MyService](lambda: MyService())

app = KotInjectionCore(modules=[module])
```

---

#### `app.get[Type]()`

**Description**: Retrieve a dependency by type from this container instance.

**Type Parameters**:
- `Type`: The type to retrieve

**Returns**: Instance of the specified type

**Example**:
```python
app = KotInjectionCore(modules=[module])
service = app.get[MyService]()
```

**Exceptions**:
- `DefinitionNotFoundError`: When the specified type is not registered
- `ContainerClosedError`: When the container is closed

---

#### `app.load_modules(modules: List[KotInjectionModule])`

**Description**: Load modules into the container.

**Parameters**:
- `modules` (List[KotInjectionModule]): List of modules to load

**Returns**: None

**Example**:
```python
app = KotInjectionCore()
app.load_modules([module1, module2])
```

**Exceptions**:
- `ContainerClosedError`: When the container is already closed
- `DuplicateDefinitionError`: When a duplicate type registration exists

---

#### `app.unload_modules(modules: List[KotInjectionModule])`

**Description**: Unload modules from the container.

**Parameters**:
- `modules` (List[KotInjectionModule]): List of modules to unload

**Returns**: None

**Example**:
```python
app.unload_modules([old_module])
```

**Exceptions**:
- `ContainerClosedError`: When the container is closed

---

#### `app.close()`

**Description**: Close the container and clean up resources.

**Returns**: None

**Example**:
```python
app = KotInjectionCore(modules=[module])
# ... use ...
app.close()
```

**Notes**:
- After closing, dependencies cannot be retrieved from this container
- Using a context manager automatically closes the container

---

#### `app.is_closed`

**Description**: Returns whether the container is closed.

**Returns**: bool - True if closed

**Example**:
```python
app = KotInjectionCore()
print(app.is_closed)  # False

app.close()
print(app.is_closed)  # True
```

---

#### Context Manager Support

**Description**: Supports automatic resource management using `with` statement.

**Example**:
```python
with KotInjectionCore(modules=[module]) as app:
    service = app.get[MyService]()
    # ... use ...
# app.close() is called automatically here
```

---

### IsolatedKotInjectionComponent

Base class for components using an isolated container instance.

#### `get_app(self) -> KotInjectionCore`

**Description**: Returns the `KotInjectionCore` instance used by this component (abstract method).

**Returns**: KotInjectionCore

**Example**:
```python
from kotinjection import IsolatedKotInjectionComponent, KotInjectionCore

# Library-specific container
library_app = KotInjectionCore(modules=[library_module])

# Component base class
class LibraryComponent(IsolatedKotInjectionComponent):
    def get_app(self):
        return library_app

# Actual component
class MyService(LibraryComponent):
    def __init__(self):
        # Get dependencies from isolated container
        self.repository = self.get[Repository]()
```

---

#### `self.get`

**Description**: Property for retrieving dependencies.

**Type**: KotInjectionContainer

**Example**:
```python
class MyComponent(IsolatedKotInjectionComponent):
    def __init__(self):
        # Get dependencies using get[Type]() syntax
        self.service = self.get[MyService]()
        self.repo = self.get[Repository]()
```

---

### KotInjectionModule

Container for dependency definitions.

#### `KotInjectionModule()`

**Description**: Create a new module instance.

**Example**:
```python
module = KotInjectionModule()
```

---

#### `with module:`

**Description**: Module context manager. Define dependencies within this block.

**Example**:
```python
module = KotInjectionModule()
with module:
    module.single[MyService](lambda: MyService())
    module.factory[Handler](lambda: Handler())
```

---

#### `module.single[Type](factory: Callable)`

**Description**: Register a dependency with singleton scope.

**Type Parameters**:
- `Type`: The type to register

**Parameters**:
- `factory` (Callable): Factory function to create the instance

**Example**:
```python
# No dependencies
module.single[Database](lambda: Database())

# With dependencies
module.single[Repository](
    lambda: Repository(db=module.get())
)
```

**Notes**:
- Same instance is reused
- Factory is executed only once on first retrieval

---

#### `module.factory[Type](factory: Callable)`

**Description**: Register a dependency with factory scope.

**Type Parameters**:
- `Type`: The type to register

**Parameters**:
- `factory` (Callable): Factory function to create the instance

**Example**:
```python
# New instance created each time
module.factory[RequestHandler](
    lambda: RequestHandler(repo=module.get())
)
```

**Notes**:
- New instance is created on each retrieval
- Factory is executed every time

---

#### `module.get()`

**Description**: Type inference-based dependency resolution within factory functions.

**Returns**: Resolved dependency instance

**Example**:
```python
module = KotInjectionModule()
with module:
    module.single[Database](lambda: Database())
    module.single[Repository](
        lambda: Repository(db=module.get())
    )
```

**Notes**:
- Can only be used within factory functions
- Automatically infers type based on `__init__` type hints
- All parameters must have type hints

**Exceptions**:
- `ResolutionContextError`: When called outside a resolution context

---

## Lifecycle

### KotInjectionLifeCycle

Enum defining dependency lifecycles.

#### `KotInjectionLifeCycle.SINGLETON`

**Description**: Singleton scope. Same instance is reused.

**Example**:
```python
from kotinjection import KotInjectionLifeCycle

# Used internally (typically not used directly by users)
lifecycle = KotInjectionLifeCycle.SINGLETON
```

---

#### `KotInjectionLifeCycle.FACTORY`

**Description**: Factory scope. New instance created each time.

**Example**:
```python
from kotinjection import KotInjectionLifeCycle

lifecycle = KotInjectionLifeCycle.FACTORY
```

---

## Exceptions

All KotInjection exceptions inherit from `KotInjectionError`.

### KotInjectionError

**Description**: Base exception for all KotInjection errors. Catch this to handle any KotInjection error generically.

**Example**:
```python
from kotinjection import KotInjectionError

try:
    service = KotInjection.get[MyService]()
except KotInjectionError as e:
    print(f"DI error: {e}")
```

---

### TypeInferenceError

**Description**: Raised when type inference fails during registration or resolution.

**Common Causes**:
- Missing type hints on `__init__` parameters
- Using built-in types without accessible signatures

**Example**:
```python
from kotinjection import TypeInferenceError

# This will raise TypeInferenceError - missing type hints
class BadService:
    def __init__(self, db, cache):  # No type hints!
        pass

# Correct - all parameters have type hints
class GoodService:
    def __init__(self, db: Database, cache: CacheService):
        pass
```

---

## Advanced Usage

### How Type Inference Works

KotInjection leverages Python type hints to automatically resolve dependencies.

**Requirements**:
1. Type hints are required on all `__init__` method parameters
2. Use `module.get()` within factory functions

**Example**:
```python
class Service:
    # Type hints required on all parameters
    def __init__(self, repo: Repository, cache: CacheService):
        self.repo = repo
        self.cache = cache

module = KotInjectionModule()
with module:
    module.single[Repository](lambda: Repository())
    module.single[CacheService](lambda: CacheService())
    module.single[Service](
        # module.get() automatically resolves dependencies based on type hints
        lambda: Service(
            repo=module.get(),
            cache=module.get()
        )
    )
```

---

### Error Handling

#### Unregistered Type

```python
from kotinjection import DefinitionNotFoundError

try:
    service = KotInjection.get[UnregisteredService]()
except DefinitionNotFoundError as e:
    print(f"Error: {e}")
```

#### Access Before Initialization

```python
from kotinjection import NotInitializedError

try:
    service = KotInjection.get[MyService]()
except NotInitializedError as e:
    print(f"Error: {e}")
```

#### Circular Dependency

```python
from kotinjection import CircularDependencyError

# ServiceA depends on ServiceB
# ServiceB depends on ServiceA → Circular dependency

try:
    service = KotInjection.get[ServiceA]()
except CircularDependencyError as e:
    print(f"Error: {e}")
```

---

### Best Practices

#### 1. Module Separation

```python
# Database module
db_module = KotInjectionModule()
with db_module:
    db_module.single[Database](lambda: Database())

# Repository module
repo_module = KotInjectionModule()
with repo_module:
    repo_module.single[Repository](
        lambda: Repository(db=repo_module.get())
    )

# Service module
service_module = KotInjectionModule()
with service_module:
    service_module.single[Service](
        lambda: Service(repo=service_module.get())
    )

# Initialize all
KotInjection.start(modules=[db_module, repo_module, service_module])
```

#### 2. Library Development Isolation

```python
# Define library-specific container
library_app = KotInjectionCore(modules=[library_modules])

# Library base class
class LibraryComponent(IsolatedKotInjectionComponent):
    def get_app(self):
        return library_app

# Library public API
class LibraryAPI(LibraryComponent):
    def __init__(self):
        # Use isolated container
        self.service = self.get[LibraryService]()
```

#### 3. Testing Usage

```python
import unittest
from kotinjection import KotInjectionCore

class TestMyService(unittest.TestCase):
    def setUp(self):
        # Isolated container for testing
        self.app = KotInjectionCore(modules=[test_module])

    def tearDown(self):
        # Cleanup
        self.app.close()

    def test_service(self):
        service = self.app.get[MyService]()
        # Run tests...
```

---

## Summary

The KotInjection API provides a simple and intuitive DI container. With Context Isolation, it supports advanced use cases such as library development, multi-tenant applications, and test isolation.

For detailed usage examples, see [examples/context_isolation_example.py](../examples/context_isolation_example.py).
