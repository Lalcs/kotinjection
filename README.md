# KotInjection

Koin-like Dependency Injection Container for Python

[![image](https://img.shields.io/pypi/v/Kotinjection.svg)](https://pypi.org/project/Kotinjection/)
[![image](https://img.shields.io/pypi/l/Kotinjection.svg)](https://pypi.org/project/Kotinjection/)
[![image](https://img.shields.io/pypi/pyversions/Kotinjection.svg)](https://pypi.org/project/Kotinjection/)
[![image](https://img.shields.io/github/contributors/lalcs/Kotinjection.svg)](https://github.com/lalcs/Kotinjection/graphs/contributors)
[![image](https://img.shields.io/pypi/dm/Kotinjection)](https://pypistats.org/packages/Kotinjection)
[![Unit Tests](https://github.com/Lalcs/Kotinjection/actions/workflows/unittest.yml/badge.svg)](https://github.com/Lalcs/Kotinjection/actions/workflows/unittest.yml)

**KotInjection** is a lightweight DI (Dependency Injection) container library for Python, inspired by
Kotlin's [Koin](https://insert-koin.io/). It features type inference-based automatic dependency resolution and
Koin-style DSL syntax.

## Features

- **Simple API** - Intuitive DSL similar to Koin
- **Type Inference Support** - Automatic dependency resolution using Python type hints
- **Lifecycle Management** - Supports singleton and factory patterns
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

# Factory (new instance created each time)
module.factory[RequestHandler](
    lambda: RequestHandler(repo=module.get())
)
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

| Class | Description |
|-------|-------------|
| `KotInjection` | Global DI container API |
| `KotInjectionCore` | Isolated container instance |
| `KotInjectionModule` | Dependency definitions container |
| `IsolatedKotInjectionComponent` | Base class for isolated components |

### Key Methods

```python
# Global API
KotInjection.start(modules=[...])    # Initialize
KotInjection.get[Type]()             # Retrieve dependency
KotInjection.stop()                  # Cleanup

# Module Definition
module.single[Type](factory)         # Singleton
module.factory[Type](factory)        # Factory
module.get()                         # Type inference in factories
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

## Comparison with Koin

| Feature           | Koin (Kotlin)               | KotInjection (Python)                   |
|-------------------|-----------------------------|-----------------------------------------|
| DSL Syntax        | `single { }`, `factory { }` | `module.single[T]`, `module.factory[T]` |
| Type Inference    | `get()`                     | `module.get()`                          |
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

