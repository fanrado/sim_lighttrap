"""
Tests for the PMT readout mode (geometry.detectorType = "pmt").

Feature:
  The second stage of the light trap (blue-WLS slab + edge SiPMs + reflector
  foils + backplane leak counter) can be replaced by a PMT model: a 23 mm
  diameter photocathode disc (optional MgF2 window) facing the first layer
  across the LAr gap, read out by MyPMTDetector with a flat QE (default 100 %)
  inside [110, 500] nm and 0 outside.  The bench light source is a 14 mm
  diameter parallel VUV beam (GPS Plane/Circle, radius 7 mm).
  Plumbing:
    - config.hh/.cc: SimConfig.detectorType, pmtDiameter_mm,
      pmtWindowThickness_mm, pmtQE, pmtQEmin_nm, pmtQEmax_nm, source radius_cm,
      MgF2Config; validation of detectorType / ranges.
    - construction.{hh,cc}: /detector/{detectorType,pmtDiameter,pmtWindowThick,
      pmtQE,pmtQEmin,pmtQEmax}; G4Tubs photocathode (+ window) built only when
      detectorType == "pmt"; second-stage volumes skipped; SD wiring guarded.
    - detector.{hh,cc}: MyPMTDetector (terminal, QE band) → ntuples 9/10.
    - run.cc: ntuples 9 PMTPhotons / 10 PMTHits.
    - sim_lighttrap.cc: forwards the YAML keys and /gps/pos/radius.
    - sim_config_pmt.yaml + mac/run_pmt_beam.mac: ready-made bench setup.
    - detector.cc: missing pde_broadcom.dat warns instead of looping forever
      (that loop hung every run started outside the build directory).

Source-level checks (Geant4 can't be compiled in CI); same style as
tests/test_backplane_foil_config.py.
"""

import re

import pytest
import yaml

CONFIG_YAML     = "sim_config.yaml"
PMT_YAML        = "sim_config_pmt.yaml"
PMT_MAC         = "mac/run_pmt_beam.mac"
CONFIG_HH       = "include/config.hh"
CONFIG_CC       = "src/config.cc"
MAIN_CC         = "src/sim_lighttrap.cc"
CONSTRUCTION_HH = "include/construction.hh"
CONSTRUCTION_CC = "src/construction.cc"
DETECTOR_HH     = "include/detector.hh"
DETECTOR_CC     = "src/detector.cc"
RUN_CC          = "src/run.cc"
NAMEMAP_HH      = "include/namemap.hh"
CMAKE           = "CMakeLists.txt"

PMT_KEYS = {
    "pmtDiameter_mm": 23.0,
    "pmtWindowThickness_mm": 0.0,
    "pmtQE": 1.0,
    "pmtQEmin_nm": 110.0,
    "pmtQEmax_nm": 500.0,
}
MESSENGER = {
    "detectorType": "/detector/detectorType",
    "pmtDiameter_mm": "/detector/pmtDiameter",
    "pmtWindowThickness_mm": "/detector/pmtWindowThick",
    "pmtQE": "/detector/pmtQE",
    "pmtQEmin_nm": "/detector/pmtQEmin",
    "pmtQEmax_nm": "/detector/pmtQEmax",
}


def read(path):
    with open(path) as fh:
        return fh.read()


def strip_comments(code):
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", code)


@pytest.fixture(scope="module")
def pmt_doc():
    with open(PMT_YAML) as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def base_doc():
    with open(CONFIG_YAML) as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def construction_cc():
    return read(CONSTRUCTION_CC)


@pytest.fixture(scope="module")
def construction_code(construction_cc):
    return strip_comments(construction_cc)


# ── YAML: the ready-made PMT bench configuration ─────────────────────────────

def test_pmt_yaml_selects_pmt_mode(pmt_doc):
    assert pmt_doc["geometry"]["detectorType"] == "pmt"


