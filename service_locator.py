"""Service Locator pattern implementation for dependency management.

This module provides a central registry for all singleton service instances
in the application, eliminating the need for global variables.
"""

from functools import lru_cache
from typing import Any, ClassVar, Optional, TypeVar, cast

# Generic type for service instances
T = TypeVar("T")


class ServiceLocator:
    """Service locator pattern implementation.

    This class provides a central registry for all singleton service instances
    in the application, eliminating the need for global variables.
    """

    _instance: ClassVar[Optional["ServiceLocator"]] = None
    _services: ClassVar[dict[str, Any]] = {}

    def __new__(cls) -> "ServiceLocator":
        """Ensure singleton behavior for the ServiceLocator itself."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls: type["ServiceLocator"], name: str, instance: Any) -> None:
        """Register a service instance with the locator.

        Args:
            name: The name to register the service under
            instance: The service instance to register
        """
        cls._services[name] = instance

    @classmethod
    def get(
        cls: type["ServiceLocator"], name: str, factory_func: Optional[callable] = None
    ) -> Any:
        """Get a service instance by name, creating it if needed.

        Args:
            name: The name of the service to retrieve
            factory_func: Optional function to create the service if it doesn't exist

        Returns:
            The requested service instance

        Raises:
            KeyError: If the service doesn't exist and no factory_func is provided
        """
        if name not in cls._services and factory_func is not None:
            cls._services[name] = factory_func()

        if name in cls._services:
            return cls._services[name]

        raise KeyError(f"No service registered for '{name}' and no factory provided")

    @classmethod
    def get_typed(
        cls: type["ServiceLocator"],
        name: str,
        expected_type: type[T],
        factory_func: Optional[callable] = None,
    ) -> T:
        """Get a service instance with type checking.

        Args:
            name: The name of the service to retrieve
            expected_type: The expected type of the service
            factory_func: Optional function to create the service if it doesn't exist

        Returns:
            The requested service instance with correct type

        Raises:
            TypeError: If the service is not of the expected type
        """
        service = cls.get(name, factory_func)
        if not isinstance(service, expected_type):
            raise TypeError(
                f"Service '{name}' is not of expected type {expected_type.__name__}"
            )
        return cast("T", service)

    @classmethod
    def clear(cls: type["ServiceLocator"]) -> None:
        """Clear all registered services (mainly for testing)."""
        cls._services.clear()


# Create a singleton instance
service_locator = ServiceLocator()


@lru_cache
def get_settings() -> Any:
    """Get cached settings instance."""
    from config.settings import Settings

    return Settings()
