#ifndef DETECTOR_HH
#define DETECTOR_HH

#include "G4VSensitiveDetector.hh"

#include "G4RunManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4AnalysisManager.hh"

class MySensitiveDetector : public G4VSensitiveDetector
{
public:
  MySensitiveDetector(G4String);
  ~MySensitiveDetector();

private:
  virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

  G4PhysicsFreeVector *QE;
};

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

// PMT photocathode (detectorType = "pmt").  Terminal: every photon reaching the
// photocathode is killed (the cathode is opaque).  Every arrival is recorded to
// ntuple 9 (PMTPhotons, pre-QE); a photon is additionally recorded to ntuple 10
// (PMTHits, post-QE) with probability `qe` if its wavelength lies inside
// [wlMin_nm, wlMax_nm], and never outside that band.  Default: flat 100 % QE
// over 110-500 nm (the "ideal VUV PMT" starting assumption).
class MyPMTDetector : public G4VSensitiveDetector
{
public:
  MyPMTDetector(G4String name, G4double qe, G4double wlMin_nm, G4double wlMax_nm);
  ~MyPMTDetector();

  // Efficiency at a given wavelength [nm]: qe inside the band, 0 outside.
  G4double Efficiency(G4double wl_nm) const;

private:
  virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

  G4double fQE;
  G4double fWlMin;   // nm
  G4double fWlMax;   // nm
};

#endif