@pytest.mark.parametrize("key,value", sorted(PMT_KEYS.items()))
def test_pmt_yaml_pmt_parameters(pmt_doc, key, value):
    assert key in pmt_doc["geometry"], f"sim_config_pmt.yaml geometry.{key} missing"
    assert pmt_doc["geometry"][key] == pytest.approx(value)


def test_pmt_yaml_photocathode_is_23mm(pmt_doc):
    assert pmt_doc["geometry"]["pmtDiameter_mm"] == pytest.approx(23.0)


def test_pmt_yaml_qe_band_is_110_to_500nm_at_100pct(pmt_doc):
    g = pmt_doc["geometry"]
    assert g["pmtQE"] == pytest.approx(1.0)
    assert g["pmtQEmin_nm"] == pytest.approx(110.0)
    assert g["pmtQEmax_nm"] == pytest.approx(500.0)


def test_pmt_yaml_source_is_14mm_circular_beam(pmt_doc):
    src = pmt_doc["source"]
    assert src["positionType"] == "Plane"
    assert src["positionShape"] == "Circle"
    assert src["radius_cm"] == pytest.approx(0.7), "14 mm beam → radius 7 mm = 0.7 cm"
    assert (src["centerX_cm"], src["centerY_cm"]) == (0.0, 0.0), "beam centred on the PMT axis"
    assert (src["directionX"], src["directionY"], src["directionZ"]) == (0.0, 0.0, 1.0), "parallel beam along +z"
    assert src["particle"] == "opticalphoton"


def test_pmt_yaml_source_is_vuv(pmt_doc):
    e = pmt_doc["source"]["energy_eV"]
    wl_nm = 1239.84193 / e
    assert 110.0 <= wl_nm <= 200.0, f"expected a VUV source, got {wl_nm:.1f} nm"


def test_pmt_yaml_keeps_first_layer(pmt_doc):
    g = pmt_doc["geometry"]
    for key in ("pTPlayerThickness_mm", "uvAcrylicThickness_mm", "LArThickness_mm", "lightTrapSize_cm"):
        assert key in g, f"first-layer key {key} missing from sim_config_pmt.yaml"


def test_pmt_yaml_mgf2_arrays_have_13_points(pmt_doc):
    m = pmt_doc["materials"]["mgf2"]
    assert len(m["rindex"]) == 13
    assert len(m["abslen_m"]) == 13


def test_base_yaml_defaults_to_sipm_and_documents_pmt_keys(base_doc):
    g = base_doc["geometry"]
    assert g["detectorType"] == "sipm", "the original two-layer design must stay the default"
    for key in PMT_KEYS:
        assert key in g, f"sim_config.yaml should document geometry.{key}"
    assert "radius_cm" in base_doc["source"]


# ── macro ────────────────────────────────────────────────────────────────────

def test_pmt_macro_switches_geometry_and_uses_circular_beam():
    mac = read(PMT_MAC)
    assert re.search(r"^/detector/detectorType\s+pmt\s*$", mac, re.M)
    assert re.search(r"^/detector/pmtDiameter\s+23\b", mac, re.M)
    assert re.search(r"^/run/reinitializeGeometry\s*$", mac, re.M)
    assert re.search(r"^/gps/pos/shape\s+Circle\s*$", mac, re.M)
    assert re.search(r"^/gps/pos/radius\s+7\s+mm\s*$", mac, re.M)
    assert re.search(r"^/gps/direction\s+0\s+0\s+1\s*$", mac, re.M)
    # geometry must be re-initialised BEFORE the run starts
    assert mac.index("/run/reinitializeGeometry") < mac.index("/run/beamOn")


# ── SimConfig plumbing ───────────────────────────────────────────────────────

