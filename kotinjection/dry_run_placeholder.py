"""
DryRunPlaceholder

A placeholder class used during dry-run factory execution for type discovery.
"""

from typing import Any


class DryRunPlaceholder:
    """
    Placeholder for dry-run factory execution.

    This class accepts any method call or attribute access,
    always returning a new placeholder instance.
    """

    def __getattr__(self, name: str) -> "DryRunPlaceholder":
        """Accept any attribute access."""
        return DryRunPlaceholder()

    def __call__(self, *args: Any, **kwargs: Any) -> "DryRunPlaceholder":
        """Accept any method call."""
        return DryRunPlaceholder()

    def __repr__(self) -> str:
        return "<DryRunPlaceholder>"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, DryRunPlaceholder)

    def __ne__(self, other: Any) -> bool:
        return not isinstance(other, DryRunPlaceholder)

    def __bool__(self) -> bool:
        return True

    def __iter__(self) -> "DryRunPlaceholder":
        return self

    def __next__(self) -> None:
        raise StopIteration

    def __enter__(self) -> "DryRunPlaceholder":
        return self

    def __exit__(self, *args: Any) -> None:
        pass
