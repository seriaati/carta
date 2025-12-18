import importlib
import inspect
import pkgutil

from fastapi import APIRouter, FastAPI
from loguru import logger


def discover_routers(
    package_name: str = "app.api", prefix: str = "/api", recursive: bool = True
) -> list[tuple[APIRouter, str]]:
    """
    Discover all router instances in a package.

    Args:
        package_name: The package to scan for routers.
        prefix: The prefix to add to all routes.
        recursive: Whether to recursively scan subpackages.

    Returns:
        A list of tuples containing the router instance and its subpath (if any).
    """
    routers: list[tuple[APIRouter, str]] = []

    # Import the package to scan
    package = importlib.import_module(package_name)
    package_path = getattr(package, "__path__", None)

    if not package_path:
        logger.warning(f"Cannot scan {package_name} for routers as it's not a package")
        return routers

    # Iterate through all modules in the package
    for _, module_name, is_pkg in pkgutil.iter_modules(package_path):
        full_module_name = f"{package_name}.{module_name}"

        # If it's a package and recursive is True, scan the subpackage
        if is_pkg and recursive:
            sub_routers = discover_routers(
                package_name=full_module_name, prefix=prefix, recursive=recursive
            )
            routers.extend(sub_routers)
            continue

        try:
            # Import the module
            module = importlib.import_module(full_module_name)

            # Find all router instances in the module
            for _, obj in inspect.getmembers(module):
                if isinstance(obj, APIRouter):
                    # Extract subpath from module name for more organized nesting (optional)
                    # e.g., app.controllers.v1.auth -> /v1
                    parts = package_name.split(".")
                    if len(parts) > 2:  # app.controllers.{part}
                        subpath = f"/{parts[2]}" if parts[2] != "__init__" else ""
                    else:
                        subpath = ""

                    routers.append((obj, subpath))
                    logger.info(f"Discovered router in {full_module_name}")

        except (ImportError, AttributeError) as e:
            logger.error(f"Error importing module {full_module_name}: {e}")

    return routers


def register_routers(app: FastAPI, prefix: str = "/api") -> None:
    """
    Register all routers in the app.controllers package with the FastAPI app.

    Args:
        app: The FastAPI app.
        prefix: The prefix to add to all routes.
    """
    routers = discover_routers(prefix=prefix)

    for router, subpath in routers:
        full_prefix = f"{prefix}{subpath}"
        app.include_router(router, prefix=full_prefix)