def test_config_hh_has_pmt_fields():
    hh = strip_comments(read(CONFIG_HH))
    assert re.search(r'std::string\s+detectorType\s*=\s*"sipm"', hh)
    for field, default in (("pmtDiameter_mm", "23.0"), ("pmtWindowThickness_mm", "0.0"),
                           ("pmtQE", "1.0"), ("pmtQEmin_nm", "110.0"), ("pmtQEmax_nm", "500.0")):
        assert re.search(rf"double\s+{field}\s*=\s*{re.escape(default)}", hh), f"{field} default {default}"
    assert re.search(r"double\s+radius_cm\s*=", hh)
    assert "struct MgF2Config" in hh and re.search(r"MgF2Config\s+mgf2;", hh)


def test_config_cc_parses_and_validates():
    cc = strip_comments(read(CONFIG_CC))
    for key in ["detectorType", *PMT_KEYS]:
        assert f'geo["{key}"]' in cc, f"config.cc does not parse geometry.{key}"
    assert 'src["radius_cm"]' in cc
    assert 'mat["mgf2"]' in cc
    # invalid selector / ranges are rejected
    assert re.search(r'detectorType\s*!=\s*"sipm"\s*&&\s*cfg\.detectorType\s*!=\s*"pmt"', cc)
    assert "pmtDiameter_mm <= 0.0" in cc
    assert "pmtQEmin_nm >= cfg.pmtQEmax_nm" in cc


def test_main_forwards_yaml_to_messenger_and_gps_radius():
    main = strip_comments(read(MAIN_CC))
    for cmd in MESSENGER.values():
        assert f'"{cmd} "' in main, f"sim_lighttrap.cc does not forward {cmd}"
    assert '"/gps/pos/radius "' in main
    # detector commands precede the geometry re-initialisation
    assert main.index("/detector/detectorType") < main.index("/run/reinitializeGeometry")


# ── construction: messenger, geometry, SD wiring ─────────────────────────────

@pytest.mark.parametrize("cmd", sorted(set(MESSENGER.values())))
def test_messenger_properties_declared(construction_code, cmd):
    name = cmd.rsplit("/", 1)[1]
    assert re.search(rf'DeclareProperty\s*\(\s*"{name}"', construction_code), f"{cmd} not declared"


def test_construction_defaults(construction_code):
    assert re.search(r'fDetectorType\s*=\s*"sipm"', construction_code)
    assert re.search(r"pmtDiameter\s*=\s*23\.\s*\*\s*mm", construction_code)
    assert re.search(r"pmtQE\s*=\s*1\.0", construction_code)
    assert re.search(r"pmtQEmin_nm\s*=\s*110\.", construction_code)
    assert re.search(r"pmtQEmax_nm\s*=\s*500\.", construction_code)


def test_photocathode_is_a_tubs_disc_of_pmt_diameter(construction_code):
    assert '#include "G4Tubs.hh"' in read(CONSTRUCTION_HH)
    m = re.search(r'PMTPhotocathode\s*=\s*new\s+G4Tubs\s*\(\s*"PMTPhotocathode"\s*,\s*0\.\s*,\s*rPMT', construction_code)
    assert m, "photocathode must be a full G4Tubs disc of radius rPMT"
    assert re.search(r"rPMT\s*=\s*pmtDiameter\s*/\s*2\.", construction_code)


def test_window_is_optional_mgf2(construction_code):
    assert re.search(r"if\s*\(\s*pmtWindowThickness\s*>\s*0\.\s*\)\s*\{[^}]*new\s+G4Tubs\s*\(\s*\"PMTWindow\"", construction_code, re.S)
    assert re.search(r'new\s+G4LogicalVolume\s*\(\s*PMTWindow\s*,\s*mgf2', construction_code)
    assert re.search(r'FindOrBuildMaterial\s*\(\s*"G4_MAGNESIUM_FLUORIDE"', construction_code)
    assert "DefineMgF2Material();" in construction_code


