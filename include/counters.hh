#ifndef COUNTERS_HH
#define COUNTERS_HH

#include "G4Types.hh"

// Per-run photon bookkeeping, printed by MyRunAction::EndOfRunAction so the
// physics of a run can be checked in the terminal / Qt output pane without
// opening the ROOT file or trusting the viewer (sequential run manager only).
struct RunCounters
{
  G4long nPrimary        = 0;   // beam photons (events)
  G4long nWLSpTP         = 0;   // WLS photons born in the pTP film
  G4long nWLSother       = 0;   // WLS / scintillation photons born elsewhere
  G4long nLayer1Forward  = 0;   // photons leaving the first layer toward the PMT
  G4long nLayer1Edges    = 0;   // photons reaching the first-layer ±x edges
  G4long nPMTPhotons     = 0;   // photons reaching the photocathode (pre-QE)
  G4long nPMTDirect      = 0;   // ... of which unshifted beam photons
  G4long nPMTHits        = 0;   // detected photo-electrons (post-QE)

  void Reset() { *this = RunCounters(); }

  static RunCounters& Instance() { static RunCounters c; return c; }
};

#endif
