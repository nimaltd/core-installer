# core-installer

[![CI](https://github.com/nimaltd/core-installer/actions/workflows/ci.yml/badge.svg)](https://github.com/nimaltd/core-installer/actions/workflows/ci.yml)

The shared core of [stm32-installer](https://github.com/nimaltd/stm32-installer) and [zephyr-installer](https://github.com/nimaltd/zephyr-installer): everything an installer does that does not depend on the kind of project.

You do not install this yourself. Install one of the installers, and this comes inside it.

---

## What it does

- **Fetches a library** from GitHub by `owner/name`, from a GitHub address, from the zip GitHub's **Download ZIP** gives, or from a folder. A bad connection is tried again, five times across two GitHub hosts, and a private repository is read with a token given with `--key` or in `GITHUB_TOKEN`. A token that can see the repository but not read it is told exactly which permission to add.
- **Reads the library's `installer.yml`**: what it is, what it needs, and which files make it up.
- **Installs what a library needs first.** A library listed under `requires.libraries` that is missing or too old goes in before it. One already in the project at a version that will do is left alone. Everything is fetched before anything is installed, so a library that cannot be had leaves the project as it was.
- **Asks about options**, the parts of a library a project may or may not want.
- **Copies the files** into the project, and keeps what the user wrote between `USER CODE BEGIN` and `USER CODE END` on every update.
- **Remembers what it installed**, and where, in a record file in the project, so an update knows what to replace and what to remove.
- **Uninstalls a library** with `--uninstall`: out of the build through the installer's `Target`, then its files, saving first what the user wrote in them. A library another one needs stays.
- **Runs the command line**: the questions, the output, `--ref`, `--dir`, `--with`, `--without`, `--key` and `--uninstall`.

What a project looks like, the requirements checked against it, and how a library is registered with its build, are the installer's own. The core asks for them through a `Target`.

---

## For someone writing an installer

Each installer takes this repository in whole as a git submodule, at `src/core`, so the core is built into the installer's own wheel. The installer then still installs from one file, with no internet and nothing else to fetch.

```bash
git submodule add https://github.com/nimaltd/core-installer.git src/core
```

The installer's package is the `src` folder itself, mapped in its `pyproject.toml`, with the core listed beside it:

```toml
[tool.setuptools]
package-dir = { "example_installer" = "src" }
packages = ["example_installer", "example_installer.core"]
```

It describes its kind of project in a `Target`, and hands it to the core before anything else runs, in the package's `__init__.py`:

```python
from .core import target
from .core.target import Target


class Example(Target):
    name = "example-installer"           # the command, as messages name it
    version = "1.0.0"                    # what requires.example_installer is compared with
    requires_key = "example_installer"   # the key under requires for that; default installer
    record_name = ".example-installer.json"  # the record of what was installed
    project = "example project"          # the user's project, in the help
    integrations = ()                    # what --ide can pick; none means no --ide
    no_project = "No project file was recognised here."  # said when nothing matched
    no_project_hint = "Add the folder to your build."    # and what to do instead

    def add_arguments(self, parser):
        """Command line options of its own, added to the core's argparse parser."""

    def take_arguments(self, args, ask):
        """What they were given as. ask(prompt) asks the user, None when nobody can answer."""

    def default_folder(self, library):
        """The folder offered for a library installed for the first time."""
        return library.name

    def read_manifest(self, manifest, data):
        """Read this target's own section of installer.yml onto manifest."""

    def read_requirements(self, requirements, data):
        """Read this target's part of requires onto requirements."""

    def requirements_empty(self, requirements):
        """Whether that part asks for nothing."""
        return True

    def warnings(self, manifest):
        """Values in installer.yml this target does not know, as sentences."""
        return []

    def check(self, library, project_root):
        """What the project is missing for this library, as a list of Finding."""
        return []

    def integrate(self, project_root, library, destination, only=None, dropped=(),
                  dropped_defines=()):
        """Register the library with the project's build. A list of Outcome."""
        return []

    def uninstall(self, project_root, library):
        """Take it out of the build again, before its files go. A list of Outcome."""
        return []


target.use(Example())
```

Then the installer's command is the core's:

```python
from .core.cli import main
```

The core reads `target.current` each time it needs an answer, so `use()` has to come first, before anything of the core runs.

A `Finding` is one line under **Requirements**: `OK`, `WARN` or `INFO`, a message, and a hint for what to do. An `Outcome` is one line under **Project**: which build it was, `CHANGED`, `ALREADY` or `MANUAL`, a message, the steps left to the user, and the backup taken before the edit. Before changing a file of the project, take a copy with `files.backup(path)`.

---

## Running the tests

```bash
python test/run_tests.py
```

The tests load this folder as the package `core_installer`, with a target of its own that registers nothing, so they cover the core alone. What every installer does with it is tested in the installer. CI runs these tests, and the whole suite of every installer, stm32-installer and zephyr-installer, with this core in place of its own.

---

## Support

I write these tools and libraries in my own time and give them away, because good tools should be easy to get. If this one saved you an afternoon, there are two things that genuinely help:

**Star the repo.** It costs you one click, it helps other engineers find the tool, and it is the main reason I keep going.

**[Buy me a coffee on Ko-fi](https://ko-fi.com/nimaltd).** Any amount is a real motivation to keep writing, documenting and maintaining this work.

[![GitHub](https://img.shields.io/badge/GitHub-Follow-black?style=for-the-badge&logo=github)](https://github.com/NimaLTD)
[![YouTube](https://img.shields.io/badge/YouTube-Subscribe-red?style=for-the-badge&logo=youtube)](https://youtube.com/@nimaltd)
[![Instagram](https://img.shields.io/badge/Instagram-Follow-purple?style=for-the-badge&logo=instagram)](https://instagram.com/github.nimaltd)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue?style=for-the-badge&logo=linkedin)](https://linkedin.com/in/nimaltd)
[![Email](https://img.shields.io/badge/Email-Contact-red?style=for-the-badge&logo=gmail)](mailto:nima.askari@gmail.com)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-orange?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/nimaltd)

---

## License

Apache License 2.0. See [LICENSE](LICENSE).
