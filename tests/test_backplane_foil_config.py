"""
Tests for the configurable backplane (+z) reflector foil.

Feature (commit 70df08b):
  The +z backplane reflector foil is made selectable at run time via
  geometry.backplaneFoil in sim_config.yaml:
    "vikuiti" — 3M ESR, specular ~98 % reflector (default)
    "ptfe"    — sintered PTFE, diffuse (Lambertian) ~95 % reflector
    "none"    — no foil built/skinned; full back-face escape to leak detector
  Plumbing:
    - config.hh: new PTFEConfig{reflectivity}, MaterialsConfig.ptfe,
      SimConfig.backplaneFoil (std::string, default "vikuiti").
    - config.cc: parse materials.ptfe.reflectivity and geometry.backplaneFoil.
    - construction.{hh,cc}: fBackplaneFoil member, PTFE optical surface +
      DefinePTFEOpticalSurface() (dielectric_metal / unified / groundfrontpainted),
      called from DefineMaterials(); backplane skin selects Vikuiti/PTFE/none;
      unknown value warns and falls back to vikuiti; vis-attributes guarded for
      the no-foil case; new /detector/backplaneFoil messenger property.
    - sim_lighttrap.cc: forward cfg.backplaneFoil via /detector/backplaneFoil.

YAML checks parse the file directly; C++ checks are static source-parsing
(Geant4 can't be compiled here), mirroring tests/test_ptp_sigmaalpha_config.py.
"""

import re

import pytest
import yaml

CONFIG_YAML = "sim_config.yaml"
CONFIG_HH = "include/config.hh"
CONFIG_CC = "src/config.cc"
MAIN_CC = "src/sim_lighttrap.cc"
CONSTRUCTION_HH = "include/construction.hh"
CONSTRUCTION_CC = "src/construction.cc"

KEY = "backplaneFoil"                 # YAML geometry key / SimConfig field
CMD = "/detector/backplaneFoil"       # messenger command
ALLOWED = {"vikuiti", "ptfe", "none"}
DEFAULT = "vikuiti"


# ── helpers ───────────────────────────────────────────────────────────────────

def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def doc():
    with open(CONFIG_YAML) as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def geometry(doc):
    assert "geometry" in doc, "sim_config.yaml must have a 'geometry:' section"
    return doc["geometry"]


@pytest.fixture(scope="module")
def materials(doc):
    assert "materials" in doc, "sim_config.yaml must have a 'materials:' section"
    return doc["materials"]


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
def cons_hh():
    return read(CONSTRUCTION_HH)


@pytest.fixture(scope="module")
def cons_cc():
    return read(CONSTRUCTION_CC)


# ── 1. sim_config.yaml: geometry.backplaneFoil ───────────────────────────────

def test_yaml_key_present(geometry):
    assert KEY in geometry, f"geometry.{KEY} missing from sim_config.yaml"


def test_yaml_default_is_vikuiti(geometry):
    """Default foil must be the specular ESR (vikuiti) — no regression."""
    val = geometry[KEY]
    assert isinstance(val, str), f"{KEY} should be a string, got {type(val)}"
    assert val == DEFAULT, f"default {KEY} should be '{DEFAULT}', got '{val}'"


def test_yaml_value_in_allowed_set(geometry):
    """Only vikuiti | ptfe | none are meaningful selector values."""
    val = geometry[KEY]
    assert val in ALLOWED, f"{KEY}='{val}' must be one of {sorted(ALLOWED)}"


# ── 2. sim_config.yaml: materials.ptfe.reflectivity ──────────────────────────

def test_yaml_ptfe_section_present(materials):
    assert "ptfe" in materials, "materials.ptfe missing from sim_config.yaml"
    assert "reflectivity" in materials["ptfe"], "materials.ptfe.reflectivity missing"


def test_yaml_ptfe_reflectivity_length_13(materials):
    """PTFE reflectivity is sampled on the shared 13-point wavelength grid."""
    refl = materials["ptfe"]["reflectivity"]
    assert isinstance(refl, list), "ptfe.reflectivity should be a list"
    assert len(refl) == 13, f"ptfe.reflectivity should have 13 points, got {len(refl)}"


def test_yaml_ptfe_reflectivity_physical(materials):
    """Reflectivities are probabilities in [0,1]; PTFE is a strong (~0.95) diffuse reflector."""
    refl = materials["ptfe"]["reflectivity"]
    for r in refl:
        assert 0.0 <= r <= 1.0, f"ptfe reflectivity {r} outside [0,1]"
    assert all(abs(r - 0.95) < 1e-9 for r in refl), (
        "documented PTFE reflectivity should be 0.95 across the band"
    )


# ── 3. include/config.hh: PTFEConfig + SimConfig field ───────────────────────

