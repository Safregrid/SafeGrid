"""
Shared pytest setup for SafeGrid.

Imported by pytest BEFORE any test module, so environment set here is visible
to app.core.config, which instantiates Settings() at import time.
"""

import os

# The FastAPI lifespan starts a grid refresh loop that calls the live
# Open-Meteo API. Tests must not do that: CI would become network-dependent
# and a test session would write to the shared safegrid.db on a timer.
# Each test opts back in where needed by monkeypatching the flag.
os.environ["grid_scheduler_enabled"] = "false"
