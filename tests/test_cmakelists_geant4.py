"""
Tests for portable Geant4 discovery in CMakeLists.txt.

History:
  - 8d6725e added a hardcoded machine-specific Spack path to CMAKE_PREFIX_PATH.
  - 2b3dcc7 replaced it with portable discovery via the GEANT4_CMAKE_DIR env var
    (plus the standard -DGeant4_DIR / -DCMAKE_PREFIX_PATH cmake flags).

Covers:
  - No hardcoded machine-specific install path leaks back in (regression guard)
  - Geant4 is hinted via the GEANT4_CMAKE_DIR environment variable, guarded by
    an if(DEFINED ENV{...}) so an unset var does not break configure
  - The env hint is appended to CMAKE_PREFIX_PATH before find_package(Geant4)
  - The build still requires Geant4 via find_package(... REQUIRED ...)
  - The pre-existing build wiring (project name, executable, links) is intact
"""

import re

import pytest

CMAKE_FILE = "CMakeLists.txt"

ENV_VAR = "GEANT4_CMAKE_DIR"


# ── helpers ───────────────────────────────────────────────────────────────────

def read_cmake():
    with open(CMAKE_FILE) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def cmake_text():
    return read_cmake()


# ── the portable-discovery feature ───────────────────────────────────────────

def test_no_hardcoded_spack_path(cmake_text):
    """Regression: the machine-specific Spack path from 8d6725e must be gone."""
    assert "/opt/homebrew/Cellar/spack" not in cmake_text, (
        "hardcoded machine-specific Spack path reappeared in CMakeLists.txt"
    )
    # More generally, no absolute path should be hardcoded into a prefix-path
    # append (env-var references like $ENV{...} are fine).
    for m in re.finditer(
        r"list\s*\(\s*APPEND\s+CMAKE_PREFIX_PATH(.*?)\)", cmake_text, re.DOTALL
    ):
        for entry in re.findall(r'"([^"]+)"', m.group(1)):
            assert "$ENV{" in entry or not entry.startswith("/"), (
                f"CMAKE_PREFIX_PATH still hardcodes an absolute path: {entry}"
            )


def test_env_var_used_for_discovery(cmake_text):
    """Geant4 should be locatable via the GEANT4_CMAKE_DIR environment variable."""
    assert f"ENV{{{ENV_VAR}}}" in cmake_text, (
        f"expected Geant4 discovery to reference the {ENV_VAR} environment variable"
    )


def test_env_hint_is_guarded(cmake_text):
    """The env hint must be guarded so an unset variable doesn't break configure."""
    assert re.search(
        rf"if\s*\(\s*DEFINED\s+ENV\{{{ENV_VAR}\}}\s*\)", cmake_text
    ), f"the {ENV_VAR} hint should be wrapped in if(DEFINED ENV{{{ENV_VAR}}})"


def test_env_hint_appended_to_prefix_path(cmake_text):
    """When set, GEANT4_CMAKE_DIR should be appended to CMAKE_PREFIX_PATH."""
    m = re.search(
        r"list\s*\(\s*APPEND\s+CMAKE_PREFIX_PATH(.*?)\)", cmake_text, re.DOTALL
    )
    assert m, "expected a list(APPEND CMAKE_PREFIX_PATH ...) block"
    assert f"ENV{{{ENV_VAR}}}" in m.group(1), (
        f"{ENV_VAR} should be appended to CMAKE_PREFIX_PATH"
    )


def test_find_package_geant4_still_required(cmake_text):
    """The Geant4 dependency must remain REQUIRED."""
    m = re.search(r"find_package\s*\(\s*Geant4([^)]*)\)", cmake_text)
    assert m, "find_package(Geant4 ...) is missing"
    assert "REQUIRED" in m.group(1), "Geant4 should remain REQUIRED"


def test_env_hint_precedes_find_package(cmake_text):
    """The env hint is only useful if it runs before find_package(Geant4)."""
    hint_pos = cmake_text.find(f"ENV{{{ENV_VAR}}}")
    find_pos = cmake_text.find("find_package(Geant4")
    assert hint_pos != -1 and find_pos != -1
    assert hint_pos < find_pos, (
        f"{ENV_VAR} hint must be applied before find_package(Geant4)"
    )


# ── regression: existing build wiring untouched ──────────────────────────────

def test_project_declaration_intact(cmake_text):
    assert re.search(
        r"project\s*\(\s*LightTrapSimulation", cmake_text
    ), "project(LightTrapSimulation) declaration is missing"


def test_geant4_use_file_included(cmake_text):
    assert "Geant4_USE_FILE" in cmake_text, "include(${Geant4_USE_FILE}) is missing"


def test_executable_and_geant4_linkage_intact(cmake_text):
    assert re.search(
        r"add_executable\s*\(\s*sim_lighttrap", cmake_text
    ), "sim_lighttrap executable target is missing"
    assert re.search(
        r"target_link_libraries\s*\(\s*sim_lighttrap[^)]*Geant4_LIBRARIES",
        cmake_text,
        re.DOTALL,
    ), "sim_lighttrap should link against Geant4_LIBRARIES"


# ── CMake 4 compatibility of the fetched yaml-cpp ────────────────────────────

def test_cmake4_policy_floor_for_fetched_yaml_cpp(cmake_text):
    """yaml-cpp 0.8.0 declares cmake_minimum_required(VERSION 3.4); CMake >= 4
    refuses it unless CMAKE_POLICY_VERSION_MINIMUM >= 3.5 is set before the
    FetchContent configure step."""
    assert re.search(r"cmake_minimum_required\s*\(\s*VERSION\s+3\.16\.\.\.3\.\d+", cmake_text), \
        "project minimum should be 3.16 (Geant4 11) with a policy upper bound"
    m = re.search(r"set\s*\(\s*CMAKE_POLICY_VERSION_MINIMUM\s+3\.5\s+CACHE", cmake_text)
    assert m, "CMAKE_POLICY_VERSION_MINIMUM 3.5 must be set for the fetched yaml-cpp"
    assert m.start() < cmake_text.index("FetchContent_MakeAvailable"), "must be set before FetchContent_MakeAvailable"
