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

#endif
