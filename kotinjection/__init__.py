# Public API
from .api import KotInjection
from .component import IsolatedKotInjectionComponent
from .context import KotInjectionContext
from .core import KotInjectionCore
from .exceptions import (
    AlreadyStartedError,
    CircularDependencyError,
    ContainerClosedError,
    DefinitionNotFoundError,
    DuplicateDefinitionError,
    KotInjectionError,
    NotInitializedError,
    ResolutionContextError,
    TypeInferenceError,
)
from .global_context import GlobalContext
from .inject_descriptor import InjectDescriptor
from .inject_proxy import create_inject
from .lifecycle import KotInjectionLifeCycle
from .module import KotInjectionModule

__all__ = [
    "KotInjection",
    "KotInjectionCore",
    "IsolatedKotInjectionComponent",
    "KotInjectionContext",
    "GlobalContext",
    "KotInjectionModule",
    "KotInjectionLifeCycle",
    # Inject
    "InjectDescriptor",
    "create_inject",
    # Exceptions
    "KotInjectionError",
    "AlreadyStartedError",
    "NotInitializedError",
    "ContainerClosedError",
    "DuplicateDefinitionError",
    "DefinitionNotFoundError",
    "CircularDependencyError",
    "TypeInferenceError",
    "ResolutionContextError",
]

# Version will be dynamically set by poetry-dynamic-versioning
try:
    from ._version import __version__
except ImportError:
    # Fallback for development
    __version__ = '0.0.0'
