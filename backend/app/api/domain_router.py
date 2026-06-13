from collections.abc import Iterable

from fastapi import APIRouter

from app.api.legacy_routes import router as legacy_router


def build_domain_router(paths: Iterable[str]) -> APIRouter:
    router = APIRouter()
    wanted = set(paths)
    found: set[str] = set()

    for route in legacy_router.routes:
        path = getattr(route, "path", None)
        if path in wanted:
            router.routes.append(route)
            found.add(path)

    missing = wanted - found
    if missing:
        missing_paths = ", ".join(sorted(missing))
        raise RuntimeError(f"Missing legacy routes for domain router: {missing_paths}")

    return router

