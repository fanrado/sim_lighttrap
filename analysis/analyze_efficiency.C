// analyze_efficiency.C -- ROOT macro companion to analyze_efficiency.py
//
// Reads a LightTrap output ROOT file and reports the WLS / SiPM-collection
// efficiencies of the two-layer light trap, then writes a few diagnostic
// histograms (wavelength spectra, SiPM hit map) to a PDF.
//
// Trees in the file (see src/run.cc, include/namemap.hh):
//   Primary      : one row per primary photon                  -> N_primary
//   WLSPhoton    : one row per OpWLS/Scint photon; matName code
//                  identifies the emitting material (pTP=1, bluewls=3)
//   SiPMPhotons  : one row per photon reaching a SiPM (pre-PDE)
//   SiPMHits     : subset of SiPMPhotons passing the PDE roll (post-PDE)
//
// Usage (with the project's ROOT environment sourced):
//   root -l 'analysis/analyze_efficiency.C("build/output_apexltsim0.root")'
//   root -l analysis/analyze_efficiency.C        // uses the default file below

#include <algorithm>
#include <cmath>
#include <cstdio>

#include "TCanvas.h"
#include "TFile.h"
#include "TH1D.h"
#include "TH2D.h"
#include "TLegend.h"
#include "TStyle.h"
#include "TTree.h"

// NameMap codes (include/namemap.hh)
namespace {
constexpr int kMatPTP     = 1;  // first-layer pTP film
constexpr int kMatBlueWLS = 3;  // second-layer blue-WLS acrylic slab

const char* kDefaultFile = "build/out_vikuiti.root";

// Binomial ratio p = k/n with a symmetric 1-sigma error (sqrt(p(1-p)/n)).
// k may exceed n for non-binomial ratios (e.g. blue/pTP); the error is then
// only indicative, flagged by the >100% value itself.
struct Ratio {
  double p, err;
};
Ratio wilson(double k, double n) {
  if (n == 0) return {NAN, NAN};
  const double p   = k / n;
  const double var = std::max(p * (1.0 - p), 0.0) / n;
  return {p, std::sqrt(var)};
}

// Fetch a tree or abort with a clear message.
TTree* get_tree(TFile* f, const char* name) {
  TTree* t = dynamic_cast<TTree*>(f->Get(name));
  if (!t) {
    ::Error("analyze_efficiency", "tree '%s' not found in file", name);
  }
  return t;
}

void print_pct(const char* label, const Ratio& r) {
  if (std::isnan(r.p))
    printf("%s     n/a\n", label);
  else
    printf("%s%7.3f%% +/- %.3f%%\n", label, 100.0 * r.p, 100.0 * r.err);
}
}  // namespace

