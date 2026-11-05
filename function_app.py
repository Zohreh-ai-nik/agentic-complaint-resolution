"""Function App entry point.

The Azure Functions Python v2 model discovers a single ``app`` object here and
wires up every trigger registered on the blueprints we import. Keeping the entry
point tiny makes the API easy to read: one line per concern.
"""

from __future__ import annotations

import azure.functions as func

from src.api import complaints, health, search

app = func.FunctionApp()

# Each blueprint groups related routes (see src/api/).
app.register_blueprint(health.bp)
app.register_blueprint(complaints.bp)
app.register_blueprint(search.bp)
