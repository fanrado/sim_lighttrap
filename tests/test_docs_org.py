"""
Tests for the five org-mode documentation files added in commit 6587474.

Covers:
  - File existence for all five docs
  - Org-mode header fields (#+TITLE, #+AUTHOR, #+DATE, #+OPTIONS)
  - Required section headings per file
  - Cross-file link consistency (overview.org → other docs)
  - NameMap integer codes agree between geometry.org and physics.org
  - Physics constants are internally consistent (hc, VUV energy/wavelength)
"""

import re
import math
import os
import pytest

DOCS_DIR = "docs"
DOC_FILES = [
    "overview.org",
    "geometry.org",
    "physics.org",
    "running.org",
    "analysis.org",
]

HC_EV_NM = 1239.84193  # hc in eV·nm


# ── helpers ───────────────────────────────────────────────────────────────────

def read_doc(filename):
    path = os.path.join(DOCS_DIR, filename)
    with open(path) as fh:
        return fh.read()


def org_headings(text):
    """Return list of top-level (* ...) headings in an org file."""
    return [m.group(1).strip() for m in re.finditer(r"^\* (.+)$", text, re.MULTILINE)]


def org_header_value(text, keyword):
    """Return the value of an org-mode #+KEYWORD: header, or None."""
    m = re.search(rf"^#\+{keyword}:\s*(.+)$", text, re.MULTILINE | re.IGNORECASE)
    return m.group(1).strip() if m else None


def org_file_links(text):
    """Return list of filenames referenced by [[file:<name>]] links."""
    return re.findall(r"\[\[file:([^\]]+\.org)\]", text)


def namemap_codes(text):
    """
    Parse '| Name | Code |' table rows from an org table.
    Returns dict {name: int_code} for rows that have an integer code.
    """
    codes = {}
    for row in re.finditer(r"\|\s*(\w[\w\s]*?)\s*\|\s*(\d+)\s*\|", text):
        name = row.group(1).strip()
        code = int(row.group(2))
        codes[name] = code
    return codes


# ── 1. File existence ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("filename", DOC_FILES)
def test_file_exists(filename):
    assert os.path.isfile(os.path.join(DOCS_DIR, filename)), (
        f"Expected documentation file docs/{filename} to exist"
    )


# ── 2. Org-mode header fields ─────────────────────────────────────────────────

@pytest.mark.parametrize("filename", DOC_FILES)
def test_has_title(filename):
    text = read_doc(filename)
    assert org_header_value(text, "TITLE"), f"{filename}: missing #+TITLE:"


@pytest.mark.parametrize("filename", DOC_FILES)
def test_has_author(filename):
    text = read_doc(filename)
    assert org_header_value(text, "AUTHOR"), f"{filename}: missing #+AUTHOR:"


@pytest.mark.parametrize("filename", DOC_FILES)
def test_has_date(filename):
    text = read_doc(filename)
    date_val = org_header_value(text, "DATE")
    assert date_val, f"{filename}: missing #+DATE:"
    assert re.match(r"\d{4}-\d{2}-\d{2}", date_val), (
        f"{filename}: #+DATE: '{date_val}' is not in YYYY-MM-DD format"
    )


@pytest.mark.parametrize("filename", DOC_FILES)
def test_has_options(filename):
    text = read_doc(filename)
    assert org_header_value(text, "OPTIONS"), f"{filename}: missing #+OPTIONS:"


@pytest.mark.parametrize("filename", DOC_FILES)
def test_has_at_least_one_heading(filename):
    text = read_doc(filename)
    headings = org_headings(text)
    assert len(headings) >= 1, f"{filename}: no top-level headings found"


# ── 3. Required section headings per file ─────────────────────────────────────

REQUIRED_HEADINGS = {
    "overview.org": ["Purpose", "Repository Layout", "Simulation Flow", "Related Documentation"],
    "geometry.org": ["Coordinate Convention", "Module Layout", "World Volume",
                     "Detector Components", "Geometry Messenger Commands", "NameMap Integer Codes"],
    "physics.org": ["Physics List", "Primary Particle Generator",
                    "Tracking and Stepping Logic", "Sensitive Detector Response"],
    "running.org": ["Prerequisites", "Building", "Running", "Output", "Macro Files Reference"],
    "analysis.org": ["Output File", "Ntuple Reference", "Key Analysis Quantities", "Input Data"],
}


@pytest.mark.parametrize("filename,expected", [
    (f, h) for f, hs in REQUIRED_HEADINGS.items() for h in hs
])
def test_required_heading_present(filename, expected):
    text = read_doc(filename)
    headings = org_headings(text)
    assert expected in headings, (
        f"{filename}: required heading '{expected}' not found. "
        f"Found: {headings}"
    )


# ── 4. Cross-file link consistency (overview.org) ────────────────────────────

def test_overview_links_to_all_other_docs():
    text = read_doc("overview.org")
    linked = set(org_file_links(text))
    other_docs = set(DOC_FILES) - {"overview.org"}
    missing = other_docs - linked
    assert not missing, (
        f"overview.org is missing links to: {missing}. Found links: {linked}"
    )


def test_all_linked_files_exist():
    for filename in DOC_FILES:
        text = read_doc(filename)
        for linked in org_file_links(text):
            path = os.path.join(DOCS_DIR, linked)
            assert os.path.isfile(path), (
                f"{filename}: linked file '{linked}' does not exist at docs/{linked}"
            )


