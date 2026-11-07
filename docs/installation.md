# Installation

## Requirements

The package metadata currently requires Python 3.9 or newer. Network access is needed for live provider data. TON Center and TONAPI keys are configurable; the code can also call public endpoints subject to their rate and access limits.

## From PyPI

```bash
python -m pip install --upgrade Tonviewer
```

Verify the package and import location:

```bash
python -c "import tonviewer; print(tonviewer.__version__); print(tonviewer.__file__)"
```

When working in a source checkout, the printed path should point to that checkout's `src/tonviewer` folder, not another environment's `site-packages` directory.

## From source

```bash
git clone https://github.com/z9zzzz/Tonviewer.git
cd Tonviewer
python -m pip install -e .
```

For local tests and development tools:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

The `dev` extra declares pytest, pytest-asyncio, pytest-cov, respx, and aioresponses. Use the same Python executable to install the environment and run the tests. For example, on Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

## Imports

The package import is lowercase, even though the PyPI distribution name is conventionally capitalized:

```python
import tonviewer
from tonviewer import TonviewerClient, Wallet, HashTx
```
