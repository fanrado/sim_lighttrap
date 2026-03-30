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
// Records every photon that enters, then kills the track.
class MyLeakDetector : public G4VSensitiveDetector
{
public:
  MyLeakDetector(G4String name, G4int ntupleID);
  ~MyLeakDetector();

private:
  virtual G4bool ProcessHits(G4Step *, G4TouchableHistory *);

  G4int fNtupleID;
};

#endif
