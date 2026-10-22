"""
Tests for smooth, file-configurable WLS emission spectra (pTP + blue-WLS).

Feature (commit 209e42a):
  WLSCOMPONENT was pinned to the shared 13-point energy grid, giving only ~4
  usable points for pTP and 2 for blue-WLS, so Geant4 rendered the emission as
  piecewise-linear segments.  This commit adds a shared addWLSEmission() helper
  (src/construction.cc) with three-way precedence:
      1. file table   (materials.<mat>.wlscomponent_file, arbitrary # of points)
      2. inline 13-pt  (materials.<mat>.wlscomponent, shared grid, back-compat)
      3. built-in smooth asymmetric Gaussian on a dedicated 40-point fine grid
  Config loading (src/config.cc) gains loadEmissionFile()/dirOf(), storing the
  file spectrum in PTPConfig/BlueWLSConfig.emissionWl_nm/emissionIntensity.
  Example templates: input/ptp_emission.dat (peak 340 nm), input/bluewls_emission.dat
  (peak 430 nm).

Two kinds of tests below:
  * Functional tests of the example .dat files, parsed with the same rules the
    C++ loader uses (strip after '#', skip blanks, two numeric columns).
  * Static source-parsing tests of the C++ (which cannot be compiled here),
    mirroring tests/test_forward_direction_flag.py.
"""

import os
import re

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONSTRUCTION_CC = os.path.join(REPO_ROOT, "src", "construction.cc")
CONFIG_CC = os.path.join(REPO_ROOT, "src", "config.cc")
CONFIG_HH = os.path.join(REPO_ROOT, "include", "config.hh")
CONSTRUCTION_HH = os.path.join(REPO_ROOT, "include", "construction.hh")
PTP_DAT = os.path.join(REPO_ROOT, "input", "ptp_emission.dat")
BLUEWLS_DAT = os.path.join(REPO_ROOT, "input", "bluewls_emission.dat")

EVUM = 1.239841939  # eV*µm


def read(path):
    with open(path) as fh:
        return fh.read()


def strip_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def parse_dat(path):
    """Parse a WLS .dat table exactly as loadEmissionFile does: drop text after
    '#', skip lines without two numbers.  Returns list of (wavelength, intensity)."""
    rows = []
    for line in read(path).splitlines():
        h = line.find("#")
        if h != -1:
            line = line[:h]
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            w, v = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        rows.append((w, v))
    return rows


@pytest.fixture(scope="module")
def construction_cc():
    return read(CONSTRUCTION_CC)


@pytest.fixture(scope="module")
def config_cc():
    return read(CONFIG_CC)


# ── Example data files (functional) ──────────────────────────────────────────

@pytest.mark.parametrize("path,peak_nm", [(PTP_DAT, 340.0), (BLUEWLS_DAT, 430.0)])
def test_dat_has_at_least_two_rows(path, peak_nm):
    """The loader rejects <2 data rows; the templates must satisfy that."""
    assert len(parse_dat(path)) >= 2


@pytest.mark.parametrize("path,peak_nm", [(PTP_DAT, 340.0), (BLUEWLS_DAT, 430.0)])
def test_dat_peaks_at_expected_wavelength(path, peak_nm):
    """Peak intensity sits at the documented emission peak (pTP 340, blue 430 nm)."""
    rows = parse_dat(path)
    wl_at_peak = max(rows, key=lambda r: r[1])[0]
    assert wl_at_peak == pytest.approx(peak_nm), (
        f"{os.path.basename(path)} peak at {wl_at_peak} nm, expected {peak_nm}"
    )


@pytest.mark.parametrize("path", [PTP_DAT, BLUEWLS_DAT])
def test_dat_intensities_nonnegative(path):
    assert all(v >= 0.0 for _, v in parse_dat(path))


@pytest.mark.parametrize("path", [PTP_DAT, BLUEWLS_DAT])
def test_dat_brackets_band_with_zero_endpoints(path):
    """The templates document zero-intensity points at each wavelength end for a
    clean roll-off; verify the min- and max-wavelength rows are zero."""
    rows = sorted(parse_dat(path), key=lambda r: r[0])
    assert rows[0][1] == 0.0, "lowest-wavelength endpoint should be zero"
    assert rows[-1][1] == 0.0, "highest-wavelength endpoint should be zero"


@pytest.mark.parametrize("path", [PTP_DAT, BLUEWLS_DAT])
def test_dat_energy_strictly_increasing_after_sort_dedup(path):
    """Emulate addWLSEmission's file branch: nm→eV, sort ascending, drop dups —
    the result must be strictly increasing (Geant4's AddProperty requirement)."""
    energies = sorted(EVUM / (w / 1000.0) for w, _ in parse_dat(path))
    deduped = []
    for e in energies:
        if deduped and e <= deduped[-1]:
            continue
        deduped.append(e)
    assert all(b > a for a, b in zip(deduped, deduped[1:]))
    # No exact-duplicate wavelengths in the templates, so dedup keeps everything.
    assert len(deduped) == len(energies)


