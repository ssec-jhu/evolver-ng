import json

from fastapi.openapi.utils import get_openapi

from evolver.app.main import app

# Generate OpenAPI schema
openapi_schema = get_openapi(
    title=app.title,
    version=app.version,
    openapi_version=app.openapi_version,
    description=app.description,
    routes=app.routes,
)

# Save the schema to a JSON file
with open("openapi.json", "w") as f:
    json.dump(openapi_schema, f, indent=2)