void analyze_efficiency(const char* fname = kDefaultFile) {
  TFile* f = TFile::Open(fname, "READ");
  if (!f || f->IsZombie()) {
    ::Error("analyze_efficiency", "could not open ROOT file: %s", fname);
    return;
  }

  TTree* primary = get_tree(f, "Primary");
  TTree* wls     = get_tree(f, "WLSPhoton");
  TTree* photons = get_tree(f, "SiPMPhotons");
  TTree* hits    = get_tree(f, "SiPMHits");
  if (!primary || !wls || !photons || !hits) {
    f->Close();
    return;
  }
  // Optional: back-face leak counter (ntuple 6). forward==1 means mom.z()>0
  // (photon exits layer 1 toward the blue slab); forward==0 is backward-going
  // (e.g. reflected off the Vikuiti backplane). See src/detector.cc.
  TTree* backplane = get_tree(f, "FirstLayerBackplane");

  // --- raw counts ---------------------------------------------------------
  const Long64_t n_primary  = primary->GetEntries();
  const Long64_t n_wls_total = wls->GetEntries();
  const Long64_t n_ptp      = wls->GetEntries(Form("matName==%d", kMatPTP));
  const Long64_t n_bluewls  = wls->GetEntries(Form("matName==%d", kMatBlueWLS));
  const Long64_t n_wls_other = n_wls_total - n_ptp - n_bluewls;
  const Long64_t n_at_sipm  = photons->GetEntries();
  const Long64_t n_detected = hits->GetEntries();

  if (n_primary == 0) {
    ::Error("analyze_efficiency", "Primary tree is empty; nothing to normalize to.");
    f->Close();
    return;
  }

  // --- efficiencies -------------------------------------------------------
  const Ratio eps_wls1    = wilson(n_ptp, n_primary);
  const Ratio eps_wls2    = wilson(n_bluewls, n_ptp);      // 2nd-stage conversion
  const Ratio eps_collect = wilson(n_at_sipm, n_bluewls);  // transport to SiPM
  const Ratio eps_detect  = wilson(n_detected, n_bluewls); // after PDE
  const Ratio avg_pde     = wilson(n_detected, n_at_sipm);
  const Ratio eps_system  = wilson(n_detected, n_primary); // full chain

  const char* line = "--------------------------------------------------------------------";
  printf("%s\n", line);
  printf("LightTrap efficiency analysis\n");
  printf("  file: %s\n", fname);
  printf("%s\n", line);
  printf("Raw counts\n");
  printf("  primary photons            N_primary  = %12lld\n", n_primary);
  printf("  WLS photons (total)        N_wls      = %12lld\n", n_wls_total);
  printf("    in pTP        (matName=%d)            = %12lld\n", kMatPTP, n_ptp);
  printf("    in blue-WLS   (matName=%d)            = %12lld\n", kMatBlueWLS, n_bluewls);
  if (n_wls_other)
    printf("    other material                       = %12lld  (%.2e of total)\n",
           n_wls_other, double(n_wls_other) / std::max<Long64_t>(n_wls_total, 1));
  printf("  photons reaching SiPM      N_at_sipm  = %12lld\n", n_at_sipm);
  printf("  detected (after PDE)       N_hits     = %12lld\n", n_detected);
  printf("%s\n", line);
  printf("1. First layer -- pTP wavelength-shifting efficiency\n");
  print_pct("     eps_WLS1 = N_pTP / N_primary        = ", eps_wls1);
  printf("%s\n", line);
  printf("2. Second layer -- blue-WLS + SiPM collection\n");
  print_pct("     2nd-stage conversion  N_blue/N_pTP  = ", eps_wls2);
  print_pct("     collection  N_at_sipm / N_blue      = ", eps_collect);
  print_pct("     detection   N_hits    / N_blue      = ", eps_detect);
  print_pct("     average PDE N_hits    / N_at_sipm   = ", avg_pde);
  printf("%s\n", line);
  printf("Overall chain\n");
  print_pct("     photoelectrons per primary  N_hits/N_primary = ", eps_system);
  printf("%s\n", line);

  // --- first-layer backplane forward/backward split -----------------------
  Long64_t n_bp_total = 0, n_bp_fwd = 0, n_bp_bwd = 0;
  if (backplane) {
    n_bp_total = backplane->GetEntries();
    n_bp_fwd   = backplane->GetEntries("forward==1");
    n_bp_bwd   = backplane->GetEntries("forward==0");
    const Ratio frac_fwd = wilson(n_bp_fwd, n_bp_total);
    const Ratio frac_bwd = wilson(n_bp_bwd, n_bp_total);
    printf("First-layer backplane (photons crossing the back face)\n");
    printf("  crossings (total)          N_bp       = %12lld\n", n_bp_total);
    printf("    forward  (mom.z>0)                   = %12lld\n", n_bp_fwd);
    printf("    backward (mom.z<0)                   = %12lld\n", n_bp_bwd);
    print_pct("    forward  fraction  N_fwd / N_bp    = ", frac_fwd);
    print_pct("    backward fraction  N_bwd / N_bp    = ", frac_bwd);
    printf("%s\n", line);
  } else {
    ::Warning("analyze_efficiency",
              "FirstLayerBackplane tree not found; skipping backplane plots.");
  }

  // --- diagnostic plots ---------------------------------------------------
  gStyle->SetOptStat(0);
  TCanvas* c = new TCanvas("c_eff", "LightTrap diagnostics", 1200, 800);
  c->Divide(2, 2);

  c->cd(1);
  primary->Draw("wl>>h_prim(100)", "", "");
  if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_prim"))) {
    h->SetTitle("Primary photon wavelength;#lambda [nm];photons");
  }

  c->cd(2);
  wls->Draw("wl>>h_ptp(100)", Form("matName==%d", kMatPTP), "");
  if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_ptp"))) {
    h->SetTitle("pTP re-emission wavelength;#lambda [nm];photons");
  }

  c->cd(3);
  photons->Draw("fwl>>h_sipm(100)", "", "");
  if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_sipm"))) {
    h->SetTitle("Wavelength arriving at SiPM;#lambda [nm];photons");
  }

  c->cd(4);
  hits->Draw("fY:fX>>h_map(200,0,0,200,0,0)", "", "colz");
  if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_map"))) {
    h->SetTitle("SiPM hit map (post-PDE);x [mm];y [mm]");
  }

  const char* out_pdf = "analyze_efficiency.pdf";

  // --- first-layer backplane: forward vs backward plots -------------------
  TCanvas* c2 = nullptr;
  if (backplane) {
    c2 = new TCanvas("c_bp", "First-layer backplane forward/backward", 1200, 800);
    c2->Divide(2, 2);

    // Wavelength, forward vs backward overlaid (fixed range so 'same' aligns).
    c2->cd(1);
    backplane->Draw("fwl>>h_bp_wl_f(120,0,600)", "forward==1", "goff");
    backplane->Draw("fwl>>h_bp_wl_b(120,0,600)", "forward==0", "goff");
    TH1* hwf = dynamic_cast<TH1*>(gDirectory->Get("h_bp_wl_f"));
    TH1* hwb = dynamic_cast<TH1*>(gDirectory->Get("h_bp_wl_b"));
    if (hwf && hwb) {
      hwf->SetLineColor(kRed);
      hwb->SetLineColor(kBlue);
      hwf->SetTitle("Backplane wavelength;#lambda [nm];photons");
      hwf->SetMaximum(1.10 * std::max(hwf->GetMaximum(), hwb->GetMaximum()));
      hwf->Draw("HIST");
      hwb->Draw("HIST SAME");
      TLegend* leg = new TLegend(0.62, 0.75, 0.88, 0.88);
      leg->AddEntry(hwf, "forward (mom.z>0)", "l");
      leg->AddEntry(hwb, "backward (mom.z<0)", "l");
      leg->Draw();
    }

    // Direction cosine along +z; the forward/backward split is the sign of it.
    c2->cd(2);
    backplane->Draw("fcosTheta>>h_bp_ct_f(100,-1,1)", "forward==1", "goff");
    backplane->Draw("fcosTheta>>h_bp_ct_b(100,-1,1)", "forward==0", "goff");
    TH1* hcf = dynamic_cast<TH1*>(gDirectory->Get("h_bp_ct_f"));
    TH1* hcb = dynamic_cast<TH1*>(gDirectory->Get("h_bp_ct_b"));
    if (hcf && hcb) {
      hcf->SetLineColor(kRed);
      hcb->SetLineColor(kBlue);
      hcf->SetTitle("Backplane direction cosine;cos#theta_{z};photons");
      hcf->SetMaximum(1.10 * std::max(hcf->GetMaximum(), hcb->GetMaximum()));
      hcf->Draw("HIST");
      hcb->Draw("HIST SAME");
    }

    // Impact position of forward- and backward-going photons on the back face.
    c2->cd(3);
    backplane->Draw("fY:fX>>h_bp_xy_f(200,0,0,200,0,0)", "forward==1", "colz");
    if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_bp_xy_f")))
      h->SetTitle("Backplane hit map -- forward;x [mm];y [mm]");

    c2->cd(4);
    backplane->Draw("fY:fX>>h_bp_xy_b(200,0,0,200,0,0)", "forward==0", "colz");
    if (TH1* h = dynamic_cast<TH1*>(gDirectory->Get("h_bp_xy_b")))
      h->SetTitle("Backplane hit map -- backward;x [mm];y [mm]");
  }

  // Write a multi-page PDF (page 1: efficiency; page 2: backplane) when the
  // backplane tree is present, otherwise a single page.
  if (c2) {
    c->Print(Form("%s(", out_pdf), "pdf");
    c2->Print(Form("%s)", out_pdf), "pdf");
  } else {
    c->SaveAs(out_pdf);
  }
  printf("wrote diagnostic plots -> %s\n", out_pdf);

  f->Close();
}
