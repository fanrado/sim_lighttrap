"""
Tests for the analysis/Analyze_out.C ROOT macro.

Feature (commit 389e967):
  A ROOT macro that reads the analysis trees from a simulation output file
  (structure of build/out_none.root) and writes a single multi-page PDF, one
  page per tree. Counter trees carrying a "forward" flag are overlaid
  forward-vs-backward; Primary and the SiPM trees are drawn as single
  distributions.

Two layers of checks:
  1. Static consistency — every tree name and every branch the macro reads must
     actually exist in the simulation's ntuple definitions (src/run.cc). This
     catches silent drift (a renamed branch → empty plots) without needing ROOT.
  2. Runtime — if `root` is available, build a tiny synthetic file mirroring the
     data model, run the macro on it, and assert it produces the PDF and plots
     every expected tree without error.
"""

import os
import re
import shutil
import subprocess

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO = os.path.join(REPO, "analysis", "Analyze_out.C")
RUN_CC = os.path.join(REPO, "src", "run.cc")


def read(path):
    with open(path) as fh:
        return fh.read()


# ── parse the simulation's ntuple definitions from run.cc ────────────────────

def parse_run_cc_ntuples(src):
    """Return {treeName: set(branchNames)} from run.cc CreateNtuple* calls."""
    trees = {}
    current = None
    col_re = re.compile(r'CreateNtuple[IDFS]Column\s*\(\s*"([^"]+)"')
    new_re = re.compile(r'CreateNtuple\s*\(\s*"([^"]+)"')
    for line in src.splitlines():
        mnew = new_re.search(line)
        if mnew and "Column" not in line:
            current = mnew.group(1)
            trees[current] = set()
            continue
        mcol = col_re.search(line)
        if mcol and current is not None:
            trees[current].add(mcol.group(1))
        if "FinishNtuple" in line:
            current = None
    return trees


# ── parse the macro's TreeSpec {name, vars} entries ──────────────────────────

def parse_macro_treespecs(src):
    """Return list of (treeName, [vars]) from the macro's TreeSpec initializers."""
    specs = []
    # Match: {"TreeName",\n   {"a", "b", ...}}
    for m in re.finditer(
        r'\{\s*"([A-Za-z0-9_]+)"\s*,\s*\{([^}]*)\}\s*\}', src
    ):
        name = m.group(1)
        varblob = m.group(2)
        vars_ = re.findall(r'"([^"]+)"', varblob)
        specs.append((name, vars_))
    return specs


@pytest.fixture(scope="module")
def macro_src():
    return read(MACRO)


@pytest.fixture(scope="module")
def run_trees():
    return parse_run_cc_ntuples(read(RUN_CC))


@pytest.fixture(scope="module")
def macro_specs(macro_src):
    return parse_macro_treespecs(macro_src)


# ── 1. static consistency ────────────────────────────────────────────────────

def test_macro_defines_treespecs(macro_specs):
    names = {n for n, _ in macro_specs}
    # The six trees the macro is documented to plot.
    expected = {"Primary", "FirstLayerBackplane", "FirstLayerEdges",
                "SecondLayerBackplane", "SiPMPhotons", "SiPMHits"}
    assert expected <= names, f"macro should plot {expected}, found {names}"


def test_macro_trees_exist_in_run_cc(macro_specs, run_trees):
    for name, _ in macro_specs:
        assert name in run_trees, (
            f"macro reads tree '{name}' but run.cc defines no such ntuple "
            f"(defined: {sorted(run_trees)})"
        )


def test_macro_branches_exist_in_run_cc(macro_specs, run_trees):
    """Every variable the macro projects must be a real branch of that tree."""
    for name, vars_ in macro_specs:
        actual = run_trees.get(name, set())
        for v in vars_:
            assert v in actual, (
                f"macro projects '{v}' from tree '{name}', but run.cc's "
                f"'{name}' has no such branch (branches: {sorted(actual)})"
            )


def test_forward_flag_trees_have_forward_branch(macro_specs, run_trees):
    """Trees the macro overlays forward/backward must actually carry 'forward'."""
    fwd_trees = {"FirstLayerBackplane", "FirstLayerEdges", "SecondLayerBackplane"}
    for name in fwd_trees:
        assert "forward" in run_trees.get(name, set()), (
            f"'{name}' should have a 'forward' branch for fwd/bwd overlay"
        )


def test_single_distribution_trees_have_no_forward(run_trees):
    """Primary and SiPM trees are drawn as single distributions (no forward flag)."""
    for name in ("Primary", "SiPMPhotons", "SiPMHits"):
        assert "forward" not in run_trees.get(name, set()), (
            f"'{name}' unexpectedly has a 'forward' branch; macro treats it as "
            "a single distribution"
        )


def test_macro_uses_forward_branch_detection(macro_src):
    """The macro must branch on the presence of a 'forward' branch at run time."""
    assert 'GetBranch("forward")' in macro_src, (
        "macro should detect the forward flag via GetBranch(\"forward\")"
    )
    assert 'forward==1' in macro_src and 'forward==0' in macro_src, (
        "macro should project forward==1 / forward==0 for the overlay"
    )


def test_macro_default_input_and_pdf_naming(macro_src):
    """Default input is an out_*.root file; PDF name is derived from the base name."""
    assert re.search(r'Analyze_out\s*\(\s*const char\*\s*filename\s*=\s*"[^"]*\.root"',
                     macro_src), "Analyze_out should default filename to a .root file"
    assert '"_analysis.pdf"' in macro_src or '_analysis.pdf' in macro_src, (
        "macro should build an <base>_analysis.pdf output name"
    )


