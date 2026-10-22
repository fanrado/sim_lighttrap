"""
Doc-consistency tests for the backplane-reflector README additions.

Feature (commit 631d1e4):
  README.md gains a "Comparing backplane reflectors" section pointing at
  scripts/compare_backplane.sh, a "Running the unit tests" section, and notes
  backplaneFoil / ptfe.reflectivity in the YAML parameter table.

A docs commit isn't unit-testable in the usual sense, but its concrete claims
are: referenced files must exist, the documented foil selector values must match
the YAML/config, and the documented pytest invocations must point at files that
exist. These checks catch doc drift (broken script paths, renamed test files,
selector values that diverge from the code).
"""

import os
import re

import pytest
import yaml

README = "README.md"
CONFIG_YAML = "sim_config.yaml"
COMPARE_SCRIPT = "scripts/compare_backplane.sh"
FEATURE_TEST = "tests/test_backplane_foil_config.py"

ALLOWED = {"vikuiti", "ptfe", "none"}


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def readme():
    return read(README)


@pytest.fixture(scope="module")
def yaml_doc():
    with open(CONFIG_YAML) as fh:
        return yaml.safe_load(fh)


# ── referenced files exist ───────────────────────────────────────────────────

def test_readme_references_compare_script(readme):
    assert COMPARE_SCRIPT in readme, (
        f"README should reference {COMPARE_SCRIPT}"
    )


def test_compare_script_exists_and_executable():
    assert os.path.isfile(COMPARE_SCRIPT), (
        f"README references {COMPARE_SCRIPT} but it does not exist"
    )
    assert os.access(COMPARE_SCRIPT, os.X_OK), (
        f"{COMPARE_SCRIPT} should be executable (documented as a runnable helper)"
    )


def test_readme_references_feature_test_file(readme):
    assert FEATURE_TEST in readme, (
        f'README "Running the unit tests" should reference {FEATURE_TEST}'
    )


def test_feature_test_file_exists():
    assert os.path.isfile(FEATURE_TEST), (
        f"README references {FEATURE_TEST} but it does not exist"
    )


# ── documented pytest runner matches the stored pattern ──────────────────────

def test_readme_pytest_invocation_uses_python313(readme):
    """Docs must point at a runner that actually has pytest (python3.13)."""
    assert re.search(r"python3\.13\s+-m\s+pytest\s+tests/", readme), (
        "README should document 'python3.13 -m pytest tests/ ...'"
    )


# ── documented selector values match YAML + are the accepted set ─────────────

def test_readme_documents_all_foil_values(readme):
    for val in ALLOWED:
        assert re.search(rf"`{val}`", readme), (
            f"README backplane section should document the `{val}` foil value"
        )


def test_readme_foil_default_matches_yaml(readme, yaml_doc):
    """README calls vikuiti the default; that must match geometry.backplaneFoil."""
    assert "vikuiti" in readme
    # README annotates the default foil in its comparison table.
    assert re.search(r"vikuiti.*default|default.*vikuiti", readme, re.IGNORECASE), (
        "README should mark vikuiti as the default foil"
    )
    assert yaml_doc["geometry"]["backplaneFoil"] == "vikuiti", (
        "YAML default backplaneFoil should agree with the README (vikuiti)"
    )


def test_readme_ptfe_reflectivity_note_matches_yaml(readme, yaml_doc):
    """README's materials row cites ptfe.reflectivity; it must exist in the YAML."""
    assert "ptfe.reflectivity" in readme, (
        "README materials row should mention ptfe.reflectivity"
    )
    assert "ptfe" in yaml_doc["materials"], "materials.ptfe missing from YAML"
    assert "reflectivity" in yaml_doc["materials"]["ptfe"], (
        "materials.ptfe.reflectivity missing from YAML"
    )
