from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from .api.api import api_router
from .config import settings

# Create the FastAPI application instance
app = FastAPI(
    title="Email Intelligence Analyzer (EIA)",
    description="An automated system to analyze emails for business opportunities using NLP.",
    version="0.1.0"
)

# --- API Router ---
# Include the main API router, which holds all versioned API endpoints.
app.include_router(api_router, prefix="/api/v1")

# --- Frontend Serving ---
# Get the absolute path to the frontend directory.
# This makes the path resolution independent of where the script is run from.
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

# Check if the directory exists to avoid runtime errors.
if os.path.exists(frontend_dir):
    # Mount the 'static' directory to serve CSS, JS, etc. (if you add any)
    # This line is optional if you only have index.html but good practice.
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    # Serve the main index.html file for the root path
    @app.get("/", response_class=FileResponse, tags=["Frontend"])
    def read_index():
        """
        Serves the main Vue.js dashboard application.
        """
        return FileResponse(os.path.join(frontend_dir, "index.html"))
else:
    @app.get("/", tags=["Frontend"])
    def read_root_no_frontend():
        return {"status": "ok", "message": "Welcome to the EIA API. Frontend not found."}


# --- Development Server Runner ---
# This part allows running the app directly with `python -m eia.main` for development.
if __name__ == "__main__":
    import uvicorn

    if not settings:
        print("Could not load application settings. Please check your config.yml.")
    else:
        print(f"Starting server on http://{settings.server.host}:{settings.server.port}")
        uvicorn.run(
            "eia.main:app",
            host=settings.server.host,
            port=settings.server.port,
            reload=True # Reloads the server on code changes, great for development
        )