# ── 2. runtime: build synthetic file, run the macro ──────────────────────────

SYNTH_C = r'''
#include "TFile.h"
#include "TTree.h"
#include "TRandom3.h"
void make_synth(const char* out) {
  TFile* f = TFile::Open(out, "RECREATE");
  TRandom3 rng(1234);
  { TTree* t = new TTree("Primary","Primary");
    double posX,posY,posZ,momX,momY,momZ,wl; int pdg,eventID;
    t->Branch("eventID",&eventID);t->Branch("posX",&posX);t->Branch("posY",&posY);
    t->Branch("posZ",&posZ);t->Branch("momX",&momX);t->Branch("momY",&momY);
    t->Branch("momZ",&momZ);t->Branch("wl",&wl);t->Branch("pdg",&pdg);
    for(int i=0;i<200;++i){eventID=i;posX=rng.Gaus();posY=rng.Gaus();posZ=rng.Gaus();
      momX=rng.Gaus();momY=rng.Gaus();momZ=rng.Gaus();wl=128+rng.Gaus()*5;pdg=22;t->Fill();}
    t->Write(); }
  const char* cs[3]={"FirstLayerBackplane","FirstLayerEdges","SecondLayerBackplane"};
  for(int k=0;k<3;++k){ TTree* t=new TTree(cs[k],cs[k]);
    double fX,fY,fZ,fT,fwl,fcosTheta; int forward,eventID;
    t->Branch("eventID",&eventID);t->Branch("fX",&fX);t->Branch("fY",&fY);
    t->Branch("fZ",&fZ);t->Branch("fT",&fT);t->Branch("fwl",&fwl);
    t->Branch("fcosTheta",&fcosTheta);t->Branch("forward",&forward);
    for(int i=0;i<200;++i){eventID=i;fX=rng.Gaus();fY=rng.Gaus();fZ=rng.Gaus();
      fT=rng.Uniform(0,10);fwl=430+rng.Gaus()*10;fcosTheta=rng.Uniform(-1,1);
      forward=(fcosTheta>0)?1:0;t->Fill();}
    t->Write(); }
  { TTree* t=new TTree("SiPMPhotons","SiPMPhotons");
    double fX,fY,fZ,fT,fwl; int eventID;
    t->Branch("eventID",&eventID);t->Branch("fX",&fX);t->Branch("fY",&fY);
    t->Branch("fZ",&fZ);t->Branch("fT",&fT);t->Branch("fwl",&fwl);
    for(int i=0;i<150;++i){eventID=i;fX=rng.Gaus();fY=rng.Gaus();fZ=rng.Gaus();
      fT=rng.Uniform(0,10);fwl=430+rng.Gaus()*10;t->Fill();}
    t->Write(); }
  { TTree* t=new TTree("SiPMHits","SiPMHits");
    double fX,fY,fZ; int eventID;
    t->Branch("eventID",&eventID);t->Branch("fX",&fX);t->Branch("fY",&fY);t->Branch("fZ",&fZ);
    for(int i=0;i<90;++i){eventID=i;fX=rng.Gaus();fY=rng.Gaus();fZ=rng.Gaus();t->Fill();}
    t->Write(); }
  f->Close();
}
'''


@pytest.mark.skipif(shutil.which("root") is None, reason="ROOT not available")
def test_macro_runs_and_produces_pdf(tmp_path):
    synth_c = tmp_path / "make_synth.C"
    synth_c.write_text(SYNTH_C)
    synth_root = tmp_path / "synth.root"

    gen = subprocess.run(
        ["root", "-l", "-b", "-q",
         f'{synth_c}("{synth_root}")'],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
    )
    assert synth_root.exists(), f"failed to build synthetic file:\n{gen.stderr}"

    # Run the macro from tmp_path so the derived PDF lands there, not in the repo.
    proc = subprocess.run(
        ["root", "-l", "-b", "-q", f'{MACRO}("{synth_root}")'],
        cwd=tmp_path, capture_output=True, text=True, timeout=180,
    )
    out = proc.stdout + proc.stderr

    assert proc.returncode == 0, f"macro exited {proc.returncode}\n{out}"
    assert "could not open input file" not in out, out

    # PDF produced.
    pdf = tmp_path / "synth_analysis.pdf"
    assert pdf.exists() and pdf.stat().st_size > 0, f"no output PDF produced\n{out}"
    assert "Wrote" in out, f"macro did not report writing the PDF\n{out}"

    # Every expected tree was plotted, none reported missing.
    for name in ("Primary", "FirstLayerBackplane", "FirstLayerEdges",
                 "SecondLayerBackplane", "SiPMPhotons", "SiPMHits"):
        assert f"Plotting tree '{name}'" in out, (
            f"macro did not plot tree '{name}'\n{out}"
        )
        assert f"tree '{name}' not found" not in out, (
            f"macro reported '{name}' missing on a file that contains it\n{out}"
        )


@pytest.mark.skipif(shutil.which("root") is None, reason="ROOT not available")
def test_macro_handles_missing_file_gracefully(tmp_path):
    """A non-existent input must be reported, not crash the interpreter."""
    proc = subprocess.run(
        ["root", "-l", "-b", "-q", f'{MACRO}("{tmp_path}/nope.root")'],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
    )
    out = proc.stdout + proc.stderr
    assert "could not open input file" in out, (
        f"macro should report a missing input file, got:\n{out}"
    )
    assert not (tmp_path / "nope_analysis.pdf").exists(), (
        "no PDF should be produced for a missing input"
    )
