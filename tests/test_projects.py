from pathlib import Path

from kuku_localise.projects import create_project, list_projects, read_project, slugify, update_project


def test_project_metadata_and_listing(tmp_path: Path):
    project = create_project(tmp_path, "The Broken Duke")
    assert project.name == "the-broken-duke"
    assert read_project(project)["language"] == "Hindi"
    update_project(project, language="Tamil", model="gemini-test")
    assert read_project(project)["model"] == "gemini-test"
    assert list_projects(tmp_path) == [project]


def test_slugify_requires_a_name():
    assert slugify("A Show! 2026") == "a-show-2026"
    try:
        slugify("---")
    except ValueError:
        pass
    else:
        raise AssertionError("expected a missing-name error")