def test_photocathode_material_matches_upstream_volume(construction_code):
    """No Fresnel boundary at the cathode face: LAr if bare, MgF2 behind a window."""
    assert re.search(r"cathodeMat\s*=\s*\(\s*pmtWindowThickness\s*>\s*0\.\s*\)\s*\?\s*mgf2\s*:\s*worldMat", construction_code)
    assert re.search(r"new\s+G4LogicalVolume\s*\(\s*PMTPhotocathode\s*,\s*cathodeMat", construction_code)


def test_pmt_branch_skips_second_stage(construction_code):
    """Blue WLS slab, SiPMs, foils and backplane leak det are only built in the else-branch."""
    m = re.search(r"if\s*\(\s*isPMT\s*\)\s*\{(.*?)\}\s*else\s*\{(.*?)\n  \}\n", construction_code, re.S)
    assert m, "expected an if (isPMT) { ... } else { ... } split in Construct()"
    pmt_branch, sipm_branch = m.group(1), m.group(2)
    assert "PMTPhotocathode" in pmt_branch
    for name in ("pTPsubstrate", "SiPMs", "VikuitiEdge", "BackplaneLeakDet"):
        assert name not in pmt_branch, f"{name} must not be built in PMT mode"
        assert name in sipm_branch, f"{name} must still be built in sipm mode"
    assert "PMTPhotocathode" not in sipm_branch


def test_unknown_detector_type_falls_back_to_sipm(construction_code):
    assert re.search(r'fDetectorType\s*!=\s*"sipm"\s*&&\s*fDetectorType\s*!=\s*"pmt"', construction_code)
    assert re.search(r'fDetectorType\s*=\s*"sipm";', construction_code)


def test_first_layer_gap_measured_to_selected_stage(construction_code):
    assert re.search(r"kStage2FrontZ\s*=\s*isPMT\s*\?\s*kPMTFrontZ\s*:\s*kBlueWLSFrontZ", construction_code)
    assert re.search(r"kUVAcrylBackZ\s*=\s*kStage2FrontZ\s*-\s*LArthickness", construction_code)


def test_sd_wiring_is_guarded_and_pmt_sd_gets_qe_band(construction_code):
    sd = construction_code[construction_code.index("ConstructSDandField"):]
    assert re.search(r"if\s*\(\s*logicSiPMs\s*\)", sd), "SiPM SD must be guarded (null in PMT mode)"
    assert re.search(r"if\s*\(\s*logicBackplaneLeakDet\s*\)", sd), "leak SD must be guarded (null in PMT mode)"
    assert re.search(r"if\s*\(\s*logicPMTPhotocathode\s*\)", sd)
    assert re.search(r'new\s+MyPMTDetector\s*\(\s*"PMTDetector"\s*,\s*pmtQE\s*,\s*pmtQEmin_nm\s*,\s*pmtQEmax_nm\s*\)', sd)
    # first-layer counters are built in both modes and stay unguarded
    assert "logicFirstLayerExitDet->SetSensitiveDetector" in sd
    assert "logicFirstLayerEdgeDet->SetSensitiveDetector" in sd


def test_vis_attributes_guarded_for_absent_volumes(construction_code):
    vis = construction_code[construction_code.index("vaWLS"):construction_code.index("return physWorld")]
    for lv in ("logicpTPsubstrate", "logicSiPMs", "logicVikuitiEdge", "logicBackplaneLeakDet",
               "logicPMTWindow", "logicPMTPhotocathode"):
        assert re.search(rf"if\s*\(\s*{lv}\s*\)\s*{lv}->SetVisAttributes|if\s*\(\s*{lv}\s*\)\s*\n\s*{lv}->SetVisAttributes", vis), \
            f"{lv}->SetVisAttributes must be null-guarded"


# ── MyPMTDetector ────────────────────────────────────────────────────────────

def test_pmt_detector_class_declared():
    hh = strip_comments(read(DETECTOR_HH))
    assert re.search(r"class\s+MyPMTDetector\s*:\s*public\s+G4VSensitiveDetector", hh)
    assert re.search(r"MyPMTDetector\s*\(\s*G4String\s+\w+\s*,\s*G4double\s+\w+\s*,\s*G4double\s+\w+\s*,\s*G4double\s+\w+\s*\)", hh)
    assert re.search(r"G4double\s+Efficiency\s*\(\s*G4double", hh)


