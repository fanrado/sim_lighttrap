"""
Tests for the PMT readout (branch vuv_meas_pmt: first layer + PMT only).

Feature:
  The LightTrap first layer (pTP film on UV acrylic) is read out by a PMT: a
  23 mm diameter photocathode disc (optional MgF2 window) facing the first
  layer across the LAr gap, read out by MyPMTDetector with a flat QE (default
  100 %) inside [110, 500] nm and 0 outside.  The bench light source is a
  14 mm diameter parallel VUV beam (GPS Plane/Circle, radius 7 mm).
  The two-layer design (blue-WLS slab + SiPMs + foils) is NOT on this branch.
  Plumbing:
    - config.hh/.cc: pmtDiameter_mm, pmtWindowThickness_mm, pmtQE,
      pmtQEmin_nm, pmtQEmax_nm, source radius_cm, MgF2Config; range checks.
    - construction.{hh,cc}: /detector/{pmtDiameter,pmtWindowThick,pmtQE,
      pmtQEmin,pmtQEmax}; G4Tubs photocathode (+ window) always built.
    - detector.{hh,cc}: MyPMTDetector (terminal, QE band) → ntuples 6/7.
    - run.cc: ntuples 6 PMTPhotons / 7 PMTHits (see test_output_ntuples.py).
    - sim_lighttrap.cc: forwards the YAML keys and /gps/pos/radius.
    - sim_config.yaml, mac/run.mac, mac/vis.mac: 14 mm beam setup.

Source-level checks (Geant4 can't be compiled in CI).
"""

import re

import pytest
import yaml

