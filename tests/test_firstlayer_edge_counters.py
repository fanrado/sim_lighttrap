"""
Tests for the first-layer ±x edge counters in construction.cc.

Feature (commit ab6532f, beads sim_lighttrap-mwk):
  New pass-through LAr counter slabs on both ±x faces of the first-layer
  (pTP/UV-acrylic) stack.  One shared logical volume (logicFirstLayerEdgeDet)
  is placed twice (+x copy 0, −x copy 1); a single non-killing MyLeakDetector
  ("FirstLayerEdgeDetector", 8, false) records lateral escapes into ntuple 8
  (region c, FirstLayerEdges).

  Sizing:
    kEdgeDetThick     = 0.1*mm                          (slab thickness in x)
    kFirstLayerThick  = uvAcrylicThickness + pTPlayerthickness
    kFirstLayerCenterZ= kUVAcrylBackZ - kFirstLayerThick/2.
    box half-extents  = (kEdgeDetThick/2, lighttrapsize/2, kFirstLayerThick/2)
    placements at x = ±(lighttrapsize/2 + kEdgeDetThick/2), z = kFirstLayerCenterZ

  The slabs are worldMat (LAr) — optically invisible, no boundary — like the
  backplane counter.

These are static source-parsing tests (the Geant4 C++ cannot be compiled in this
environment), mirroring tests/test_pass_through_counter.py.
"""

import re

import pytest

CONSTRUCTION_HH = "include/construction.hh"
CONSTRUCTION_CC = "src/construction.cc"


def read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def cons_hh():
    return read(CONSTRUCTION_HH)


@pytest.fixture(scope="module")
def cons_cc():
    return read(CONSTRUCTION_CC)


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


# ── header: new member declarations ──────────────────────────────────────────

def test_header_declares_edge_det_members(cons_hh):
    code = strip_comments(cons_hh)
    assert re.search(r"G4Box\s*\*\s*FirstLayerEdgeDet\s*;", code), "FirstLayerEdgeDet member missing"
    assert re.search(
        r"G4LogicalVolume\s*\*\s*logicFirstLayerEdgeDet\s*;", code
    ), "logicFirstLayerEdgeDet member missing"


def test_header_declares_both_edge_placements(cons_hh):
    """Two physical-volume pointers back the +x and −x placements of the shared slab."""
    code = strip_comments(cons_hh)
    assert "physFirstLayerEdgeDet_pX" in code, "physFirstLayerEdgeDet_pX member missing"
    assert "physFirstLayerEdgeDet_nX" in code, "physFirstLayerEdgeDet_nX member missing"


# ── sizing constants ─────────────────────────────────────────────────────────

def test_edge_det_thickness_constant(cons_cc):
    code = strip_comments(cons_cc)
    assert re.search(
        r"G4double\s+kEdgeDetThick\s*=\s*0\.1\s*\*\s*mm", code
    ), "kEdgeDetThick should be declared as 0.1*mm"


def test_first_layer_thickness_spans_both_films(cons_cc):
    """kFirstLayerThick must be the acrylic + pTP film thickness (the full first layer)."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"kFirstLayerThick\s*=\s*uvAcrylicThickness\s*\+\s*pTPlayerthickness", code
    )
    assert m, "kFirstLayerThick should be uvAcrylicThickness + pTPlayerthickness"


def test_first_layer_center_z(cons_cc):
    """The edge slabs are centred at the first-layer mid-plane, half a layer ahead of the back face."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"kFirstLayerCenterZ\s*=\s*kUVAcrylBackZ\s*-\s*kFirstLayerThick\s*/\s*2\.", code
    )
    assert m, "kFirstLayerCenterZ should be kUVAcrylBackZ - kFirstLayerThick/2."


# ── geometry: shared box + two placements ────────────────────────────────────

def test_edge_box_half_extents(cons_cc):
    """Box: thin in x (kEdgeDetThick/2), full y (lighttrapsize/2), full first-layer z."""
    code = strip_comments(cons_cc)
    m = re.search(
        r'FirstLayerEdgeDet\s*=\s*new\s+G4Box\(\s*"FirstLayerEdgeDet"\s*,'
        r"\s*kEdgeDetThick\s*/\s*2\.\s*,"
        r"\s*lighttrapsize\s*/\s*2\.\s*,"
        r"\s*kFirstLayerThick\s*/\s*2\.\s*\)",
        code,
    )
    assert m, "FirstLayerEdgeDet box half-extents should be (kEdgeDetThick/2, lighttrapsize/2, kFirstLayerThick/2)"


