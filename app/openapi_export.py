"""Write the OpenAPI document to a file without starting a server.

    uv run python -m app.openapi_export ../../packages/api-client/openapi/openapi.json

The frontend API client is generated from this file (``nx run api-client:generate``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.core.config import Settings
from app.main import create_app


def export(path: Path) -> None:
    # Fixed settings so the document is reproducible regardless of the caller's environment.
    app = create_app(Settings(app_env="local", docs_enabled=True, service_version="v1", _env_file=None))
    schema = app.openapi()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    export(target)
    sys.stderr.write(f"OpenAPI written to {target}\n")
