"""
Tests for exposing pTPsigmaAlpha through YAML config + messenger.

Feature (commit f28b9a4, beads sim_lighttrap-0jc):
  geometry.pTPsigmaAlpha_rad (default 0.0 = smooth) is added to sim_config.yaml
  and SimConfig, parsed in config.cc, and forwarded to the geometry at startup
  via the /detector/pTPsigmaAlpha messenger command so the pTP border-surface
  roughness is configurable without recompiling. Mirrors the existing
  pTPlayerThickness_mm plumbing.

The YAML checks parse the file directly; the C++ checks are static
source-parsing (Geant4 can't be compiled here), mirroring the existing
tests/test_cmakelists_geant4.py style.
"""

import re

import pytest
import yaml

CONFIG_YAML = "sim_config.yaml"
CONFIG_HH = "include/config.hh"
CONFIG_CC = "src/config.cc"
MAIN_CC = "src/sim_lighttrap.cc"
CONSTRUCTION_CC = "src/construction.cc"

KEY = "pTPsigmaAlpha_rad"           # YAML / SimConfig field
CMD = "/detector/pTPsigmaAlpha"     # messenger command


# ── helpers ───────────────────────────────────────────────────────────────────

def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def geometry():
    with open(CONFIG_YAML) as fh:
        doc = yaml.safe_load(fh)
    assert "geometry" in doc, "sim_config.yaml must have a 'geometry:' section"
    return doc["geometry"]


@pytest.fixture(scope="module")
def cfg_hh():
    return read(CONFIG_HH)


@pytest.fixture(scope="module")
def cfg_cc():
    return read(CONFIG_CC)


@pytest.fixture(scope="module")
def main_cc():
    return read(MAIN_CC)


@pytest.fixture(scope="module")
def cons_cc():
    return read(CONSTRUCTION_CC)


# ── 1. sim_config.yaml ───────────────────────────────────────────────────────

def test_yaml_key_present(geometry):
    assert KEY in geometry, f"geometry.{KEY} missing from sim_config.yaml"


def test_yaml_default_is_zero_smooth(geometry):
    """Default must be 0.0 (perfectly smooth / specular)."""
    val = geometry[KEY]
    assert isinstance(val, (int, float)), f"{KEY} should be numeric, got {type(val)}"
    assert val == 0.0, f"default {KEY} should be 0.0 (smooth), got {val}"


def test_yaml_value_non_negative(geometry):
    """A facet-slope RMS is a non-negative angle in radians."""
    assert geometry[KEY] >= 0.0, f"{KEY} must be non-negative"


# ── 2. include/config.hh: SimConfig field ────────────────────────────────────

def test_struct_field_declared_with_default(cfg_hh):
    """SimConfig must declare double pTPsigmaAlpha_rad defaulting to 0.0."""
    m = re.search(rf"double\s+{KEY}\s*=\s*([0-9.]+)\s*;", cfg_hh)
    assert m, f"SimConfig should declare 'double {KEY} = ...;'"
    assert float(m.group(1)) == 0.0, f"{KEY} default should be 0.0, got {m.group(1)}"


# ── 3. src/config.cc: parsing ────────────────────────────────────────────────

def test_config_parses_key_into_field(cfg_cc):
    """fromFile must read geo['pTPsigmaAlpha_rad'] into cfg.pTPsigmaAlpha_rad."""
    # guarded read: if (geo["pTPsigmaAlpha_rad"]) cfg.pTPsigmaAlpha_rad = ...as<double>()
    assert re.search(
        rf'geo\s*\[\s*"{KEY}"\s*\]', cfg_cc
    ), f"config.cc should look up geo[\"{KEY}\"]"
    assert re.search(
        rf'cfg\.{KEY}\s*=\s*geo\s*\[\s*"{KEY}"\s*\]\.as<double>\(\)', cfg_cc
    ), f"config.cc should assign cfg.{KEY} = geo[\"{KEY}\"].as<double>()"


# ── 4. src/sim_lighttrap.cc: forwarding via messenger ────────────────────────

def test_messenger_command_applied(main_cc):
    """The parsed value must be forwarded via ApplyCommand(\"/detector/pTPsigmaAlpha ...\")."""
    m = re.search(
        rf'ApplyCommand\s*\(\s*"{re.escape(CMD)}\s*"\s*\+\s*d2s\(([^)]*)\)', main_cc
    )
    assert m, f'expected ApplyCommand("{CMD} " + d2s(cfg.{KEY}))'
    assert KEY in m.group(1), f"the command must forward cfg.{KEY}, got d2s({m.group(1)})"


def test_sigmaalpha_forwarded_without_unit_scaling(main_cc):
    """pTPsigmaAlpha is in radians in both YAML and messenger — no *10 cm→mm scaling."""
    m = re.search(
        rf'ApplyCommand\s*\(\s*"{re.escape(CMD)}\s*"\s*\+\s*d2s\(([^)]*)\)', main_cc
    )
    assert m, "pTPsigmaAlpha ApplyCommand not found"
    arg = m.group(1)
    assert "*" not in arg, f"pTPsigmaAlpha must be forwarded unscaled, got d2s({arg})"


# ── 5. src/construction.cc: the messenger command target exists ──────────────

def test_messenger_property_declared(cons_cc):
    """The /detector/pTPsigmaAlpha command must actually exist on the geometry messenger."""
    assert re.search(
        r'DeclareProperty\s*\(\s*"pTPsigmaAlpha"', cons_cc
    ), 'geometry messenger should DeclareProperty("pTPsigmaAlpha", ...)'


def test_geometry_default_matches_yaml_default(cons_cc):
    """The C++ geometry default for pTPsigmaAlpha must also be 0.0 (smooth)."""
    m = re.search(r"pTPsigmaAlpha\s*=\s*([0-9.]+)\s*;", cons_cc)
    assert m, "construction.cc should initialize pTPsigmaAlpha to a default"
    assert float(m.group(1)) == 0.0, (
        f"construction.cc default pTPsigmaAlpha should be 0.0, got {m.group(1)}"
    )
