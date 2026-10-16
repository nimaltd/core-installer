"""Tests for what a target can change: its requires key, its folder, its part of installer.yml."""

import pytest

from core_installer import cli, download, installer, manifest, target


class _Other(target.Target):
    """A second installer, with a requires key and a folder of its own."""

    name = "other-installer"
    version = "1.0.0"
    record_name = ".other-installer.json"
    requires_key = "other_installer"

    def __init__(self):
        self.read = []

    def default_folder(self, library):
        return f"modules/{library.name}"

    def read_manifest(self, manifest_, data):
        self.read.append((manifest_.name, data.get("other")))
        manifest_.other = data.get("other")


@pytest.fixture
def other(monkeypatch):
    """Make _Other the target for one test, and put the old one back after."""
    chosen = _Other()
    monkeypatch.setattr(target, "current", chosen)

    return chosen


def test_each_installer_reads_only_its_own_requires_key(library, other):
    # Written for a much newer stm32-installer, which this installer ignores.
    root = library(requires={"installer": "99.0.0"})
    assert manifest.load(root).name == "demo"

    root = library(name="newer", requires={"other_installer": "99.0.0"})

    with pytest.raises(manifest.ManifestError) as raised:
        manifest.load(root)

    assert "needs other-installer 99.0.0" in str(raised.value)
    assert "pip install --upgrade other-installer" in str(raised.value)


def test_the_requires_key_must_be_three_numbers(library, other):
    root = library(requires={"other_installer": 1.1})

    with pytest.raises(manifest.ManifestError) as raised:
        manifest.load(root)

    assert "requires.other_installer" in str(raised.value)


def test_the_target_reads_its_own_section_once_the_rest_is_read(library, other):
    root = library()
    text = (root / "installer.yml").read_text(encoding="utf-8")
    (root / "installer.yml").write_text(text + "other:\n  setting: 3\n", encoding="utf-8")

    loaded = manifest.load(root)

    assert other.read == [("demo", {"setting": 3})]
    assert loaded.other == {"setting": 3}


def test_a_new_library_is_offered_the_targets_folder(library, project, other):
    lib = manifest.load(library())

    assert cli._default_folder(lib, project()) == "modules/demo"


def test_the_default_target_keeps_the_old_answers(library, project):
    lib = manifest.load(library())

    assert target.Target().requires_key == "installer"
    assert cli._default_folder(lib, project()) == "demo"


class _Asking(target.Target):
    """An installer with a --flavour of its own, which asks when it is not given."""

    name = "asking-installer"
    version = "1.0.0"
    record_name = ".asking-installer.json"

    def __init__(self):
        self.flavour = None

    def add_arguments(self, parser):
        parser.add_argument("--flavour", default=None)

    def take_arguments(self, args, ask):
        self.flavour = args.flavour or ask("Flavour? ") or "plain"


def test_an_installer_adds_options_of_its_own(monkeypatch, capsys):
    chosen = _Asking()
    monkeypatch.setattr(target, "current", chosen)

    with pytest.raises(SystemExit):
        cli.main(["--help"])

    assert "--flavour" in capsys.readouterr().out

    assert cli.main(["--flavour", "mint"]) == 2
    assert chosen.flavour == "mint"


def test_an_installer_can_ask_when_its_option_is_not_given(monkeypatch):
    chosen = _Asking()
    monkeypatch.setattr(target, "current", chosen)
    monkeypatch.setattr(cli, "_answer", lambda prompt: "lemon" if prompt == "Flavour? " else None)

    cli.main([])

    assert chosen.flavour == "lemon"


def test_the_default_target_adds_no_options(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])

    assert "--flavour" not in capsys.readouterr().out


class _Split(target.Target):
    """
    An installer that keeps what other libraries need in a folder of its own,
    as arduino-installer does with Arduino's libraries folder.
    """

    name = "split-installer"
    version = "1.0.0"
    record_name = ".split-installer.json"

    def __init__(self, shared, moved_to=None):
        self.shared = shared
        self.moved_to = moved_to

    def project_root(self, given):
        if self.moved_to == "refuse":
            raise installer.InstallError("not a project of mine")

        return self.moved_to or given

    def dependency_root(self, project_root):
        return self.shared

    def folder_for(self, library, project_root):
        return library.name if project_root == self.shared else f"src/{library.name}"

    def include_line(self, library, destination, project_root):
        return f"{destination.relative_to(project_root).as_posix()}/{library.name}.h"


def _needing(library, tmp_path):
    """demo, which needs helper, both as folders on disk."""
    helper = library(name="helper", headers=("helper.h",), sources=(), root=tmp_path / "libs" / "helper")
    demo = library(name="demo", headers=("demo.h",), sources=(), requires={"libraries": ["helper"]},
                   root=tmp_path / "libs" / "demo")

    return demo, helper


