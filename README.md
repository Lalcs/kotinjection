# KotInjection

[![image](https://img.shields.io/pypi/v/kotinjection.svg)](https://pypi.org/project/kotinjection/)
[![image](https://img.shields.io/pypi/l/kotinjection.svg)](https://pypi.org/project/kotinjection/)
[![image](https://img.shields.io/pypi/pyversions/kotinjection.svg)](https://pypi.org/project/kotinjection/)
[![image](https://img.shields.io/github/contributors/lalcs/kotinjection.svg)](https://github.com/lalcs/kotinjection/graphs/contributors)
[![image](https://img.shields.io/pypi/dm/kotinjection)](https://pypistats.org/packages/kotinjection)
[![Unit Tests](https://github.com/Lalcs/kotinjection/actions/workflows/unittest.yml/badge.svg)](https://github.com/Lalcs/kotinjection/actions/workflows/unittest.yml)

Koin-like Dependency Injection Container for Python

**KotInjection** is a lightweight DI (Dependency Injection) container library for Python, inspired by
Kotlin's [Koin](https://insert-koin.io/). It features type inference-based automatic dependency resolution and
Koin-style DSL syntax.

## Features

- **Simple API** - Intuitive DSL similar to Koin
- **Type Inference Support** - Automatic dependency resolution using Python type hints
- **Lifecycle Management** - Supports singleton and factory patterns
- **Eager Initialization** - Optional `created_at_start` for singleton pre-loading (like Koin)
- **Lazy Injection** - Class attribute lazy dependency injection (like Koin's `by inject()`)
- **Context Isolation** - Independent container instances for isolated DI contexts
- **Lightweight** - Pure Python implementation with no external dependencies
- **Type Safe** - Safe dependency management through type hints

## Installation

```bash
pip install kotinjection
```

## Quick Start

### Basic Usage

```python
from kotinjection import KotInjection, KotInjectionModule


# Define dependencies
class Database:
    def __init__(self):
        self.connection = "db://localhost"


class UserRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_users(self):
        return f"Users from {self.db.connection}"


# Create a module
module = KotInjectionModule()
with module:
    module.single[Database](lambda: Database())
    module.single[UserRepository](
        lambda: UserRepository(db=module.get())
    )

# Initialize the DI container
KotInjection.start(modules=[module])

# Retrieve dependencies
repo = KotInjection.get[UserRepository]()
print(repo.get_users())  # "Users from db://localhost"

# Stop when done
KotInjection.stop()
```

### Lifecycle Management

```python
# Singleton (same instance is reused)
module.single[Database](lambda: Database())

# Singleton with type (auto-instantiated with dependency resolution)
module.single[IDatabase](PostgresDatabase)

# Factory (new instance created each time)
module.factory[RequestHandler](
    lambda: RequestHandler(repo=module.get())
)

# Factory with type (auto-instantiated)
module.factory[RequestHandler](RequestHandler)
```

### Eager Initialization

By default, singletons are lazily initialized on first access. Use `created_at_start=True` to initialize at `start()` time.

```python
# Definition level - specific singleton is eagerly initialized
module.single[Database](lambda: Database(), created_at_start=True)

# Module level - all singletons in this module are eagerly initialized
module = KotInjectionModule(created_at_start=True)
with module:
    module.single[Database](lambda: Database())  # Eager
    module.single[Cache](lambda: Cache(), created_at_start=False)  # Override: Lazy
```

### Lazy Injection (Class Attributes)

Similar to Koin's `by inject()`, you can define dependencies as class attributes that are resolved lazily on first access.

```python
from kotinjection import KotInjection

class MyService:
    # Dependency is resolved on first access, not at class definition time
    repository = KotInjection.inject[UserRepository]

    def get_users(self):
        return self.repository.get_users()

# Initialize after class definition
KotInjection.start(modules=[module])

# Dependency is resolved when accessed
service = MyService()
service.get_users()  # repository is resolved here
```

## Context Isolation

Context Isolation provides independent DI container instances that are completely separate from the global container.
Ideal for library development, multi-tenant applications, and test isolation.

### Basic Usage

```python
from kotinjection import KotInjectionCore, KotInjectionModule

# Create an isolated container instance
module = KotInjectionModule()
with module:
    module.single[MyService](lambda: MyService())

app = KotInjectionCore(modules=[module])

# Retrieve dependencies from the instance
service = app.get[MyService]()
```

### Use Case 1: Library Development

Create libraries that don't conflict with the host application's DI.

```python
from kotinjection import (
    KotInjectionCore,
    IsolatedKotInjectionComponent,
    KotInjectionModule
)

# Define a library-specific container
library_module = KotInjectionModule()
with library_module:
    library_module.single[LibraryRepository](lambda: LibraryRepository())

library_app = KotInjectionCore(modules=[library_module])


# Base class for library components
class LibraryComponent(IsolatedKotInjectionComponent):
    def get_app(self):
        return library_app


# Actual service class
class MyLibraryService(LibraryComponent):
    def __init__(self):
        # Get dependencies from the isolated container
        self.repository = self.get[LibraryRepository]()

    def do_something(self):
        return self.repository.fetch_data()
```

### Use Case 2: Multi-Tenant

Each tenant can have an independent DI environment.

```python
# Tenant 1's container
tenant1_app = KotInjectionCore(modules=[tenant1_module])

# Tenant 2's container
tenant2_app = KotInjectionCore(modules=[tenant2_module])

# Use independent dependencies for each tenant
tenant1_service = tenant1_app.get[Service]()
tenant2_service = tenant2_app.get[Service]()
```

### Use Case 3: Test Isolation

Use an independent DI container for each test case.

```python
import unittest
from kotinjection import KotInjectionCore


class TestMyService(unittest.TestCase):
    def test_with_isolated_container(self):
        # Test-specific isolated container
        with KotInjectionCore(modules=[test_module]) as app:
            service = app.get[MyService]()
            # Run tests...
        # Automatically cleaned up when exiting the context
```

## API Reference

For complete API documentation, see [API Reference](docs/api_reference.md).

### Quick Reference

| Class                           | Description                           |
|---------------------------------|---------------------------------------|
| `KotInjection`                  | Global DI container API               |
| `KotInjectionCore`              | Isolated container instance           |
| `KotInjectionModule`            | Dependency definitions container      |
| `IsolatedKotInjectionComponent` | Base class for isolated components    |
| `create_inject`                 | Create inject proxy for isolated containers |

### Key Methods

```python
# Global API
KotInjection.start(modules=[...])  # Initialize
KotInjection.get[Type]()  # Retrieve dependency (eager)
KotInjection.inject[Type]  # Lazy injection (class attribute)
KotInjection.stop()  # Cleanup

# Module Definition
module = KotInjectionModule(created_at_start=True)  # Eager init for all singletons
module.single[Type](factory)  # Singleton with factory (lazy by default)
module.single[Type](ImplType)  # Singleton with type (auto-instantiated)
module.single[Type](factory, created_at_start=True)  # Singleton (eager)
module.factory[Type](factory)  # Factory with factory function
module.factory[Type](ImplType)  # Factory with type (auto-instantiated)
module.get()  # Type inference in factories
module.get[Type]()  # Explicit type resolution (for third-party libs)

# Isolated Container
create_inject(app)  # Create inject proxy for isolated containers
```

## Advanced Usage

### Multiple Modules

```python
# Database module
db_module = KotInjectionModule()
with db_module:
    db_module.single[Database](lambda: Database())
    db_module.single[CacheService](lambda: CacheService())

# Repository module
repo_module = KotInjectionModule()
with repo_module:
    repo_module.single[UserRepository](
        lambda: UserRepository(
            db=repo_module.get(),
            cache=repo_module.get()
        )
    )

# Initialize with all modules
KotInjection.start(modules=[db_module, repo_module])
```

### Type Inference with Isolated Containers

```python
# Create the app first
app = KotInjectionCore()

# Use module.get() in module definitions
module = KotInjectionModule()
with module:
    module.single[Repository](lambda: Repository())
    module.single[Service](lambda: Service(repo=module.get()))

# Load modules
app.load_modules([module])

# Retrieve dependencies
service = app.get[Service]()
```

### Mixing Manual Instances with Type Inference

`module.get()` resolves dependencies based on sequential call order. When mixing manually instantiated objects with `module.get()`, **use keyword arguments** for clarity.

#### Pattern That Doesn't Work

When `module.get()` call order doesn't match parameter order, type inference fails:

```python
class UserRepository:
    def __init__(self, redis: Redis, db: Database):
        ...

# module.get() returns Redis (index 0), but we want Database!
module.single[UserRepository](
    lambda: UserRepository(Redis(host="localhost"), module.get())
)
```

#### Recommended: Use Keyword Arguments

```python
module.single[UserRepository](
    lambda: UserRepository(redis=Redis(host="localhost"), db=module.get())
)
```

#### Alternative: Use Index Parameter

Specify the parameter index explicitly with `module.get(index)`:

```python
# module.get(1) resolves the second parameter (Database)
module.single[UserRepository](
    lambda: UserRepository(Redis(host="localhost"), module.get(1))
)
```

### Explicit Type Resolution with `module.get[Type]()`

When using third-party libraries in factory functions, DryRun mode may cause errors because `module.get()` returns a placeholder object during type discovery.

#### The Problem

```python
from sqlalchemy import create_engine

class Config:
    DATABASE_URI = "postgresql://localhost/db"

class DatabaseClient:
    def __init__(self, config: Config):
        # create_engine expects a real string, but during DryRun
        # module.get() returns a DryRunPlaceholder!
        self.engine = create_engine(config.DATABASE_URI)

module = KotInjectionModule()
with module:
    module.single[Config](lambda: Config())
    module.single[DatabaseClient](
        lambda: DatabaseClient(module.get())  # Error during DryRun!
    )
```

#### The Solution: Use `module.get[Type]()`

Use explicit type specification to resolve the actual instance even during DryRun:

```python
module = KotInjectionModule()
with module:
    module.single[Config](lambda: Config())
    # get[Config]() returns the actual Config instance, not a placeholder
    module.single[DatabaseClient](
        lambda: DatabaseClient(module.get[Config]())  # Works!
    )
```

#### When to Use

| Syntax | DryRun Behavior | Use When |
|--------|-----------------|----------|
| `module.get()` | Returns `DryRunPlaceholder` | Dependency is stored/passed without immediate use |
| `module.get[Type]()` | Returns **actual instance** | Value is used immediately (e.g., passed to third-party libraries) |

#### Mixing Both Styles

You can mix `module.get()` and `module.get[Type]()` in the same factory:

```python
class Service:
    def __init__(self, config: Config, db: Database):
        self.uri = config.DATABASE_URI  # Uses config immediately
        self.db = db  # Just stores reference

module.single[Service](lambda: Service(
    module.get[Config](),  # Explicit type - actual instance
    module.get()           # Type inference - placeholder OK
))
```

## Comparison with Koin

| Feature           | Koin (Kotlin)               | KotInjection (Python)                   |
|-------------------|-----------------------------|-----------------------------------------|
| DSL Syntax        | `single { }`, `factory { }` | `module.single[T]`, `module.factory[T]` |
| Type Inference    | `get()`                     | `module.get()`                          |
| Lazy Injection    | `by inject()`               | `KotInjection.inject[T]`                |
| Context Isolation | `koinApplication { }`       | `KotInjectionCore()`                    |
| Scope Management  | Multiple scopes             | Singleton/Factory only                  |
| Context Manager   | N/A                         | `with` statement support                |

## Development Guidelines

### Running Tests

```bash
python -m unittest discover tests
```

### Type Hints

All type hints are required for dependency resolution.

```python
class MyService:
    def __init__(self, repo: Repository):  # Type hint required
        self.repo = repo
```

## License

MIT License

## Acknowledgements

This project is inspired by Kotlin's [Koin](https://insert-koin.io/).

