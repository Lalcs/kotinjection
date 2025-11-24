"""
SingletonBuilder

Builder for singleton definitions
"""

from typing import TYPE_CHECKING

from .definition_builder import DefinitionBuilder
from .lifecycle import KotInjectionLifeCycle

if TYPE_CHECKING:
    from .module import KotInjectionModule


class SingletonBuilder(DefinitionBuilder):
    """Builder for singleton definitions"""

    def __init__(self, module: 'KotInjectionModule'):
        super().__init__(module, KotInjectionLifeCycle.SINGLETON)