# ── config.hh: new parallel-array fields ─────────────────────────────────────

@pytest.mark.parametrize("struct", ["PTPConfig", "BlueWLSConfig"])
def test_config_struct_has_emission_arrays(struct):
    code = read(CONFIG_HH)
    m = re.search(rf"struct\s+{struct}\s*\{{(.*?)\}};", code, re.DOTALL)
    assert m, f"{struct} not found"
    body = m.group(1)
    assert "emissionWl_nm" in body, f"{struct} missing emissionWl_nm"
    assert "emissionIntensity" in body, f"{struct} missing emissionIntensity"


# ── config.cc: file loading & path resolution ────────────────────────────────

def test_dirof_helper_present(config_cc):
    code = strip_comments(config_cc)
    assert re.search(r"std::string\s+dirOf\s*\(", code), "dirOf() helper missing"


def test_loadEmissionFile_tries_cwd_then_cfgdir_for_relative(config_cc):
    """Relative paths resolve against cwd first, then the config file's dir."""
    code = strip_comments(config_cc)
    m = re.search(r"candidates\s*=\s*(.*?);", code, re.DOTALL)
    assert m, "candidate list not found"
    cand = m.group(1)
    assert "relOrAbs" in cand and "cfgDir + relOrAbs" in cand, (
        "relative branch should try relOrAbs then cfgDir + relOrAbs"
    )
    # An absolute path is used verbatim (single candidate).
    assert "absolute ?" in cand


def test_loadEmissionFile_strips_hash_and_skips_blank(config_cc):
    code = strip_comments(config_cc)
    body = re.search(
        r"loadEmissionFile\s*\([^)]*\)\s*\{(.*?)\n\}", config_cc, re.DOTALL
    )
    assert body, "loadEmissionFile body not found"
    b = body.group(1)
    assert "line.find('#')" in b, "should strip text after '#'"
    assert re.search(r"if\s*\(\s*ss\s*>>\s*w\s*>>\s*v\s*\)", b), (
        "should only keep lines with two parsed numbers"
    )


def test_loadEmissionFile_requires_two_rows(config_cc):
    code = strip_comments(config_cc)
    assert re.search(r"wl\.size\(\)\s*<\s*2", code), (
        "loadEmissionFile must reject fewer than 2 data rows"
    )


@pytest.mark.parametrize("mat", ["ptp", "blueWLS"])
def test_wlscomponent_file_wired_for_material(config_cc, mat):
    """Each material parses wlscomponent_file into its emission arrays."""
    code = strip_comments(config_cc)
    label = "pTP" if mat == "ptp" else "blueWLS"
    m = re.search(
        rf'n\["wlscomponent_file"\][^;]*loadEmissionFile\(\s*"{label}"[^;]*'
        rf'emissionWl_nm[^;]*emissionIntensity',
        code,
        re.DOTALL,
    )
    assert m, f"wlscomponent_file not wired to loadEmissionFile for {mat}"


def test_parseMaterials_receives_config_dir(config_cc):
    """fromFile passes dirOf(path) so relative spectrum files resolve correctly."""
    code = strip_comments(config_cc)
    assert re.search(r"parseMaterials\(\s*mat\s*,\s*dirOf\(\s*path\s*\)\s*\)", code)
    assert re.search(r"parseMaterials\([^)]*const std::string&\s*cfgDir", code)


# ── construction.hh / construction.cc: addWLSEmission precedence & math ───────

def test_addWLSEmission_declared(construction_cc):
    hdr = read(CONSTRUCTION_HH)
    assert re.search(r"void\s+addWLSEmission\s*\(", hdr), (
        "addWLSEmission not declared in construction.hh"
    )


def addwls_body(code):
    m = re.search(
        r"MyLightTrapConstruction::addWLSEmission\s*\([^{]*\)\s*\{(.*?)\n\}",
        code,
        re.DOTALL,
    )
    assert m, "addWLSEmission definition not found"
    return m.group(1)


def test_addWLSEmission_precedence_file_then_inline_then_gaussian(construction_cc):
    """Branch order must be: file (fileWl) → inline13 → built-in Gaussian."""
    body = strip_comments(construction_cc)
    body = addwls_body(body)
    file_pos = body.find("fileWl.empty()")
    inline_pos = body.find("inline13.empty()")
    # the else (Gaussian) branch is marked by the fine-grid loop constant
    gauss_pos = body.find("kNEm")
    assert -1 < file_pos < inline_pos < gauss_pos, (
        "precedence should be file > inline13 > Gaussian"
    )