CONFIG_YAML     = "sim_config.yaml"
PMT_YAML        = "sim_config.yaml"
PMT_MAC         = "mac/run.mac"
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
    "pmtDiameter_mm": 23.0,          # R6836 photocathode min. effective area
    "pmtTubeDiameter_mm": 28.2,      # R6836 tube / faceplate diameter
    "pmtLength_mm": 92.0,            # R6836 body length
    "pmtWindowThickness_mm": 1.5,    # MgF2 faceplate (assumption)
    "pmtWallThickness_mm": 1.0,
    "pmtQE": 1.0,
    "pmtQEmin_nm": 110.0,
    "pmtQEmax_nm": 500.0,
}
MESSENGER = {
    "pmtDiameter_mm": "/detector/pmtDiameter",
    "pmtTubeDiameter_mm": "/detector/pmtTubeDiameter",
    "pmtLength_mm": "/detector/pmtLength",
    "pmtWindowThickness_mm": "/detector/pmtWindowThick",
    "pmtWallThickness_mm": "/detector/pmtWallThick",
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

def test_yaml_has_no_two_layer_keys(pmt_doc):
    g = pmt_doc["geometry"]
    for key in ("detectorType", "nSiPMs", "pTPSubstrateThickness_mm", "backplaneFoil"):
        assert key not in g, f"two-layer key geometry.{key} must not be on this branch"
    for mat in ("blueWLS", "acrylicMcMaster", "vikuiti", "ptfe"):
        assert mat not in pmt_doc["materials"], f"two-layer material {mat} must not be on this branch"


@pytest.mark.parametrize("key,value", sorted(PMT_KEYS.items()))
def test_pmt_yaml_pmt_parameters(pmt_doc, key, value):
    assert key in pmt_doc["geometry"], f"sim_config.yaml geometry.{key} missing"
    assert pmt_doc["geometry"][key] == pytest.approx(value)


def test_pmt_yaml_photocathode_is_23mm(pmt_doc):
    assert pmt_doc["geometry"]["pmtDiameter_mm"] == pytest.approx(23.0)


def test_pmt_yaml_r6836_tube_and_7mm_gap(pmt_doc):
    g = pmt_doc["geometry"]
    assert g["pmtTubeDiameter_mm"] == pytest.approx(28.2), "R6836 faceplate/tube Ø 28.2 mm"
    assert g["pmtLength_mm"] == pytest.approx(92.0), "R6836 body length 92 mm"
    assert g["pmtTubeDiameter_mm"] > g["pmtDiameter_mm"], "window is wider than the photocathode"
    assert g["pmtWindowThickness_mm"] > 0.0, "the R6836 has an MgF2 faceplate"
    assert g["LArThickness_mm"] == pytest.approx(7.0), "PMT 7 mm behind the back of the acrylic"


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
        assert key in g, f"first-layer key {key} missing from sim_config.yaml"


def test_pmt_yaml_mgf2_arrays_have_13_points(pmt_doc):
    m = pmt_doc["materials"]["mgf2"]
    assert len(m["rindex"]) == 13
    assert len(m["abslen_m"]) == 13


def test_yaml_source_radius_documented(base_doc):
    assert "radius_cm" in base_doc["source"]


# ── macro ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("mac_file", ["mac/run.mac", "mac/run_vuv_spectrum.mac", "mac/run_285.mac"])
def test_run_macros_use_14mm_circular_beam(mac_file):
    mac = read(mac_file)
    assert re.search(r"^/gps/pos/type\s+Plane\s*$", mac, re.M)
    assert re.search(r"^/gps/pos/shape\s+Circle\s*$", mac, re.M)
    assert re.search(r"^/gps/pos/radius\s+7\s+mm\s*$", mac, re.M)
    # on the beam axis, in front of the sample (z < -10 mm) and inside the default world (|z| < 182 mm)
    m = re.search(r"^/gps/pos/centre\s+0\.?\s+0\.?\s+(\S+)\s+(\w+)\s*$", mac, re.M)
    assert m, f"{mac_file}: /gps/pos/centre 0 0 <z> <unit> expected"
    z_mm = float(m.group(1)) * {"cm": 10.0, "mm": 1.0, "m": 1000.0}[m.group(2)]
    assert -182.0 < z_mm < -10.0, f"{mac_file}: beam start z = {z_mm} mm must be inside the world and before the sample"
    assert re.search(r"^/gps/direction\s+0\s+0\s+1\s*$", mac, re.M)
    assert "/gps/pos/halfx" not in mac and "Square" not in [l.split()[-1] for l in mac.splitlines() if l.startswith("/gps/pos/shape")]
    assert "/detector/" not in mac, "run macros must not need geometry commands: PMT is the only design"


def test_vis_macro_draws_geometry_and_preloads_beam():
    mac = read("mac/vis.mac")
    assert re.search(r"^/vis/open\s+Qt3D", mac, re.M)
    assert re.search(r"^/vis/drawVolume", mac, re.M)
    assert re.search(r"^/gps/pos/shape\s+Circle\s*$", mac, re.M)
    assert re.search(r"^/gps/pos/radius\s+7\s+mm\s*$", mac, re.M)
    # must not start a run by itself (interactive session); comments may mention it
    commands = [l.strip() for l in mac.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    assert not any(c.startswith("/run/beamOn") for c in commands)
    assert not any(c.startswith("/detector/") for c in commands)


def test_offscreen_macro_renders_geometry_headlessly():
    mac = read("mac/draw_offscreen.mac")
    assert re.search(r"^/run/initialize\s*$", mac, re.M), "geometry must be built before /vis/drawVolume"
    assert mac.index("/run/initialize") < mac.index("/vis/drawVolume")
    assert re.search(r"^/vis/open\s+TSG_OFFSCREEN\s*$", mac, re.M)
    assert re.search(r"^/vis/drawTree\s+!\s+ATree\s*$", mac, re.M)
    # culling must be enabled, or the invisible world box hides the zoomed views
    assert re.search(r"^/vis/viewer/set/culling\s+global\s+true\s*$", mac, re.M)
    assert re.search(r"^/vis/viewer/set/culling\s+invisible\s+true\s*$", mac, re.M)
    assert "RayTracer" not in [l.split()[0] for l in mac.splitlines() if l.startswith("/vis/open")]
    files = re.findall(r"^/vis/tsg/offscreen/set/file\s+(\S+)", mac, re.M)
    assert len(files) >= 3 and all(f.endswith(".png") for f in files)
    assert len(re.findall(r"^/vis/viewer/flush", mac, re.M)) >= len(files)


# ── SimConfig plumbing ───────────────────────────────────────────────────────

def test_config_hh_has_pmt_fields():
    hh = strip_comments(read(CONFIG_HH))
    for gone in ("detectorType", "nSiPMs", "pTPSubstrateThickness_mm", "backplaneFoil",
                 "BlueWLSConfig", "VikuitiConfig", "PTFEConfig", "AcrylicMcMasterConfig"):
        assert gone not in hh, f"two-layer field {gone} must not be on this branch"
    for field, default in (("pmtDiameter_mm", "23.0"), ("pmtTubeDiameter_mm", "28.2"),
                           ("pmtLength_mm", "92.0"), ("pmtWindowThickness_mm", "1.5"),
                           ("pmtWallThickness_mm", "1.0"), ("LArThickness_mm", "7.0"),
                           ("pmtQE", "1.0"), ("pmtQEmin_nm", "110.0"), ("pmtQEmax_nm", "500.0")):
        assert re.search(rf"double\s+{field}\s*=\s*{re.escape(default)}", hh), f"{field} default {default}"
    assert re.search(r"double\s+radius_cm\s*=", hh)
    assert "struct MgF2Config" in hh and re.search(r"MgF2Config\s+mgf2;", hh)


def test_config_cc_parses_and_validates():
    cc = strip_comments(read(CONFIG_CC))
    for key in PMT_KEYS:
        assert f'geo["{key}"]' in cc, f"config.cc does not parse geometry.{key}"
    assert 'src["radius_cm"]' in cc
    assert 'mat["mgf2"]' in cc
    for gone in ("blueWLS", "vikuiti", "ptfe", "acrylicMcMaster", "nSiPMs", "backplaneFoil", "detectorType"):
        assert gone not in cc, f"two-layer key {gone} must not be parsed on this branch"
    # invalid ranges are rejected
    assert "pmtDiameter_mm <= 0.0" in cc
    assert "pmtTubeDiameter_mm <= cfg.pmtDiameter_mm" in cc
    assert "pmtLength_mm <= cfg.pmtWindowThickness_mm + cfg.pmtWallThickness_mm" in cc
    assert "pmtQEmin_nm >= cfg.pmtQEmax_nm" in cc


def test_main_forwards_yaml_to_messenger_and_gps_radius():
    main = strip_comments(read(MAIN_CC))
    for cmd in MESSENGER.values():
        assert f'"{cmd} "' in main, f"sim_lighttrap.cc does not forward {cmd}"
    assert '"/gps/pos/radius "' in main
    # detector commands precede the geometry re-initialisation
    # detector commands precede the geometry re-initialisation of the YAML block
    # (an earlier reinitializeGeometry exists for the macro-only with_sample path)
    assert main.index("/detector/pmtDiameter") < main.rindex("/run/reinitializeGeometry")
    for gone in ("/detector/nSiPMs", "/detector/backplaneFoil", "/detector/detectorType", "/detector/pTPsubstratethickness"):
        assert gone not in main


# ── construction: messenger, geometry, SD wiring ─────────────────────────────

@pytest.mark.parametrize("cmd", sorted(set(MESSENGER.values())))
def test_messenger_properties_declared(construction_code, cmd):
    name = cmd.rsplit("/", 1)[1]
    assert re.search(rf'DeclareProperty\s*\(\s*"{name}"', construction_code), f"{cmd} not declared"


def test_construction_defaults(construction_code):
    assert re.search(r"pmtDiameter\s*=\s*23\.\s*\*\s*mm", construction_code)
    assert re.search(r"pmtTubeDiameter\s*=\s*28\.2\s*\*\s*mm", construction_code)
    assert re.search(r"pmtLength\s*=\s*92\.\s*\*\s*mm", construction_code)
    assert re.search(r"pmtWindowThickness\s*=\s*1\.5\s*\*\s*mm", construction_code)
    assert re.search(r"LArthickness\s*=\s*7\.\s*\*\s*mm", construction_code)
    assert re.search(r"pmtQE\s*=\s*1\.0", construction_code)
    assert re.search(r"pmtQEmin_nm\s*=\s*110\.", construction_code)
    assert re.search(r"pmtQEmax_nm\s*=\s*500\.", construction_code)


def test_photocathode_is_a_tubs_disc_of_pmt_diameter(construction_code):
    assert '#include "G4Tubs.hh"' in read(CONSTRUCTION_HH)
    m = re.search(r'PMTPhotocathode\s*=\s*new\s+G4Tubs\s*\(\s*"PMTPhotocathode"\s*,\s*0\.\s*,\s*rCath', construction_code)
    assert m, "photocathode must be a full G4Tubs disc of radius rCath"
    assert re.search(r"rCath\s*=\s*pmtDiameter\s*/\s*2\.", construction_code)


def test_faceplate_is_full_tube_diameter_mgf2(construction_code):
    """The MgF2 window spans the 28.2 mm tube, not just the 23 mm photocathode."""
    assert re.search(r"if\s*\(\s*tWin\s*>\s*0\.\s*\)\s*\{[^}]*new\s+G4Tubs\s*\(\s*\"PMTWindow\"\s*,\s*0\.\s*,\s*rTube", construction_code, re.S)
    assert re.search(r"rTube\s*=\s*pmtTubeDiameter\s*/\s*2\.", construction_code)
    assert re.search(r'new\s+G4LogicalVolume\s*\(\s*PMTWindow\s*,\s*mgf2', construction_code)
    assert re.search(r'FindOrBuildMaterial\s*\(\s*"G4_MAGNESIUM_FLUORIDE"', construction_code)
    assert "DefineMgF2Material();" in construction_code


def test_pmt_body_vacuum_envelope_endcap(construction_code):
    """Physical cylinder: vacuum interior (RINDEX 1) holding the photocathode, opaque glass wall + end cap."""
    assert re.search(r'FindOrBuildMaterial\s*\(\s*"G4_Galactic"', construction_code)
    assert re.search(r'FindOrBuildMaterial\s*\(\s*"G4_Pyrex_Glass"', construction_code)
    assert re.search(r'new\s+G4Tubs\s*\(\s*"PMTVacuum"\s*,\s*0\.\s*,\s*rInner', construction_code)
    assert re.search(r'new\s+G4Tubs\s*\(\s*"PMTEnvelope"\s*,\s*rInner\s*,\s*rTube', construction_code), "side wall is a hollow tube"
    assert re.search(r'new\s+G4Tubs\s*\(\s*"PMTEndCap"\s*,\s*0\.\s*,\s*rInner', construction_code)
    assert re.search(r"rInner\s*=\s*rTube\s*-\s*pmtWallThickness", construction_code)
    # photocathode is a daughter of the vacuum, flush with its front face
    assert re.search(r'logicPMTPhotocathode\s*,\s*"physPMTPhotocathode"\s*,\s*logicPMTVacuum', construction_code)
    assert re.search(r"-halfVac\s*\+\s*kPhotocathodeThick\s*/\s*2\.", construction_code)
    # vacuum has a refractive index so photons propagate; the glass has none (absorbing)
    vac = construction_code[construction_code.index("MyLightTrapConstruction::DefinePMTBodyMaterials()"):
                            construction_code.index("MyLightTrapConstruction::DefineMaterials()")]
    assert "pmtVacuum->SetMaterialPropertiesTable" in vac
    assert "pmtGlass->SetMaterialPropertiesTable" not in vac
    # world grows with the PMT length so the tube fits
    assert re.search(r"lighttrapsize\s*\*\s*0\.6\s*\+\s*pmtLength", construction_code)


def test_photocathode_material_matches_upstream_volume(construction_code):
    """No Fresnel boundary at the cathode face: MgF2 behind the faceplate, LAr if bare."""
    assert re.search(r"cathodeMat\s*=\s*\(\s*tWin\s*>\s*0\.\s*\)\s*\?\s*mgf2\s*:\s*worldMat", construction_code)
    assert re.search(r"new\s+G4LogicalVolume\s*\(\s*PMTPhotocathode\s*,\s*cathodeMat", construction_code)


def test_no_second_stage_volumes(construction_code):
    """The blue-WLS slab, SiPMs, reflector foils and backplane leak counter are gone."""
    for name in ("pTPsubstrate", "SiPMs", "VikuitiEdge", "ReflectiveFoilBackPlane",
                 "BackplaneLeakDet", "bluewlsacrylic", "acrylicMcMaster", "G4LogicalSkinSurface",
                 "isPMT", "fDetectorType", "nSiPMs"):
        assert name not in construction_code, f"two-layer symbol {name} must not be on this branch"
    assert "PMTPhotocathode" in construction_code


def test_first_layer_gap_measured_to_pmt_face(construction_code):
    assert re.search(r"kPMTFrontZ\s*=\s*0\.", construction_code)
    assert re.search(r"kUVAcrylBackZ\s*=\s*kPMTFrontZ\s*-\s*LArthickness", construction_code)
    assert re.search(r"zVacA\s*=\s*kPMTFrontZ\s*\+\s*tWin", construction_code)
    assert re.search(r"zVacB\s*=\s*kPMTFrontZ\s*\+\s*pmtLength\s*-\s*pmtWallThickness", construction_code)


def test_sd_wiring(construction_code):
    sd = construction_code[construction_code.index("ConstructSDandField"):]
    assert re.search(r'new\s+MyPMTDetector\s*\(\s*"PMTDetector"\s*,\s*pmtQE\s*,\s*pmtQEmin_nm\s*,\s*pmtQEmax_nm\s*,\s*fPMTQEFile\s*\)', sd)
    assert "logicPMTPhotocathode->SetSensitiveDetector(pmtDet)" in sd
    assert "logicFirstLayerExitDet->SetSensitiveDetector" in sd
    assert "logicFirstLayerEdgeDet->SetSensitiveDetector" in sd
    assert "MySensitiveDetector" not in sd and "BackplaneLeakDetector" not in sd


def test_vis_attributes_guard_optional_window(construction_code):
    vis = construction_code[construction_code.index("vaPMTWin"):construction_code.index("return physWorld")]
    assert re.search(r"if\s*\(\s*logicPMTWindow\s*\)\s*logicPMTWindow->SetVisAttributes", vis)
    assert "logicPMTPhotocathode->SetVisAttributes(vaPMTCat)" in vis
    assert "logicPMTEnvelope->SetVisAttributes" in vis and "logicPMTEndCap->SetVisAttributes" in vis


def test_with_sample_switch():
    """with_sample=on|off CLI arg, geometry.withSample YAML key, /detector/withSample messenger."""
    main = strip_comments(read(MAIN_CC))
    assert "parseWithSampleArg" in main and '"with_sample="' in main
    assert "cfg.withSample = withSampleArg" in main, "command line must override the YAML"
    assert '"/detector/withSample "' in main
    assert re.search(r'DeclareProperty\s*\(\s*"withSample"\s*,\s*fWithSample', read(CONSTRUCTION_CC))
    assert re.search(r"G4bool\s+fWithSample;", read(CONSTRUCTION_HH))
    assert re.search(r"bool\s+withSample\s*=\s*true;", strip_comments(read(CONFIG_HH)))
    assert 'geo["withSample"]' in read(CONFIG_CC)
    with open(CONFIG_YAML) as fh:
        assert yaml.safe_load(fh)["geometry"]["withSample"] is True


def test_geometry_rebuilt_immediately_after_switches():
    """/run/reinitializeGeometry only flags the rebuild; main must follow it with
    /run/initialize so the viewer / volume dump / first run see the new geometry
    (regression: with_sample=off still showed the sample in the Qt viewer)."""
    main = strip_comments(read(MAIN_CC))
    reinit = [m.start() for m in re.finditer(r'"/run/reinitializeGeometry"', main)]
    assert reinit, "no /run/reinitializeGeometry in main"
    for pos in reinit:
        nxt = main.find('"/run/initialize"', pos)
        assert nxt != -1 and nxt - pos < 400, "each /run/reinitializeGeometry must be followed by /run/initialize"


def test_world_medium_switch():
    """worldMedium gar|lar|vacuum: YAML key, CLI world_medium=, messenger, material selection."""
    with open(CONFIG_YAML) as fh:
        doc = yaml.safe_load(fh)
    assert doc["geometry"]["worldMedium"] == "gar", "bench measurement is in argon gas"
    assert "gar" in doc["materials"] and "lar" in doc["materials"]
    hh = strip_comments(read(CONFIG_HH))
    assert re.search(r'std::string\s+worldMedium\s*=\s*"gar"', hh)
    assert "struct GArConfig" in hh and re.search(r"GArConfig\s+gar;", hh)
    cc = strip_comments(read(CONFIG_CC))
    assert 'geo["worldMedium"]' in cc and 'mat["gar"]' in cc
    assert re.search(r'worldMedium\s*!=\s*"gar"\s*&&\s*cfg\.worldMedium\s*!=\s*"lar"\s*&&\s*cfg\.worldMedium\s*!=\s*"vacuum"', cc)
    main = strip_comments(read(MAIN_CC))
    assert "parseWorldMediumArg" in main and '"world_medium="' in main and '"/detector/worldMedium "' in main
    con = strip_comments(read(CONSTRUCTION_CC))
    assert re.search(r'DeclareProperty\s*\(\s*"worldMedium"\s*,\s*fWorldMedium', con)
    assert re.search(r'fWorldMedium\s*=\s*"gar";', con)
    assert re.search(r'FindOrBuildMaterial\s*\(\s*"G4_Ar"', con)
    assert re.search(r'if\s*\(\s*fWorldMedium\s*==\s*"gar"\s*\)\s*worldMat\s*=\s*garMat', con)
    assert re.search(r'fWorldMedium\s*==\s*"lar"\s*\)\s*worldMat\s*=\s*larMat', con)
    assert re.search(r'fWorldMedium\s*==\s*"vacuum"\s*\)\s*worldMat\s*=\s*pmtVacuum', con)
    # the gas has RINDEX/ABSLENGTH/RAYLEIGH tables, and counters/world are built from worldMat
    gar = con[con.index("MyLightTrapConstruction::DefineGArMaterial()"):con.index("MyLightTrapConstruction::DefineMgF2Material()")]
    for prop in ("RINDEX", "ABSLENGTH", "RAYLEIGH"):
        assert f'"{prop}"' in gar
    assert "garMat->SetMaterialPropertiesTable" in gar
    assert re.search(r'new\s+G4LogicalVolume\s*\(\s*solidWorld\s*,\s*worldMat', con)
    assert re.search(r'FirstLayerExitDet\s*,\s*worldMat', con)
    nm = read(NAMEMAP_HH)
    assert re.search(r'\{\s*"G4_Ar"\s*,\s*7\s*\}', nm)


def test_without_sample_keeps_beam_pmt_and_reference_plane(construction_cc):
    # raw source (comments kept): the "} // fWithSample" block-end markers are comments
    body = construction_cc[construction_cc.index("MyLightTrapConstruction::Construct()"):]
    # sample volumes and edge counters are inside if (fWithSample) blocks
    i_sample = body.index('new G4Box("pTPlayer"')
    assert "if (fWithSample) {" in body[:i_sample]
    i_edge = body.index('new G4Box("FirstLayerEdgeDet"')
    assert body.rfind("if (fWithSample) {", 0, i_edge) > body.rfind("} // fWithSample", 0, i_edge) - 1
    # PMT, backplane reference counter and world are unconditional
    for name in ('new G4Box("FirstLayerExitDet"', 'new G4Tubs("PMTPhotocathode"', 'new G4Tubs("PMTWindow"'):
        i = body.index(name)
        assert body.rfind("if (fWithSample) {", 0, i) < body.rfind("} // fWithSample", 0, i), f"{name} must not depend on the sample"
    # SD / vis / surfaces guarded
    sd = body[body.index("ConstructSDandField"):]
    assert re.search(r"if\s*\(\s*logicFirstLayerEdgeDet\s*\)", sd)
    assert "logicFirstLayerExitDet->SetSensitiveDetector" in sd
    assert re.search(r"if\s*\(\s*logicpTPlayer\s*\)\s*logicpTPlayer->SetVisAttributes", body)
    assert re.search(r"if\s*\(\s*fWithSample\s*\)\s*\{\s*G4OpticalSurface\s*\*pTPRoughSurf", body)


def test_source_outside_world_is_rejected_and_world_is_resizable():
    gen = strip_comments(read("src/generator.cc"))
    assert "SourceOutsideWorld" in gen and "FatalException" in gen
    assert re.search(r"solid->Inside\s*\(\s*pos\s*\)\s*==\s*kOutside", gen)
    con = strip_comments(read(CONSTRUCTION_CC))
    assert re.search(r'DeclareProperty\s*\(\s*"worldHalfZ"\s*,\s*worldHalfZ', con)
    assert re.search(r"new\s+G4Box\s*\(\s*\"solidWorld\"\s*,[^;]*WorldHalfZ\(\)", con)
    assert re.search(r"autoHalf\s*=\s*lighttrapsize\s*\*\s*0\.6\s*\+\s*pmtLength", con)
    assert 'geo["worldHalfZ_mm"]' in strip_comments(read(CONFIG_CC))
    assert '"/detector/worldHalfZ "' in strip_comments(read(MAIN_CC))
    with open(CONFIG_YAML) as fh:
        assert yaml.safe_load(fh)["geometry"]["worldHalfZ_mm"] == 0.0
    # every shipped macro / YAML source sits inside the default world (|z| < 18.2 cm)
    for mac_file in ("mac/vis.mac", "mac/run.mac", "mac/run_vuv_spectrum.mac", "mac/run_285.mac"):
        m = re.search(r"^/gps/pos/centre\s+\S+\s+\S+\s+(\S+)\s+(\w+)", read(mac_file), re.M)
        assert m, f"{mac_file}: no /gps/pos/centre"
        z = float(m.group(1)) * {"cm": 10.0, "mm": 1.0, "m": 1000.0}[m.group(2)]
        assert abs(z) < 182.0, f"{mac_file}: source z = {z} mm is outside the default world"


def test_pmt_qe_table_support():
    """pmtQEFile: YAML key, CLI pmt_qe=, messenger, loader with interpolation, example file."""
    hh = read(DETECTOR_HH)
    assert "LoadQETable" in hh and "fTableWl" in hh and "qeFile" in hh
    cc = strip_comments(read(DETECTOR_CC))
    body = cc[cc.index("MyPMTDetector::Efficiency"):cc.index("MyPMTDetector::Description")]
    assert "upper_bound" in body, "table must be linearly interpolated"
    assert re.search(r"wl_nm\s*<\s*fTableWl\.front\(\)\s*\|\|\s*wl_nm\s*>\s*fTableWl\.back\(\)", body), "QE = 0 outside the table"
    assert "PMTQEFile" in cc and "FatalException" in cc, "unreadable table must abort"
    assert re.search(r'DeclareProperty\s*\(\s*"pmtQEFile"\s*,\s*fPMTQEFile', read(CONSTRUCTION_CC))
    assert re.search(r'new\s+MyPMTDetector\s*\([^;]*fPMTQEFile\s*\)', strip_comments(read(CONSTRUCTION_CC)))
    main = strip_comments(read(MAIN_CC))
    assert "parsePMTQEArg" in main and '"pmt_qe="' in main and '"/detector/pmtQEFile "' in main
    assert 'geo["pmtQEFile"]' in strip_comments(read(CONFIG_CC))
    assert "std::string pmtQEFile;" in strip_comments(read(CONFIG_HH))
    # example table: 2 columns, QE in [0,1], covers the R6836 115-320 nm band, 0 beyond it
    rows = []
    for line in read("input/pmt_qe_r6836_example.dat").splitlines():
        line = line.split("#")[0].strip()
        if line:
            w, q = line.split()
            rows.append((float(w), float(q)))
    assert len(rows) >= 5
    assert all(0.0 <= q <= 1.0 for _, q in rows)
    assert min(w for w, _ in rows) <= 115 and max(w for w, _ in rows) >= 320
    peak_w = max(rows, key=lambda r: r[1])[0]
    assert 200 <= peak_w <= 260, "Cs-Te solar-blind peak expected around 240 nm"
    assert dict(rows)[254.0] == pytest.approx(0.137, abs=0.005), "anchored to 28 mA/W at 254 nm"
    # the shipped YAML keeps the flat ideal QE (file commented out) and documents the key
    with open(CONFIG_YAML) as fh:
        g = yaml.safe_load(fh)["geometry"]
    assert "pmtQEFile" not in g or not g["pmtQEFile"]
    assert "pmtQEFile" in read(CONFIG_YAML)


def test_yaml_geometry_block_covers_requested_items():
    with open(CONFIG_YAML) as fh:
        g = yaml.safe_load(fh)["geometry"]
    for key in ("pTPlayerThickness_mm", "pTPsigmaAlpha_rad", "lightTrapSize_cm", "uvAcrylicThickness_mm",
                "LArThickness_mm", "worldMedium", "worldHalfZ_mm", "withSample"):
        assert key in g, f"geometry.{key} missing from sim_config.yaml"


def test_qt_session_opens_with_yaml_and_vis_macro():
    main = strip_comments(read(MAIN_CC))
    m = re.search(r"bool\s+isVisMacro\s*=\s*([^;]+);", main)
    assert m, "isVisMacro missing"
    expr = m.group(1)
    assert 'macroFile.find("vis")' in expr
    assert not expr.strip().startswith("!hasConfig &&"), "the viewer must not be disabled by a YAML config"


def test_roughness_demo_macros_and_script():
    demo = read("mac/roughness_demo.mac")
    assert re.search(r"^/detector/pTPsigmaAlpha\s+0\.8", demo, re.M)
    assert re.search(r"^/run/reinitializeGeometry", demo, re.M) and re.search(r"^/run/initialize", demo, re.M)
    assert re.search(r"^/gps/energy\s+3\.0996\s+eV", demo, re.M), "400 nm beam: pTP must not absorb it"
    assert demo.index("/run/initialize") < demo.index("/run/beamOn")
    off = read("mac/roughness_off.mac")
    assert re.search(r"^/detector/pTPsigmaAlpha\s+0\.0", off, re.M) and re.search(r"^/gps/energy\s+9\.68\s+eV", off, re.M)
    panel = read("mac/draw_roughness_panel.mac")
    assert "{sa}" in panel and "{out}" in panel and "TSG_OFFSCREEN" in panel
    vis = read("mac/vis.mac")
    assert "roughness_demo.mac" in vis and "roughness_off.mac" in vis
    sh = read("scripts/draw_roughness.sh")
    assert "/control/alias sa" in sh and "draw_roughness_panel.mac" in sh


def test_scan_script_runs_with_and_without_sample():
    src = read("scripts/scan_wavelength.py")
    assert "with_sample=" in src and '"--sample"' in src
    assert "T_total" in src and "T_direct" in src and "T_wls" in src


def test_scan_script_exists_and_uses_pmt_trees():
    src = read("scripts/scan_wavelength.py")
    assert '"PMTHits"' in src and '"Primary"' in src and '"WLSPhoton"' in src
    assert "/gps/pos/radius 7 mm" in src and "/gps/pos/shape Circle" in src
    assert "1239.84193" in src
    assert "cwd=rundir" in src, "each wavelength must run in its own directory (fixed output file name)"


# ── MyPMTDetector ────────────────────────────────────────────────────────────

def test_pmt_detector_class_declared():
    hh = strip_comments(read(DETECTOR_HH))
    assert re.search(r"class\s+MyPMTDetector\s*:\s*public\s+G4VSensitiveDetector", hh)
    assert re.search(r"MyPMTDetector\s*\(\s*G4String\s+\w+\s*,\s*G4double\s+\w+\s*,\s*G4double\s+\w+\s*,\s*G4double\s+\w+\s*,\s*const\s+G4String&\s+\w+\s*=\s*\"\"\s*\)", hh)
    assert re.search(r"G4double\s+Efficiency\s*\(\s*G4double", hh)


def test_pmt_detector_efficiency_is_flat_inside_band_zero_outside():
    cc = strip_comments(read(DETECTOR_CC))
    start = cc.index("G4double MyPMTDetector::Efficiency")
    b = cc[start:cc.index("MyPMTDetector::Description", start)]
    assert re.search(r"wl_nm\s*<\s*fWlMin\s*\|\|\s*wl_nm\s*>\s*fWlMax", b)
    assert "return 0." in b and "return fQE" in b


def test_pmt_detector_is_terminal_and_fills_ntuples_6_and_7():
    cc = strip_comments(read(DETECTOR_CC))
    body = cc[cc.index("MyPMTDetector::ProcessHits"):]
    assert "SetTrackStatus(fStopAndKill)" in body
    assert re.search(r"AddNtupleRow\s*\(\s*6\s*\)", body)
    assert re.search(r"if\s*\(\s*G4UniformRand\s*\(\s*\)\s*<\s*Efficiency\s*\(\s*wl\s*\)\s*\)", body)
    assert re.search(r"AddNtupleRow\s*\(\s*7\s*\)", body)
    assert "GetParentID() == 0" in body, "primary flag must distinguish beam photons from WLS daughters"


def test_run_cc_defines_pmt_ntuples():
    run = strip_comments(read(RUN_CC))
    assert re.search(r'CreateNtuple\s*\(\s*"PMTPhotons"', run)
    assert re.search(r'CreateNtuple\s*\(\s*"PMTHits"', run)
    assert re.search(r"FinishNtuple\s*\(\s*6\s*\)", run)
    assert re.search(r"FinishNtuple\s*\(\s*7\s*\)", run)
    for name in ("PMTPhotons", "PMTHits"):
        start = run.index(f'CreateNtuple("{name}"')
        block = run[start:run.index("FinishNtuple", start)]
        cols = re.findall(r'CreateNtuple[IDS]Column\s*\(\s*"([^"]+)"', block)
        assert cols == ["eventID", "fX", "fY", "fZ", "fT", "fwl", "fcosTheta", "primary"], (name, cols)


def test_namemap_has_mgf2_and_no_two_layer_materials():
    nm = read(NAMEMAP_HH)
    assert re.search(r'\{\s*"G4_MAGNESIUM_FLUORIDE"\s*,\s*6\s*\}', nm)
    assert "bluewlsacrylic" not in nm and "acrylicMcMaster" not in nm


def test_no_sipm_detector_class():
    assert "MySensitiveDetector" not in read(DETECTOR_HH)
    assert "MySensitiveDetector" not in read(DETECTOR_CC)
    assert "pde_broadcom" not in read(DETECTOR_CC)


# ── build wiring ─────────────────────────────────────────────────────────────

def test_cmake_copies_all_yaml_configs():
    cm = read(CMAKE)
    assert re.search(r"file\s*\(\s*GLOB\s+YAML_FILES\s+\$\{PROJECT_SOURCE_DIR\}/\*\.yaml\s*\)", cm)
    assert re.search(r"file\s*\(\s*COPY\s+\$\{YAML_FILES\}\s+DESTINATION\s+\$\{PROJECT_BINARY_DIR\}\s*\)", cm)
