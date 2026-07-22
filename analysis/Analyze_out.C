#include <cmath>
#include <cstdio>
#include <string>
#include <vector>

#include "TBranch.h"
#include "TCanvas.h"
#include "TFile.h"
#include "TH1D.h"
#include "TLegend.h"
#include "TString.h"
#include "TStyle.h"
#include "TTree.h"

// ---------------------------------------------------------------------------
// Analyze_out.C
//
// Reads the analysis trees from a simulation output ROOT file (same structure
// as build/out_none.root) and produces a single multi-page PDF.
//
//   * Primary, FirstLayerBackplane, FirstLayerEdges, SecondLayerBackplane:
//       one page per tree, each observable overlaid as forward vs. backward
//       photons (trees that carry a "forward" flag). Primary has no forward
//       flag, so its observables are drawn as single distributions.
//   * SiPMPhotons and SiPMHits: their observables are drawn on the final pages.
//
// Usage:
//   root -l -b -q 'Analyze_out.C("build/out_none.root")'
// ---------------------------------------------------------------------------

namespace {

// Draw one page holding every variable of a tree, laid out on an automatic grid.
// If the tree has a "forward" branch, each variable is overlaid forward (blue)
// vs. backward (red); otherwise a single distribution is drawn.
void PlotTreePage(TTree* t, const std::vector<std::string>& vars,
                  TCanvas* c, const char* pdf) {
  if (!t) return;

  const bool hasForward = (t->GetBranch("forward") != nullptr);
  const int n = static_cast<int>(vars.size());
  if (n == 0) return;

  const int ncols = static_cast<int>(std::ceil(std::sqrt(static_cast<double>(n))));
  const int nrows = static_cast<int>(std::ceil(static_cast<double>(n) / ncols));

  c->Clear();
  c->Divide(ncols, nrows);

  // Keep drawn objects alive until after Print().
  std::vector<TObject*> keep;

  for (int i = 0; i < n; ++i) {
    c->cd(i + 1);
    const char* v = vars[i].c_str();

    double lo = t->GetMinimum(v);
    double hi = t->GetMaximum(v);
    if (lo >= hi) { lo -= 1.0; hi += 1.0; }
    const double pad = (hi - lo) * 0.02;
    lo -= pad;
    hi += pad;
    const int nb = 100;

    if (hasForward) {
      TH1D* hf = new TH1D(Form("%s_%s_fwd", t->GetName(), v),
                          Form("%s (%s);%s;Counts", v, t->GetName(), v),
                          nb, lo, hi);
      TH1D* hb = new TH1D(Form("%s_%s_bwd", t->GetName(), v), "", nb, lo, hi);

      t->Project(hf->GetName(), v, "forward==1");
      t->Project(hb->GetName(), v, "forward==0");

      hf->SetLineColor(kBlue + 1);
      hf->SetLineWidth(2);
      hb->SetLineColor(kRed + 1);
      hb->SetLineWidth(2);

      const double ymax = std::max(hf->GetMaximum(), hb->GetMaximum());
      hf->SetMaximum(ymax * 1.15 + 1.0);
      hf->SetMinimum(0.0);

      hf->Draw("HIST");
      hb->Draw("HIST SAME");

      TLegend* leg = new TLegend(0.62, 0.75, 0.88, 0.88);
      leg->SetBorderSize(0);
      leg->SetFillStyle(0);
      leg->AddEntry(hf, Form("Forward (%.0f)", hf->GetEntries()), "l");
      leg->AddEntry(hb, Form("Backward (%.0f)", hb->GetEntries()), "l");
      leg->Draw();

      keep.push_back(hf);
      keep.push_back(hb);
      keep.push_back(leg);
    } else {
      TH1D* h = new TH1D(Form("%s_%s", t->GetName(), v),
                         Form("%s (%s);%s;Counts", v, t->GetName(), v),
                         nb, lo, hi);
      t->Project(h->GetName(), v);
      h->SetLineColor(kAzure + 2);
      h->SetLineWidth(2);
      h->SetMinimum(0.0);
      h->Draw("HIST");
      keep.push_back(h);
    }
  }

  c->Print(pdf);
}

}  // namespace

void Analyze_out(const char* filename = "build/out_none.root") {
  gStyle->SetOptStat(0);
  gStyle->SetTitleSize(0.05, "t");
  gStyle->SetPadLeftMargin(0.13);
  gStyle->SetPadBottomMargin(0.13);

  TFile* f = TFile::Open(filename);
  if (!f || f->IsZombie()) {
    printf("ERROR: could not open input file '%s'\n", filename);
    return;
  }

  // Build the output PDF name from the input file base name.
  TString outpdf(filename);
  Ssiz_t slash = outpdf.Last('/');
  if (slash != kNPOS) outpdf.Remove(0, slash + 1);
  if (outpdf.EndsWith(".root")) outpdf.Remove(outpdf.Length() - 5);
  outpdf += "_analysis.pdf";

  TCanvas* c = new TCanvas("c", "Analyze_out", 1200, 900);

  // Open the multi-page PDF.
  c->Print(outpdf + "[");

  // ---- Trees with forward/backward separation (plus Primary) -------------
  struct TreeSpec {
    const char* name;
    std::vector<std::string> vars;
  };

  std::vector<TreeSpec> counterTrees = {
    {"Primary",
       {"posX", "posY", "posZ", "momX", "momY", "momZ", "wl", "pdg"}},
    {"FirstLayerBackplane",
       {"fX", "fY", "fZ", "fT", "fwl", "fcosTheta"}},
    {"FirstLayerEdges",
       {"fX", "fY", "fZ", "fT", "fwl", "fcosTheta"}},
    {"SecondLayerBackplane",
       {"fX", "fY", "fZ", "fT", "fwl", "fcosTheta"}},
  };

  for (const auto& spec : counterTrees) {
    TTree* t = dynamic_cast<TTree*>(f->Get(spec.name));
    if (!t) {
      printf("WARNING: tree '%s' not found, skipping.\n", spec.name);
      continue;
    }
    printf("Plotting tree '%s' (%lld entries)\n", spec.name, t->GetEntries());
    PlotTreePage(t, spec.vars, c, outpdf);
  }

  // ---- SiPM trees on the final pages -------------------------------------
  std::vector<TreeSpec> sipmTrees = {
    {"SiPMPhotons", {"fX", "fY", "fZ", "fT", "fwl"}},
    {"SiPMHits",    {"fX", "fY", "fZ"}},
  };

  for (const auto& spec : sipmTrees) {
    TTree* t = dynamic_cast<TTree*>(f->Get(spec.name));
    if (!t) {
      printf("WARNING: tree '%s' not found, skipping.\n", spec.name);
      continue;
    }
    printf("Plotting tree '%s' (%lld entries)\n", spec.name, t->GetEntries());
    PlotTreePage(t, spec.vars, c, outpdf);
  }

  // Close the multi-page PDF.
  c->Print(outpdf + "]");
  printf("Wrote %s\n", outpdf.Data());

  f->Close();
}
