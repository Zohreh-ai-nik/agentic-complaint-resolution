"""API blueprints for the Function App.

Each submodule exposes a ``bp`` object (an ``azure.functions.Blueprint``) that
``function_app.py`` registers. Keeping routes in blueprints keeps the entry
point small and the routes grouped by concern.
"""
