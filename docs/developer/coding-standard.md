# Coding standard

Back to: [Developer documentation](README.md) · [Documentation home](../README.md)

## Rules

1. **One class per module.** Modules without a class (constants, entry
   functions) are allowed. Not checked by a tool; checked in review.
2. **Docstrings everywhere,** Google style, with `Args`, `Returns`, `Raises`
   for every function, method, class and module, tests included. Enforced by
   pylint with `docparams`.
3. **Comments explain why,** not what. A comment that repeats the code is
   removed.
4. **Type hints complete;** `mypy --strict` must pass.
5. **Collaborators through the constructor** (dependency injection); no
   global state, no singletons except Qt's application object.
6. **External programs** are called with an argument list, the path from
   `shutil.which`, never through a shell, `check=` always explicit.
7. **Originals are never overwritten;** every processing step writes a new
   file.
8. **User-visible text in English;** translations follow with Qt translation
   files.
9. **No private data** (addresses, host names, user names, album names) in
   code, tests, documentation or commit messages.

## Measurable limits

Configured in `pyproject.toml`, enforced by gate 2 (lint) and gate 1 (format).

| Limit | Value | pylint option | pylint default |
|---|---|---|---|
| Line length | 100 | `max-line-length` (and pycodestyle) | 100 |
| Lines per module | 400 | `max-module-lines` | 1000 |
| Arguments per function | 5 | `max-args`, `max-positional-arguments` | 5 |
| Local variables | 15 | `max-locals` | 15 |
| Statements per function | 30 | `max-statements` | 50 |
| Branches per function | 10 | `max-branches` | 12 |
| Cyclomatic complexity | 10 | `max-complexity` (extension `mccabe`) | 10 |
| Public methods per class | 1 to 10 | `min-public-methods`, `max-public-methods` | 2 / 20 |

The defaults were read from `pylint --generate-toml-config` (pylint 4.1.3).
`min-public-methods = 1` because a class with a single public method is the
normal case for a single-responsibility class.

## Patterns

Gang-of-Four patterns are used where a real variation point exists (scanner
backends, page order, encoders, exporters, detection); the table is in
[concept chapter 5.2](../concept/scanbench-concept.md#classes-and-patterns).
A pattern without a variation point is not added.
