"""Framework profile config: per-profile module subset, path adds, payload adds."""
from __future__ import annotations

CAKEPHP_PATHS = [
    "/webroot/debug_kit/",
    "/debug-kit/",
    "/logs/",
    "/tmp/",
    "/config/app.php",
    "/config/app_local.php",
]

# Sprint 2 slot: --django, --laravel, --rails will land here as
# CAKEPHP_PATHS-equivalent lists. Each profile is config — no engine plumbing.
# Example future shape:
# DJANGO_PATHS = ["/static/admin/", "/__debug__/", ...]
# LARAVEL_PATHS = ["/storage/logs/laravel.log", "/.env.example", ...]
# RAILS_PATHS = ["/rails/info/properties", "/rails/info/routes", ...]
