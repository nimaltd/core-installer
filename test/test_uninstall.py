"""Taking a library out of a project: its files, its record, and what is the user's."""

import json

import pytest

from core_installer import cli, download, installer, target


@pytest.fixture
def no_network(monkeypatch):
    """Fail loudly if a test that should stay offline goes online."""

    def refuse(*args, **kwargs):
        raise AssertionError("tried to use the network")

    monkeypatch.setattr(download, "fetch", refuse)


@pytest.fixture
def nobody(monkeypatch):
    """Nobody at the keyboard: every question takes its default."""
    monkeypatch.setattr(cli, "_answer", lambda prompt: None)


@pytest.fixture
def seen(monkeypatch):
    """What the target was asked to take out of the build, and the files there then."""
    calls = []

    def uninstall(project_root, library):
        calls.append((library, sorted(p.name for p in library.destination.rglob("*") if p.is_file())))
        return []

    monkeypatch.setattr(target.current, "uninstall", uninstall)

    return calls


def _install(*args):
    assert cli.main([str(arg) for arg in args]) == 0


def _record(root):
    return json.loads((root / ".test-installer.json").read_text(encoding="utf-8"))["libraries"]


def _with_needs(library, tmp_path):
    """ee24, which needs osal, and osal itself, as folders outside the project."""
    osal = library(name="osal", headers=("osal.h",), sources=(), once=[], root=tmp_path / "src" / "osal")
    ee24 = library(name="ee24", headers=("ee24.h",), sources=("ee24.c",), once=[],
                   requires={"libraries": ["osal"]}, root=tmp_path / "src" / "ee24")

    return ee24, osal


# ----------------------------------------------------------------------------
# The files
# ----------------------------------------------------------------------------