def test_pmt_detector_efficiency_is_flat_inside_band_zero_outside():
    cc = strip_comments(read(DETECTOR_CC))
    body = re.search(r"G4double\s+MyPMTDetector::Efficiency\s*\([^)]*\)\s*const\s*\{(.*?)\}", cc, re.S)
    assert body, "MyPMTDetector::Efficiency missing"
    b = body.group(1)
    assert re.search(r"wl_nm\s*<\s*fWlMin\s*\|\|\s*wl_nm\s*>\s*fWlMax", b)
    assert "return 0." in b and "return fQE" in b


def test_pmt_detector_is_terminal_and_fills_ntuples_9_and_10():
    cc = strip_comments(read(DETECTOR_CC))
    body = cc[cc.index("MyPMTDetector::ProcessHits"):]
    assert "SetTrackStatus(fStopAndKill)" in body
    assert re.search(r"AddNtupleRow\s*\(\s*9\s*\)", body)
    assert re.search(r"if\s*\(\s*G4UniformRand\s*\(\s*\)\s*<\s*Efficiency\s*\(\s*wl\s*\)\s*\)", body)
    assert re.search(r"AddNtupleRow\s*\(\s*10\s*\)", body)
    assert "GetParentID() == 0" in body, "primary flag must distinguish beam photons from WLS daughters"


def test_run_cc_defines_pmt_ntuples():
    run = strip_comments(read(RUN_CC))
    assert re.search(r'CreateNtuple\s*\(\s*"PMTPhotons"', run)
    assert re.search(r'CreateNtuple\s*\(\s*"PMTHits"', run)
    assert re.search(r"FinishNtuple\s*\(\s*9\s*\)", run)
    assert re.search(r"FinishNtuple\s*\(\s*10\s*\)", run)
    for name in ("PMTPhotons", "PMTHits"):
        start = run.index(f'CreateNtuple("{name}"')
        block = run[start:run.index("FinishNtuple", start)]
        cols = re.findall(r'CreateNtuple[IDS]Column\s*\(\s*"([^"]+)"', block)
        assert cols == ["eventID", "fX", "fY", "fZ", "fT", "fwl", "fcosTheta", "primary"], (name, cols)


def test_namemap_has_mgf2():
    assert re.search(r'\{\s*"G4_MAGNESIUM_FLUORIDE"\s*,\s*6\s*\}', read(NAMEMAP_HH))


# ── regression: the PDE-file read must not hang ──────────────────────────────

def test_sipm_pde_file_read_cannot_loop_forever():
    cc = strip_comments(read(DETECTOR_CC))
    ctor = cc[cc.index("MySensitiveDetector::MySensitiveDetector"):cc.index("MySensitiveDetector::~MySensitiveDetector")]
    assert "while(1)" not in ctor.replace(" ", ""), "while(1)/eof() loop spins forever on a missing file"
    assert re.search(r"while\s*\(\s*datafile\s*>>\s*wl\s*>>\s*pde\s*\)", ctor)
    assert "SiPMPDEFile" in ctor and "JustWarning" in ctor
    assert "GetVectorLength() > 0" in cc, "empty PDE table must evaluate to PDE = 0, not read past the end"


# ── build wiring ─────────────────────────────────────────────────────────────

def test_cmake_copies_all_yaml_configs():
    cm = read(CMAKE)
    assert re.search(r"file\s*\(\s*GLOB\s+YAML_FILES\s+\$\{PROJECT_SOURCE_DIR\}/\*\.yaml\s*\)", cm)
    assert re.search(r"file\s*\(\s*COPY\s+\$\{YAML_FILES\}\s+DESTINATION\s+\$\{PROJECT_BINARY_DIR\}\s*\)", cm)
