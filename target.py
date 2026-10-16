"""
What one installer adds to the shared core.

The core fetches a library, reads its installer.yml, copies its files and keeps
what the user wrote. What a project looks like belongs to each installer:
STM32CubeIDE, Keil and IAR for one, Zephyr's CMake and Kconfig for another. So
each installer fills in a Target and hands it to use() before anything else
runs, and the core asks it wherever the answer depends on the kind of project.

Read it as target.current at the time of use, never imported by name: an
import would keep the default it found then.
"""

# How seriously to take a Finding.
OK = "ok"
WARN = "warn"
INFO = "info"

# What an integration did to the project.
CHANGED = "changed"
ALREADY = "already"
MANUAL = "manual"
SKIPPED = "skipped"


class Finding:
    """One observation about the project, with how seriously to take it."""

    def __init__(self, level, message, hint=""):
        self.level = level
        self.message = message
        self.hint = hint

    def __repr__(self):
        return f"Finding({self.level}, {self.message!r})"


class Outcome:
    """What an integration did, and what the user still has to do themselves."""

    def __init__(self, ide, status, message, steps=None, backup=None):
        self.ide = ide
        self.status = status
        self.message = message
        self.steps = steps or []
        self.backup = backup

    @property
    def needs_user(self):
        return self.status == MANUAL

    def __repr__(self):
        return f"Outcome({self.ide}, {self.status})"


class Target:
    """The answers that depend on the kind of project. Each installer gives its own."""

    # The command, as messages name it, such as stm32-installer.
    name = "installer"

    # Its version, which requires.installer in a manifest is compared with.
    version = "0.0.0"

    # The file in the project that remembers what was installed, and where.
    record_name = ".installer.json"

    # What the user's project is called in the help, such as "STM32 project".
    project = "project"

    # What --ide can choose from. None of them means there is no --ide.
    integrations = ()

    # The key under requires that gives the oldest of this installer a library
    # works with, such as installer for stm32-installer.
    requires_key = "installer"

    # Said when no project file was recognised, and what to do instead.
    no_project = "No project file was recognised here, so nothing was registered."
    no_project_hint = "Add the folder to your include paths and the .c files to your build."

    @property
    def update_command(self):
        """The line that updates this installer."""
        return f"pip install --upgrade {self.name}"

    def add_arguments(self, parser):
        """Command line options of this installer's own, added to the core's."""

    def take_arguments(self, args, ask):
        """
        What this installer's own options were given as, before anything runs.

        ask(prompt) puts a question to the user and returns what was typed, or
        None when nobody is there to answer, so a question is asked only when
        it can be.
        """

    def project_root(self, given):
        """
        The folder this run works in, once take_arguments() has run.

        given is --project, or the folder the command was run from. A target
        whose libraries live somewhere of their own, such as Arduino's
        libraries folder, answers with that. Raise installer.InstallError to
        stop the run with a reason.
        """
        return given

    def dependency_root(self, project_root):
        """
        The folder a library another one needs is installed into, and looked
        for in. The project's own, unless the target keeps them elsewhere.
        """
        return project_root

    def default_folder(self, library):
        """The folder offered for a library installed for the first time."""
        return library.name

    def folder_for(self, library, project_root):
        """
        The folder offered for a library installed for the first time into
        project_root, which is the project, or where dependency_root() keeps
        what other libraries need.
        """
        return self.default_folder(library)

    def include_line(self, library, destination, project_root):
        """
        What goes between the quotes of the #include the last line names, or
        None for the first header, relative to its include folder.
        """
        return None

    def read_manifest(self, manifest, data):
        """Read this target's own part of installer.yml onto manifest, once the rest is read."""

    def read_requirements(self, requirements, data):
        """Read what this kind of project checks from requires, onto requirements."""

    def requirements_empty(self, requirements):
        """Whether the part of requires this target reads asks for nothing."""
        return True

    def warnings(self, manifest):
        """Values in a manifest this target does not know, as sentences."""
        return []

    def check(self, library, project_root):
        """Findings about the project, before the library goes in."""
        return []

    def integrate(self, project_root, library, destination, only=None, dropped=(),
                  dropped_defines=()):
        """Register an installed library with the project. Returns a list of Outcome."""
        return []

    def uninstall(self, project_root, library):
        """
        Take a library out of the project's build, before its files go.

        library is an installer.Installed: its name, its folder, its compiled
        files and its defines, as the record remembers them. Returns a list of
        Outcome.
        """
        return []


current = Target()


def use(chosen):
    """Make chosen the target the core asks from now on."""
    global current
    current = chosen
