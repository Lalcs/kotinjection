# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KotInjection is a Koin-like lightweight DI (Dependency Injection) container library for Python. It features type inference-based automatic dependency resolution and Koin-style DSL syntax.

## Development Commands

### Setup
```bash
poetry install
```

### Run Tests
```bash
python -m unittest discover tests
```

### Run Single Test
```bash
python -m unittest tests.test_class_based_api.TestKotInjectionSingleton
```

### Run Tests with Coverage
```bash
coverage run -m unittest discover tests && coverage report
```

## Architecture

### Core Components

```
kotinjection/
├── api.py              # KotInjection - Global API (wrapper for KotInjectionCore)
├── core.py             # KotInjectionCore - Isolated container instance
├── container.py        # KotInjectionContainer - DI container with resolution logic
├── module.py           # KotInjectionModule - Dependency definition container
├── definition.py       # Definition - Dependency definition data class
├── singleton_builder.py # DSL builder for singleton scope
├── factory_builder.py  # DSL builder for factory scope
├── resolution_context.py # Type inference resolution context
├── context.py          # ContextVar for resolution context
├── exceptions.py       # Custom exception hierarchy
├── lifecycle.py        # KotInjectionLifeCycle enum
├── get_proxy.py        # Proxy for get[Type]() syntax
└── component.py        # IsolatedKotInjectionComponent base class
```

### Dependency Flow

```
KotInjection (Global API)
    └── KotInjectionCore (Container Instance)
            └── KotInjectionContainer (Resolution Logic)
                    └── Definition (Type + Factory + Lifecycle)
```

### Key Design Patterns

1. **Type Inference**: Uses Python type hints to automatically resolve dependencies via `get_func()` or `module.get()`
2. **Context Isolation**: `KotInjectionCore` provides completely isolated DI containers
3. **DSL Syntax**: `module.single[Type]()` and `module.factory[Type]()` for Koin-like registration
4. **Subscript Syntax**: `KotInjection.get[Type]()` using `__getitem__` for type-safe retrieval

### Exception Hierarchy

- `KotInjectionError` (base)
  - `NotInitializedError`
  - `ContainerClosedError`
  - `DuplicateDefinitionError`
  - `DefinitionNotFoundError`
  - `CircularDependencyError`
  - `TypeInferenceError`
  - `ResolutionContextError`

## Type Hints Requirement

All dependencies must have proper type hints on `__init__` parameters for type inference to work:

```python
class UserRepository:
    def __init__(self, db: Database, cache: CacheService):  # Type hints required
        self.db = db
        self.cache = cache
```