def test_ptfe_config_struct_declared(cfg_hh):
    """A PTFEConfig struct with a reflectivity vector must exist."""
    m = re.search(r"struct\s+PTFEConfig\s*\{(.*?)\}\s*;", cfg_hh, re.DOTALL)
    assert m, "config.hh should declare 'struct PTFEConfig { ... };'"
    assert re.search(r"std::vector<double>\s+reflectivity", m.group(1)), (
        "PTFEConfig should hold std::vector<double> reflectivity"
    )


def test_materials_config_has_ptfe_member(cfg_hh):
    """MaterialsConfig must aggregate a PTFEConfig member named ptfe."""
    m = re.search(r"struct\s+MaterialsConfig\s*\{(.*?)\}\s*;", cfg_hh, re.DOTALL)
    assert m, "config.hh should declare 'struct MaterialsConfig { ... };'"
    assert re.search(r"PTFEConfig\s+ptfe\s*;", m.group(1)), (
        "MaterialsConfig should have a 'PTFEConfig ptfe;' member"
    )


def test_simconfig_backplanefoil_field_default(cfg_hh):
    """SimConfig must declare std::string backplaneFoil defaulting to "vikuiti"."""
    m = re.search(rf'std::string\s+{KEY}\s*=\s*"([^"]*)"\s*;', cfg_hh)
    assert m, f'SimConfig should declare std::string {KEY} = "...";'
    assert m.group(1) == DEFAULT, (
        f"{KEY} default should be '{DEFAULT}', got '{m.group(1)}'"
    )


# ── 4. src/config.cc: parsing ────────────────────────────────────────────────

def test_config_parses_ptfe_reflectivity(cfg_cc):
    """parseMaterials must read mat['ptfe'].reflectivity into m.ptfe.reflectivity."""
    assert re.search(r'mat\s*\[\s*"ptfe"\s*\]', cfg_cc), (
        'config.cc should look up mat["ptfe"]'
    )
    assert re.search(r"m\.ptfe\.reflectivity\s*=\s*readVec\(", cfg_cc), (
        "config.cc should assign m.ptfe.reflectivity = readVec(...)"
    )


def test_config_parses_backplanefoil_as_string(cfg_cc):
    """fromFile must read geo['backplaneFoil'] as a string into cfg.backplaneFoil."""
    assert re.search(rf'geo\s*\[\s*"{KEY}"\s*\]', cfg_cc), (
        f'config.cc should look up geo["{KEY}"]'
    )
    assert re.search(
        rf'cfg\.{KEY}\s*=\s*geo\s*\[\s*"{KEY}"\s*\]\.as<std::string>\(\)', cfg_cc
    ), f'config.cc should assign cfg.{KEY} = geo["{KEY}"].as<std::string>()'


# ── 5. include/construction.hh: declarations ─────────────────────────────────

def test_construction_declares_backplane_member(cons_hh):
    assert re.search(r"G4String\s+fBackplaneFoil\s*;", cons_hh), (
        "construction.hh should declare 'G4String fBackplaneFoil;'"
    )


def test_construction_declares_ptfe_surface_and_method(cons_hh):
    assert re.search(r"G4OpticalSurface\s*\*\s*PTFE\s*;", cons_hh), (
        "construction.hh should declare 'G4OpticalSurface *PTFE;'"
    )
    assert re.search(r"void\s+DefinePTFEOpticalSurface\s*\(", cons_hh), (
        "construction.hh should declare DefinePTFEOpticalSurface()"
    )


# ── 6. src/construction.cc: implementation ───────────────────────────────────

def test_messenger_property_declared(cons_cc):
    """The /detector/backplaneFoil command must exist on the geometry messenger."""
    assert re.search(r'DeclareProperty\s*\(\s*"backplaneFoil"', cons_cc), (
        'geometry messenger should DeclareProperty("backplaneFoil", ...)'
    )


def test_geometry_default_matches_yaml_default(cons_cc):
    """The C++ geometry default must also be "vikuiti" (matches YAML default)."""
    m = re.search(r'fBackplaneFoil\s*=\s*"([^"]*)"\s*;', cons_cc)
    assert m, "construction.cc should initialize fBackplaneFoil to a default"
    assert m.group(1) == DEFAULT, (
        f"construction.cc default fBackplaneFoil should be '{DEFAULT}', got '{m.group(1)}'"
    )


def test_ptfe_surface_definition_is_lambertian_diffuse(cons_cc):
    """DefinePTFEOpticalSurface must model a diffuse dielectric_metal reflector."""
    m = re.search(
        r"void\s+MyLightTrapConstruction::DefinePTFEOpticalSurface\s*\(\s*\)\s*\{(.*?)\n\}",
        cons_cc, re.DOTALL,
    )
    assert m, "construction.cc should define DefinePTFEOpticalSurface()"
    body = m.group(1)
    assert "PTFE = new G4OpticalSurface" in body, "should construct the PTFE surface"
    assert "dielectric_metal" in body, "PTFE surface type should be dielectric_metal"
    assert "groundfrontpainted" in body, (
        "PTFE finish should be groundfrontpainted (Lambertian diffuse)"
    )
    assert "unified" in body, "PTFE surface should use the UNIFIED model"
    assert "REFLECTIVITY" in body, "PTFE surface must set a REFLECTIVITY property"


