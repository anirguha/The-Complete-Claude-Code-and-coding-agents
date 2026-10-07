# The Complete Agent and MCP Course

## MCP trading dashboard

With your course virtual environment activated, run:

```sh
cd Exercises/mcp
uv run --active app.py
```

Put `--active` before `app.py`: it is a uv option, not a script argument.
This command syncs the project dependencies, including Plotly, into the active
environment before starting the dashboard. To use the project's `.venv` instead,
omit `--active`.