def test_addWLSEmission_file_branch_sorts_and_dedups(construction_cc):
    body = addwls_body(strip_comments(construction_cc))
    assert "std::sort(pts.begin(), pts.end())" in body, "file spectrum must be sorted"
    assert re.search(r"p\.first\s*<=\s*eE\.back\(\)\s*\)\s*continue", body), (
        "duplicate/non-increasing energies must be skipped"
    )


def test_addWLSEmission_nm_to_ev_conversion(construction_cc):
    """Wavelength[nm] → energy[eV] via EVUM/(wl/1000) in both file and Gaussian branches."""
    body = addwls_body(strip_comments(construction_cc))
    assert re.search(r"EVUM\s*/\s*\(\s*fileWl\[i\]\s*/\s*1000\.?\s*\)", body)
    assert re.search(r"EVUM\s*/\s*\(\s*lam\s*/\s*1000\.?\s*\)", body)


def test_addWLSEmission_gaussian_is_asymmetric(construction_cc):
    """σ switches between red/blue side of the peak, giving an asymmetric bell."""
    body = addwls_body(strip_comments(construction_cc))
    assert re.search(r"\(\s*lam\s*>=\s*peak\s*\)\s*\?\s*sigRed\s*:\s*sigBlue", body), (
        "asymmetric sigma selection (lam>=peak ? sigRed : sigBlue) missing"
    )
    assert re.search(r"std::exp\(\s*-\s*d\s*\*\s*d\s*/\s*\(\s*2\.?\s*\*\s*sig\s*\*\s*sig", body), (
        "Gaussian exp(-d^2/(2 sig^2)) missing"
    )


def test_addWLSEmission_gaussian_walks_high_to_low_wavelength(construction_cc):
    """Grid walks λ high→low so photon energy is strictly ascending for Geant4."""
    body = addwls_body(strip_comments(construction_cc))
    assert re.search(
        r"lam\s*=\s*lamMax\s*-\s*\(\s*lamMax\s*-\s*lamMin\s*\)\s*\*\s*i\s*/\s*\(\s*kNEm\s*-\s*1\s*\)",
        body,
    ), "Gaussian grid should sweep lamMax → lamMin"


@pytest.mark.parametrize(
    "func,peak,sigBlue,sigRed,lamMin,lamMax",
    [
        ("DefinePTPMaterial", 340.0, 18.0, 30.0, 305.0, 460.0),
        ("DefineBlueWLSMaterial", 430.0, 20.0, 32.0, 375.0, 545.0),
    ],
)
def test_material_calls_addWLSEmission_with_expected_params(
    construction_cc, func, peak, sigBlue, sigRed, lamMin, lamMax
):
    """Each material wires its own file/inline arrays and Gaussian defaults."""
    code = strip_comments(construction_cc)
    m = re.search(rf"MyLightTrapConstruction::{func}\s*\([^)]*\)\s*\{{(.*)", code, re.DOTALL)
    assert m, f"{func} not found"
    body = m.group(1)
    call = re.search(r"addWLSEmission\(mpt,(.*?)\);", body, re.DOTALL)
    assert call, f"{func} does not call addWLSEmission"
    args = call.group(1)
    for val in (peak, sigBlue, sigRed, lamMin, lamMax):
        assert re.search(rf"\b{val:.0f}\.", args), (
            f"{func}: expected Gaussian param {val} in addWLSEmission call"
        )
    mat = "ptp" if func == "DefinePTPMaterial" else "blueWLS"
    assert f"{mat}.emissionWl_nm" in args and f"{mat}.emissionIntensity" in args, (
        f"{func} should pass {mat} file arrays"
    )
    assert f"{mat}.wlscomponent" in args, f"{func} should pass {mat} inline array"


@pytest.mark.parametrize("func", ["DefinePTPMaterial", "DefineBlueWLSMaterial"])
def test_old_p_emission_superseded(construction_cc, func):
    """The old direct WLSCOMPONENT fill is replaced; p_emission is now unused."""
    code = strip_comments(construction_cc)
    m = re.search(rf"MyLightTrapConstruction::{func}\s*\([^)]*\)\s*\{{(.*?)\n\}}", code, re.DOTALL)
    assert m, f"{func} not found"
    body = m.group(1)
    assert "(void)p_emission" in body, f"{func} should mark p_emission superseded"
    assert not re.search(r'AddProperty\("WLSCOMPONENT",\s*energy,\s*p_emission', body), (
        f"{func} must not still fill WLSCOMPONENT directly from p_emission"
    )