def test_the_files_the_record_and_the_folder_go(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")
    folder = root / "Libs" / "demo"
    assert (folder / "demo.c").is_file()

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    assert not folder.exists()
    assert (root / "Libs").is_dir()
    assert "demo" not in _record(root)

    out = capsys.readouterr().out
    assert "removed Libs/demo/demo.c" in out
    assert "Done. demo is out of the project." in out


def test_a_file_that_was_the_users_is_saved_first(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(), "--project", root, "--dir", "Libs/demo")
    config = root / "Libs" / "demo" / "demo_config.h"
    config.write_text("#define DEMO_SIZE 64\n", encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    saved = list((root / "Libs" / "demo").glob("demo_config.h.*.bak"))
    assert not config.exists()
    assert [p.read_text(encoding="utf-8") for p in saved] == ["#define DEMO_SIZE 64\n"]

    out = capsys.readouterr().out
    assert "it was yours to edit" in out
    assert "Libs/demo stays, for what was saved above" in out


def test_what_was_written_in_a_library_file_is_saved_first(library, project, nobody, no_network, capsys):
    header = "/* USER CODE BEGIN SETTINGS */\n/* USER CODE END SETTINGS */\nint demo(void);\n"
    lib = library(once=[], extra_files={"inc/demo.h": header})
    root = project()
    _install(lib, "--project", root, "--dir", "Libs/demo")
    path = root / "Libs" / "demo" / "demo.h"
    path.write_text(header.replace("SETTINGS */\n/*", "SETTINGS */\n#define MINE 1\n/*"), encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    saved = list((root / "Libs" / "demo").glob("demo.h.*.bak"))
    assert not path.exists()
    assert len(saved) == 1 and "#define MINE 1" in saved[0].read_text(encoding="utf-8")
    assert "it has something between its USER CODE lines" in capsys.readouterr().out


def test_a_file_changed_outside_its_sections_is_saved_first(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")
    path = root / "Libs" / "demo" / "demo.c"
    path.write_text("/* mine now */\n", encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    assert [p.read_text(encoding="utf-8") for p in (root / "Libs" / "demo").glob("demo.c.*.bak")] == ["/* mine now */\n"]
    assert "it was changed outside its USER CODE sections" in capsys.readouterr().out


def test_an_extra_that_shows_user_code_lines_is_not_taken_for_the_users(library, project, nobody, no_network):
    """A README that shows a configuration file as an example has the markers, and text between them."""
    readme = "Set it:\n/* USER CODE BEGIN X */\n#define X 1\n/* USER CODE END X */\n"
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")

    # Recorded the way the install records an extra: in files, with no fingerprint.
    path = root / ".test-installer.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["libraries"]["demo"]["files"].append("Libs/demo/README.md")
    path.write_text(json.dumps(data), encoding="utf-8")
    (root / "Libs" / "demo" / "README.md").write_text(readme, encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    assert not (root / "Libs" / "demo").exists()


def test_a_file_the_library_never_installed_stays_with_its_folder(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")
    notes = root / "Libs" / "demo" / "notes.txt"
    notes.write_text("mine\n", encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    assert notes.read_text(encoding="utf-8") == "mine\n"
    assert not (root / "Libs" / "demo" / "demo.c").exists()

    out = capsys.readouterr().out
    assert "kept    Libs/demo/notes.txt" in out
    assert "Libs/demo stays" in out


def test_a_record_naming_a_file_outside_the_folder_deletes_nothing_there(library, project, nobody, no_network):
    """The record is a file anyone can edit, so it never decides alone what is deleted."""
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")
    outside = root / "main.c"
    outside.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    path = root / ".test-installer.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["libraries"]["demo"]["files"] += ["main.c", "Libs/demo/../../main.c", str(outside)]
    path.write_text(json.dumps(data), encoding="utf-8")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    assert outside.is_file()


# ----------------------------------------------------------------------------
# What it needs, and what needs it
# ----------------------------------------------------------------------------


def test_what_a_library_needs_is_recorded(library, project, nobody, no_network, tmp_path):
    root = project()
    ee24, osal = _with_needs(library, tmp_path)
    _install(ee24, osal, "--project", root)

    assert _record(root)["ee24"]["needs"] == ["osal"]
    assert _record(root)["osal"]["needs"] == []


def test_a_library_another_needs_stays(library, project, nobody, no_network, tmp_path, capsys):
    root = project()
    ee24, osal = _with_needs(library, tmp_path)
    _install(ee24, osal, "--project", root)

    assert cli.main(["--uninstall", "osal", "--project", str(root)]) == 2

    assert "ee24 needs osal, so it stays" in capsys.readouterr().err
    assert (root / "osal" / "osal.h").is_file()
    assert "osal" in _record(root)


def test_both_on_one_line_go_in_the_right_order(library, project, nobody, no_network, tmp_path):
    root = project()
    ee24, osal = _with_needs(library, tmp_path)
    _install(ee24, osal, "--project", root)

    assert cli.main(["--uninstall", "osal", "ee24", "--project", str(root)]) == 0

    assert _record(root) == {}
    assert not (root / "osal").exists()
    assert not (root / "ee24").exists()


def test_a_library_nothing_needs_any_more_is_named(library, project, nobody, no_network, tmp_path, capsys):
    root = project()
    ee24, osal = _with_needs(library, tmp_path)
    _install(ee24, osal, "--project", root)
    capsys.readouterr()

    assert cli.main(["--uninstall", "ee24", "--project", str(root)]) == 0

    out = capsys.readouterr().out
    assert "osal came in for ee24, and nothing here needs it now" in out
    assert "test-installer --uninstall osal" in out
    assert "osal" in _record(root)


def test_a_library_not_installed_is_refused_naming_what_is(library, project, nobody, no_network, capsys):
    root = project()
    _install(library(once=[]), "--project", root, "--dir", "Libs/demo")

    assert cli.main(["--uninstall", "dmeo", "--project", str(root)]) == 2

    assert "dmeo is not installed in this project. .test-installer.json has demo." in capsys.readouterr().err


def test_uninstall_and_install_are_not_mixed(library, project, nobody, no_network, capsys):
    root = project()

    assert cli.main([str(library()), "--uninstall", "demo", "--project", str(root)]) == 2
    assert "Install on a run of its own" in capsys.readouterr().err


# ----------------------------------------------------------------------------
# What the target is told
# ----------------------------------------------------------------------------


def test_the_build_lets_go_before_the_files_go(library, project, nobody, no_network, seen):
    root = project()
    _install(library(once=[], install={"layout": "mirror", "defines": ["DEMO_FAST"]}),
             "--project", root, "--dir", "Libs/demo")

    assert cli.main(["--uninstall", "demo", "--project", str(root)]) == 0

    (lib, files), = seen
    assert lib.name == "demo"
    assert lib.destination == (root / "Libs" / "demo").resolve()
    assert lib.compiled == ["src/demo.c"]
    assert lib.defines == ["DEMO_FAST"]
    assert "demo.c" in files


def test_a_define_another_library_asks_for_stays(library, project, nobody, no_network, seen, tmp_path):
    root = project()
    first = library(name="first", headers=("first.h",), sources=(), once=[],
                    install={"defines": ["SHARED", "FIRST"]}, root=tmp_path / "src" / "first")
    second = library(name="second", headers=("second.h",), sources=(), once=[],
                     install={"defines": ["SHARED"]}, root=tmp_path / "src" / "second")
    _install(first, second, "--project", root)

    assert cli.main(["--uninstall", "first", "--project", str(root)]) == 0

    assert seen[0][0].defines == ["FIRST"]


def test_the_default_target_has_nothing_to_take_out(project):
    assert target.Target().uninstall(project(), None) == []


def test_an_installed_library_reads_only_what_it_should(project):
    root = project()
    entry = {"folder": "Libs/demo", "files": ["Libs/demo/a.c", "../x.c", 7, "Libs/demo/b.h"],
             "defines": ["OK=1", "BAD; rm", 3], "needs": ["osal", 4]}

    lib = installer.Installed(root, "demo", entry)

    assert [p.name for p in lib.files] == ["a.c", "b.h"]
    assert lib.compiled == ["a.c"]
    assert lib.defines == ["OK=1"]
    assert lib.needs == ["osal"]
