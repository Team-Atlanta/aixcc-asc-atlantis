# Redia

*Redia* is a minimal re-implementation of *Aider*, aimed to be used as a Python library.

## Installation

```bash
poetry install
```

## Usage

```python
from pathlib import Path

from redia.code.contexts import CodingContext
from redia.code.models import Coder

if __name__ == "__main__":
    coder = Coder()

    context: CodingContext = {
        "api_key": "[API KEY]",
        "base_url": "[LITELLM BASEURL]",
        "max_tokens": 1024,
        "model": "gpt-3.5-turbo",
    }

    target = Path(__file__).parent / "redia" / "code" / "models.py"

    suggestion = coder.suggest("Rename `Coder` into `Beta`.", target)(context)
    print(suggestion)
    print("---")

    suggestion = coder.suggest("Add new methods recommended.", target)(context)
    print(suggestion)
    print("---")

    suggestion = coder.suggest("Add other methods recommended.", target)(context)
    print(suggestion)
    print("---")
```