def test_edge_slab_built_from_worldmat(cons_cc):
    """Regression: the edge slab must be worldMat (LAr) so it stays optically invisible."""
    code = strip_comments(cons_cc)
    assert re.search(
        r"logicFirstLayerEdgeDet\s*=\s*new\s+G4LogicalVolume\(\s*FirstLayerEdgeDet\s*,\s*worldMat",
        code,
    ), "edge slab logical volume should be built from worldMat (LAr)"


def test_plus_x_placement(cons_cc):
    """+x slab: placed just outside the +x face at copy number 0."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"physFirstLayerEdgeDet_pX\s*=\s*new\s+G4PVPlacement\(\s*0\s*,\s*"
        r"G4ThreeVector\(\s*\+\(\s*lighttrapsize\s*/\s*2\.\s*\+\s*kEdgeDetThick\s*/\s*2\.\s*\)\s*,"
        r"\s*0\.\s*,\s*kFirstLayerCenterZ\s*\)\s*,\s*"
        r'logicFirstLayerEdgeDet\s*,\s*"physFirstLayerEdgeDet_pX"\s*,\s*logicWorld\s*,'
        r"\s*false\s*,\s*0\s*,",
        code,
    )
    assert m, "+x edge placement missing/wrong (expected copy 0 at +（lighttrapsize/2 + kEdgeDetThick/2), kFirstLayerCenterZ)"


def test_minus_x_placement(cons_cc):
    """−x slab: placed just outside the −x face at copy number 1, sharing the logical volume."""
    code = strip_comments(cons_cc)
    m = re.search(
        r"physFirstLayerEdgeDet_nX\s*=\s*new\s+G4PVPlacement\(\s*0\s*,\s*"
        r"G4ThreeVector\(\s*-\(\s*lighttrapsize\s*/\s*2\.\s*\+\s*kEdgeDetThick\s*/\s*2\.\s*\)\s*,"
        r"\s*0\.\s*,\s*kFirstLayerCenterZ\s*\)\s*,\s*"
        r'logicFirstLayerEdgeDet\s*,\s*"physFirstLayerEdgeDet_nX"\s*,\s*logicWorld\s*,'
        r"\s*false\s*,\s*1\s*,",
        code,
    )
    assert m, "−x edge placement missing/wrong (expected copy 1 at −（lighttrapsize/2 + kEdgeDetThick/2), kFirstLayerCenterZ)"


def test_both_placements_share_one_logical_volume(cons_cc):
    """The +x and −x placements reuse the same logicFirstLayerEdgeDet (one logical volume placed twice)."""
    code = strip_comments(cons_cc)
    placements = re.findall(
        r"new\s+G4PVPlacement\([^;]*?logicFirstLayerEdgeDet[^;]*?;", code
    )
    assert len(placements) == 2, f"expected exactly 2 placements of logicFirstLayerEdgeDet, found {len(placements)}"


# ── SD wiring: pass-through counter on ntuple 8 ──────────────────────────────

def test_edge_sd_is_pass_through_on_ntuple_8(cons_cc):
    """A single non-killing MyLeakDetector on ntuple 8 serves the edge counters."""
    code = strip_comments(cons_cc)
    m = re.search(
        r'new\s+MyLeakDetector\s*\(\s*"FirstLayerEdgeDetector"\s*,\s*8\s*,\s*false\s*\)',
        code,
    )
    assert m, 'expected new MyLeakDetector("FirstLayerEdgeDetector", 8, false)'


def test_edge_sd_assigned_to_shared_logical_volume(cons_cc):
    """The SD is attached to the shared logical volume so both placements are sensitive."""
    code = strip_comments(cons_cc)
    assert re.search(
        r"logicFirstLayerEdgeDet\s*->\s*SetSensitiveDetector\s*\(\s*edgeDet\s*\)", code
    ), "logicFirstLayerEdgeDet should be assigned the edge SD (edgeDet)"
