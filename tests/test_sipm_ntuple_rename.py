"""
Tests for the SiPM output-ntuple rename and its analysis reader.

Feature (commits 2c27101 + 613f436 + 4088143 + f33925d):
  The SiPM trees get explicit names — ntuple 0 "Photons" -> "SiPMPhotons"
  (photons reaching a SiPM face, pre-PDE) and ntuple 1 "Hits" -> "SiPMHits"
  (photons collected/detected, post-PDE).  Numeric FillNtuple ids are unchanged
  (title-only change in run.cc).  analysis/analyze_efficiency.py is updated to
  read the trees by their new names, and docs/analysis.org + docs/physics.org
  refer to the trees by the new names.

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_cmakelists_geant4.py.
"""

import re

import pytest

RUN_CC = "src/run.cc"
ANALYZE = "analysis/analyze_efficiency.py"
ANALYSIS_ORG = "docs/analysis.org"
PHYSICS_ORG = "docs/physics.org"


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def run_cc():
    return read(RUN_CC)


@pytest.fixture(scope="module")
def analyze():
    return read(ANALYZE)


@pytest.fixture(scope="module")
def analysis_org():
    return read(ANALYSIS_ORG)


@pytest.fixture(scope="module")
def physics_org():
    return read(PHYSICS_ORG)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def ntuple_block(code, name, finish_id):
    m = re.search(
        rf'CreateNtuple\s*\(\s*"{re.escape(name)}".*?FinishNtuple\s*\(\s*{finish_id}\s*\)',
        code,
        re.DOTALL,
    )
    return m.group(0) if m else None


# ── run.cc: names changed, ids unchanged (2c27101) ───────────────────────────

def test_sipmphotons_is_ntuple_0(run_cc):
    """SiPMPhotons must keep numeric id 0 (SD FillNtuple(0) unchanged)."""
    block = ntuple_block(strip_comments(run_cc), "SiPMPhotons", 0)
    assert block, "SiPMPhotons ntuple should be created and end at FinishNtuple(0)"


def test_sipmhits_is_ntuple_1(run_cc):
    """SiPMHits must keep numeric id 1 (SD FillNtuple(1) unchanged)."""
    block = ntuple_block(strip_comments(run_cc), "SiPMHits", 1)
    assert block, "SiPMHits ntuple should be created and end at FinishNtuple(1)"


def test_old_sipm_ntuple_names_removed(run_cc):
    """The bare CreateNtuple("Photons"/"Hits") names must be gone (only titles may mention them)."""
    code = strip_comments(run_cc)
    assert not re.search(r'CreateNtuple\s*\(\s*"Photons"\s*,', code), (
        'stale CreateNtuple("Photons", ...) still present; should be "SiPMPhotons"'
    )
    assert not re.search(r'CreateNtuple\s*\(\s*"Hits"\s*,', code), (
        'stale CreateNtuple("Hits", ...) still present; should be "SiPMHits"'
    )


def test_sipmphotons_column_layout_unchanged(run_cc):
    """Rename is title-only: SiPMPhotons keeps eventID + fX,fY,fZ,fT,fwl (1 I + 5 D)."""
    block = ntuple_block(strip_comments(run_cc), "SiPMPhotons", 0)
    assert block
    assert len(re.findall(r"CreateNtupleIColumn", block)) == 1
    assert len(re.findall(r"CreateNtupleDColumn", block)) == 5


# ── analyze_efficiency.py: reads the new names (613f436) ──────────────────────

def test_analysis_reads_sipm_trees_by_new_names(analyze):
    assert re.search(r'get_tree\s*\(\s*f\s*,\s*"SiPMPhotons"\s*\)', analyze), (
        'analyze_efficiency.py should read get_tree(f, "SiPMPhotons")'
    )
    assert re.search(r'get_tree\s*\(\s*f\s*,\s*"SiPMHits"\s*\)', analyze), (
        'analyze_efficiency.py should read get_tree(f, "SiPMHits")'
    )


def test_analysis_no_longer_reads_old_names(analyze):
    """The reader must not fetch the old bare tree names."""
    assert not re.search(r'get_tree\s*\(\s*f\s*,\s*"Photons"\s*\)', analyze), (
        'analyze_efficiency.py still reads old "Photons" tree name'
    )
    assert not re.search(r'get_tree\s*\(\s*f\s*,\s*"Hits"\s*\)', analyze), (
        'analyze_efficiency.py still reads old "Hits" tree name'
    )


def test_analysis_other_trees_unchanged(analyze):
    """Regression: Primary and WLSPhoton trees are still read by their unchanged names."""
    assert re.search(r'get_tree\s*\(\s*f\s*,\s*"Primary"\s*\)', analyze)
    assert re.search(r'get_tree\s*\(\s*f\s*,\s*"WLSPhoton"\s*\)', analyze)


# ── docs: org files refer to the new names (4088143 + f33925d) ────────────────

def test_analysis_org_uses_new_ntuple_names(analysis_org):
    """analysis.org ntuple 0/1 section headers use the SiPM names."""
    assert re.search(r"Ntuple 0\s*[—–-]\s*SiPMPhotons", analysis_org), (
        "analysis.org ntuple 0 section should be titled SiPMPhotons"
    )
    assert re.search(r"Ntuple 1\s*[—–-]\s*SiPMHits", analysis_org), (
        "analysis.org ntuple 1 section should be titled SiPMHits"
    )


def test_physics_org_uses_new_ntuple_names(physics_org):
    """physics.org SiPM SD description refers to ntuple 0/1 by the new names."""
    assert "SiPMPhotons" in physics_org, "physics.org should reference SiPMPhotons (ntuple 0)"
    assert "SiPMHits" in physics_org, "physics.org should reference SiPMHits (ntuple 1)"
