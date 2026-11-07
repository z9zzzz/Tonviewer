# Development and documentation

Install the project in editable mode with its development dependencies:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q src tests
```

Use the same Python interpreter for install and test commands. On PowerShell, run `.\.venv\Scripts\python.exe -m pytest -q` when using a local virtual environment.

The test suite uses local mocks for provider responses. Do not add examples that require a real API key or issue live financial requests during unit tests. Public API examples should state whether a method is sync or async, close clients, and label any example output as illustrative.

## Documentation changes

The landing page is `docs/README.md`; feature pages document the public methods and their results. When a method or model changes, update its feature page, `api-reference.md`, and a runnable example where appropriate. Keep the root README concise and link to the relevant guide. Avoid claiming support for methods that do not exist in the public source.
