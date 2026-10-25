# Local container scripts

This directory contains platform-specific wrappers around Docker Compose:

- `start-mac.sh` and `start-linux.sh` build and start the app in the background.
- `stop-mac.sh` and `stop-linux.sh` stop/remove the app container while preserving the named `pm-data` volume.
- `start-windows.ps1` and `stop-windows.ps1` provide the same operations in PowerShell.

The scripts resolve the project root relative to their own location. Keep them limited to Compose lifecycle commands; use `docker compose down -v` only when intentionally removing persistent database data.