def test_what_a_library_needs_goes_where_the_target_keeps_it(library, tmp_path, monkeypatch, capsys):
    shared = tmp_path / "shared"
    sketch = tmp_path / "sketch"
    shared.mkdir()
    sketch.mkdir()
    monkeypatch.setattr(target, "current", _Split(shared))
    monkeypatch.setattr(cli, "_answer", lambda prompt: None)
    demo, helper = _needing(library, tmp_path)

    assert cli.main([str(demo), str(helper), "--project", str(sketch)]) == 0

    assert (sketch / "src" / "demo" / "demo.h").is_file()
    assert (shared / "helper" / "helper.h").is_file()
    assert not (sketch / "src" / "helper").exists()
    assert "helper" in installer.installed_libraries(shared)
    assert list(installer.installed_libraries(sketch)) == ["demo"]
    assert 'Done. #include "src/demo/demo.h"' in capsys.readouterr().out


def test_what_is_kept_elsewhere_already_is_not_installed_again(library, tmp_path, monkeypatch, capsys):
    shared = tmp_path / "shared"
    sketch = tmp_path / "sketch"
    shared.mkdir()
    sketch.mkdir()
    monkeypatch.setattr(target, "current", _Split(shared))
    monkeypatch.setattr(cli, "_answer", lambda prompt: None)
    demo, helper = _needing(library, tmp_path)
    assert cli.main([str(helper), "--project", str(shared)]) == 0

    assert cli.main([str(demo), "--project", str(sketch)]) == 0

    assert "helper 1.0.0 is already in this project, kept" in capsys.readouterr().out
    assert not (sketch / "src" / "helper").exists()


def test_the_target_can_move_the_run_or_stop_it(library, tmp_path, monkeypatch, capsys):
    moved = tmp_path / "moved"
    moved.mkdir()
    # Run from a folder of the test's own, so a run that does not move writes nothing elsewhere.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(target, "current", _Split(tmp_path / "shared", moved_to=moved))
    monkeypatch.setattr(cli, "_answer", lambda prompt: None)
    lib = library(name="solo", headers=("solo.h",), sources=(), root=tmp_path / "libs" / "solo")

    assert cli.main([str(lib)]) == 0
    assert (moved / "src" / "solo" / "solo.h").is_file()
    assert cli.main(["--uninstall", "solo"]) == 0
    assert not (moved / "src" / "solo" / "solo.h").exists()

    target.current.moved_to = "refuse"
    assert cli.main([str(lib)]) == 2
    assert cli.main(["--uninstall", "solo"]) == 2
    assert capsys.readouterr().err.count("not a project of mine") == 2


def test_the_default_target_keeps_its_answers_for_the_new_hooks(library, tmp_path):
    lib = manifest.load(library())
    plain = target.Target()

    assert plain.project_root(tmp_path) == tmp_path
    assert plain.dependency_root(tmp_path) == tmp_path
    assert plain.folder_for(lib, tmp_path) == "demo"
    assert plain.include_line(lib, tmp_path / "demo", tmp_path) is None


def test_a_fetched_dependency_keeps_the_options_recorded_where_it_is_kept(library, tmp_path, monkeypatch,
                                                                          capsys):
    shared = tmp_path / "shared"
    sketch = tmp_path / "sketch"
    shared.mkdir()
    sketch.mkdir()
    monkeypatch.setattr(target, "current", _Split(shared))
    monkeypatch.setattr(cli, "_answer", lambda prompt: None)
    extra = {"description": "More", "files": {"headers": ["helper_extra.h"]}}
    old = library(name="helper", version="1.0.0", headers=("helper.h",), sources=(), options={"extra": extra},
                  extra_files={"helper_extra.h": "int x;\n"}, root=tmp_path / "v1" / "helper")
    new = library(name="helper", version="2.0.0", headers=("helper.h",), sources=(), options={"extra": extra},
                  extra_files={"helper_extra.h": "int x;\n"}, root=tmp_path / "v2" / "helper")
    demo = library(name="demo", headers=("demo.h",), sources=(), requires={"libraries": ["helper >= 2.0.0"]},
                   root=tmp_path / "libs" / "demo")
    monkeypatch.setattr(download, "fetch", lambda source, ref=None, destination=None: new)
    assert cli.main([str(old), "--project", str(shared), "--with", "extra"]) == 0

    assert cli.main([str(demo), "--project", str(sketch)]) == 0

    assert "extra      yes, as before" in capsys.readouterr().out
    assert (shared / "helper" / "helper_extra.h").is_file()