# ── 5. NameMap codes agree between geometry.org and physics.org ───────────────

def test_namemap_codes_consistent_across_files():
    geom_codes = namemap_codes(read_doc("geometry.org"))
    phys_codes = namemap_codes(read_doc("physics.org"))

    assert geom_codes, "geometry.org: no NameMap integer codes found"
    assert phys_codes, "physics.org: no NameMap integer codes found"

    common_names = set(geom_codes) & set(phys_codes)
    assert common_names, (
        "No common NameMap entries between geometry.org and physics.org"
    )
    for name in common_names:
        assert geom_codes[name] == phys_codes[name], (
            f"NameMap mismatch for '{name}': "
            f"geometry.org={geom_codes[name]}, physics.org={phys_codes[name]}"
        )


def test_namemap_ptp_code_is_1():
    codes = namemap_codes(read_doc("geometry.org"))
    assert "pTP" in codes, "geometry.org NameMap: 'pTP' entry not found"
    assert codes["pTP"] == 1, f"pTP code should be 1, got {codes['pTP']}"


def test_namemap_scintillation_code_is_100():
    codes = namemap_codes(read_doc("physics.org"))
    assert "Scintillation" in codes, "physics.org NameMap: 'Scintillation' not found"
    assert codes["Scintillation"] == 100


def test_namemap_opwls_code_is_101():
    codes = namemap_codes(read_doc("physics.org"))
    assert "OpWLS" in codes, "physics.org NameMap: 'OpWLS' not found"
    assert codes["OpWLS"] == 101


# ── 6. Physics constants consistency ─────────────────────────────────────────

def test_vuv_energy_wavelength_consistency_in_physics():
    """physics.org quotes 9.68 eV ≈ 128 nm; verify with hc."""
    text = read_doc("physics.org")
    # energy mentioned: 9.68 eV
    m = re.search(r"([\d.]+)\s*eV", text)
    assert m, "physics.org: no eV energy value found"
    energy_ev = float(m.group(1))
    wl_nm = HC_EV_NM / energy_ev
    assert 120.0 < wl_nm < 135.0, (
        f"physics.org: {energy_ev} eV → {wl_nm:.2f} nm, expected ~128 nm"
    )


def test_overview_vuv_wavelength_is_128nm():
    text = read_doc("overview.org")
    # Simulation flow refers to 128 nm
    assert "128 nm" in text, "overview.org: expected reference to '128 nm' LAr scintillation peak"


def test_geometry_rayleigh_scattering_90cm():
    text = read_doc("geometry.org")
    assert "90 cm" in text, (
        "geometry.org: expected Rayleigh scattering length of '90 cm'"
    )


def test_geometry_vikuiti_reflectivity_98pct():
    text = read_doc("geometry.org")
    # Should mention 98% reflectivity
    assert re.search(r"98\s*%", text), (
        "geometry.org: expected Vikuiti reflectivity '98 %' or '98%'"
    )


def test_physics_primary_particle_is_opticalphoton():
    text = read_doc("physics.org")
    assert "opticalphoton" in text, (
        "physics.org: primary particle type 'opticalphoton' not mentioned"
    )


# ── 7. Analysis ntuple IDs are sequential (0-7) ───────────────────────────────

def test_analysis_has_eight_ntuples():
    text = read_doc("analysis.org")
    # Match "** Ntuple N —" headings
    ntuple_ids = [int(m.group(1)) for m in re.finditer(r"Ntuple (\d+)\s+[—–]", text)]
    assert len(ntuple_ids) == 8, (
        f"analysis.org: expected 8 ntuples, found {len(ntuple_ids)}: {ntuple_ids}"
    )


def test_analysis_ntuple_ids_are_sequential():
    text = read_doc("analysis.org")
    ntuple_ids = sorted(int(m.group(1)) for m in re.finditer(r"Ntuple (\d+)\s+[—–]", text))
    assert ntuple_ids == list(range(8)), (
        f"analysis.org: ntuple IDs {ntuple_ids} are not sequential 0-7"
    )


def test_analysis_hits_ntuple_is_subset_of_photons():
    """analysis.org must state Hits is a subset of Photons (ntuple 0)."""
    text = read_doc("analysis.org")
    # The document says "Subset of ntuple 0"
    assert re.search(r"[Ss]ubset of ntuple 0", text), (
        "analysis.org: should state that Hits ntuple is a subset of ntuple 0 (Photons)"
    )


# ── 8. Running doc references correct output filename pattern ─────────────────

def test_running_output_filename_pattern():
    text = read_doc("running.org")
    assert "output_apexltsim" in text, (
        "running.org: expected output filename 'output_apexltsim<runID>.root'"
    )


def test_running_and_analysis_agree_on_output_pattern():
    run_text = read_doc("running.org")
    analysis_text = read_doc("analysis.org")
    assert "output_apexltsim" in run_text
    assert "output_apexltsim" in analysis_text


# ── 9. Macro file names referenced in running.org ─────────────────────────────

@pytest.mark.parametrize("macro", ["vis.mac", "run.mac", "det.mac", "scandet.mac"])
def test_running_references_macro(macro):
    text = read_doc("running.org")
    assert macro in text, f"running.org: expected reference to macro file '{macro}'"
