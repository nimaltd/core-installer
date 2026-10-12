"""Tests for what a target can change: its requires key, its folder, its part of installer.yml."""

import pytest

from core_installer import cli, manifest, target


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
