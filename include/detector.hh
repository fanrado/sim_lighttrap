#ifndef DETECTOR_HH
#define DETECTOR_HH

#include "G4VSensitiveDetector.hh"
#include <vector>
#include <string>

#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4AnalysisManager.hh"

// Simple 100%-efficient photon counter for validation volumes.
// Records every photon that enters (eventID, x, y, z, t, wl, cosTheta).
// killTrack=true  → terminal counter (e.g. backplane leak): kills the track.
// killTrack=false → pass-through counter (e.g. first-layer exit): the photon
//                   is recorded but continues on to downstream volumes.
class MyLeakDetector : public G4VSensitiveDetector
{
public:
  MyLeakDetector(G4String name, G4int ntupleID, G4bool killTrack = true);
  ~MyLeakDetector();

private:
  virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

  G4int  fNtupleID;
  G4bool fKillTrack;
};

// PMT photocathode.  Terminal: every photon reaching the
// photocathode is killed (the cathode is opaque).  Every arrival is recorded to
// ntuple 9 (PMTPhotons, pre-QE); a photon is additionally recorded to ntuple 10
// (PMTHits, post-QE) with probability `qe` if its wavelength lies inside
// [wlMin_nm, wlMax_nm], and never outside that band.  Default: flat 100 % QE
// over 110-500 nm (the "ideal VUV PMT" starting assumption).
class MyPMTDetector : public G4VSensitiveDetector
{
public:
  // Flat QE `qe` inside [wlMin_nm, wlMax_nm] (0 outside).  If `qeFile` is not
  // empty, a 2-column "<wavelength_nm> <QE>" table is loaded instead and used
  // with linear interpolation (0 outside the tabulated range; values > 1 are
  // taken as percent).
  MyPMTDetector(G4String name, G4double qe, G4double wlMin_nm, G4double wlMax_nm,
                const G4String& qeFile = "");
  ~MyPMTDetector();

  // Efficiency at a given wavelength [nm].
  G4double Efficiency(G4double wl_nm) const;
  G4bool   HasTable() const { return !fTableWl.empty(); }
  G4String Description() const;   // one-line summary for the run printout

  // Load "<wavelength_nm> <QE>" (comments after '#', blank lines skipped);
  // returns false if the file cannot be read or has < 2 rows.
  static G4bool LoadQETable(const G4String& path, std::vector<double>& wl, std::vector<double>& qe);

private:
  virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

  G4double fQE;
  G4double fWlMin;   // nm
  G4double fWlMax;   // nm
  G4String fQEFile;
  std::vector<double> fTableWl;  // ascending nm
  std::vector<double> fTableQE;  // fraction 0..1
};

#endif
