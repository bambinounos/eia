from fastapi import APIRouter

from .endpoints import opportunities, tasks

# This is the main router that will include all other specific routers.
# This helps in organizing the API endpoints by functionality.

api_router = APIRouter()

# Include the router for opportunities.
# All endpoints defined in the 'opportunities' router will be prefixed with '/opportunities'.
# For example, the '/' endpoint in opportunities.py will become '/api/v1/opportunities/'.
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])


# Here you could add other routers as the application grows, for example:
# from .endpoints import stats
# api_router.include_router(stats.router, prefix="/stats", tags=["Statistics"])