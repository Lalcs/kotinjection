"""
Test Fixtures

Common test classes used across test modules
"""


class Database:
    """Test database class"""

    def __init__(self):
        self.name = "TestDB"


class CacheService:
    """Test cache service"""

    def __init__(self):
        self.cache = {}


class UserRepository:
    """Test repository with dependencies"""

    def __init__(self, db: Database, cache: CacheService):
        self.db = db
        self.cache = cache


class CounterService:
    """Service with mutable state for testing singleton behavior"""

    def __init__(self):
        self.counter = 0

    def increment(self):
        self.counter += 1
        return self.counter


class ServiceWithoutHint:
    """Service with missing type hint - for error testing"""

    def __init__(self, dependency):  # No type hint!
        self.dependency = dependency


class ServiceWithPartialHints:
    """Service with partial type hints - for error testing"""

    def __init__(self, db: Database, cache):  # cache has no type hint
        self.db = db
        self.cache = cache


class Level1:
    """First level of nested dependencies"""
    pass


class Level2:
    """Second level of nested dependencies"""

    def __init__(self, l1: Level1):
        self.l1 = l1


class Level3:
    """Third level of nested dependencies"""

    def __init__(self, l2: Level2):
        self.l2 = l2


class Level4:
    """Fourth level of nested dependencies"""

    def __init__(self, l3: Level3):
        self.l3 = l3