def test_ptfe_surface_registered_in_definematerials(cons_cc):
    """DefineMaterials() must call DefinePTFEOpticalSurface() so PTFE is built."""
    m = re.search(
        r"void\s+MyLightTrapConstruction::DefineMaterials\s*\(\s*\)\s*\{(.*?)\n\}",
        cons_cc, re.DOTALL,
    )
    assert m, "construction.cc should define DefineMaterials()"
    assert "DefinePTFEOpticalSurface();" in m.group(1), (
        "DefineMaterials() should call DefinePTFEOpticalSurface()"
    )


def test_backplane_selects_surface_by_foil_value(cons_cc):
    """Backplane surface selection must map vikuiti→Vikuiti, ptfe→PTFE, none→nullptr."""
    assert re.search(
        r'fBackplaneFoil\s*==\s*"vikuiti"\s*\)\s*backplaneSurf\s*=\s*Vikuiti', cons_cc
    ), "vikuiti must select the Vikuiti surface"
    assert re.search(
        r'fBackplaneFoil\s*==\s*"ptfe"\s*\)\s*backplaneSurf\s*=\s*PTFE', cons_cc
    ), "ptfe must select the PTFE surface"
    assert re.search(
        r'fBackplaneFoil\s*==\s*"none"\s*\)\s*backplaneSurf\s*=\s*nullptr', cons_cc
    ), "none must select no surface (nullptr)"


def test_unknown_foil_falls_back_to_vikuiti(cons_cc):
    """An unknown value must warn and fall back to vikuiti (no silent bad geometry)."""
    # The else branch resets fBackplaneFoil to "vikuiti" and uses the Vikuiti surface.
    assert re.search(r'fBackplaneFoil\s*=\s*"vikuiti"\s*;', cons_cc), (
        "unknown-foil fallback should reset fBackplaneFoil to \"vikuiti\""
    )
    assert re.search(r"falling back to 'vikuiti'", cons_cc), (
        "unknown foil should emit a warning about falling back to vikuiti"
    )


def test_none_skips_foil_build(cons_cc):
    """"none" must skip building/skinning the backplane foil entirely."""
    assert re.search(
        r'if\s*\(\s*fBackplaneFoil\s*!=\s*"none"\s*\)\s*\{', cons_cc
    ), 'the foil build+skin must be guarded by if (fBackplaneFoil != "none")'


def test_backplane_skin_uses_selected_surface(cons_cc):
    """The backplane skin surface must be the run-time-selected surface, not hard-coded Vikuiti."""
    m = re.search(
        r'new\s+G4LogicalSkinSurface\s*\(\s*"skinBackplane"\s*,\s*'
        r"logicReflectiveFoilBackPlane\s*,\s*(\w+)\s*\)",
        cons_cc,
    )
    assert m, 'construction.cc should create the "skinBackplane" skin surface'
    assert m.group(1) == "backplaneSurf", (
        f"skinBackplane should use backplaneSurf, got {m.group(1)}"
    )


def test_visattributes_guarded_for_no_foil(cons_cc):
    """Vis-attributes must be guarded so the no-foil (nullptr logical) case is safe."""
    assert re.search(
        r"if\s*\(\s*logicReflectiveFoilBackPlane\s*\)\s*\n?\s*"
        r"logicReflectiveFoilBackPlane->SetVisAttributes",
        cons_cc,
    ), "SetVisAttributes on the backplane foil must be null-guarded"


# ── 7. src/sim_lighttrap.cc: forwarding via messenger ────────────────────────

def test_messenger_command_applied(main_cc):
    """cfg.backplaneFoil must be forwarded via ApplyCommand("/detector/backplaneFoil " + ...)."""
    m = re.search(
        rf'ApplyCommand\s*\(\s*"{re.escape(CMD)}\s*"\s*\+\s*([^)]*)\)', main_cc
    )
    assert m, f'expected ApplyCommand("{CMD} " + cfg.{KEY})'
    assert KEY in m.group(1), (
        f"the command must forward cfg.{KEY}, got + {m.group(1)}"
    )


def test_foil_forwarded_as_string_no_d2s(main_cc):
    """backplaneFoil is a string selector — it must NOT be wrapped in d2s()/numeric conversion."""
    m = re.search(
        rf'ApplyCommand\s*\(\s*"{re.escape(CMD)}\s*"\s*\+\s*([^)]*)\)', main_cc
    )
    assert m, "backplaneFoil ApplyCommand not found"
    arg = m.group(1)
    assert "d2s" not in arg, f"string selector must not use d2s(), got + {arg}"
    assert "*" not in arg, f"string selector must not be scaled, got + {arg}"
