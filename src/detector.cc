#include "detector.hh"
#include "counters.hh"


// ---------------------------------------------------------------------------
MyLeakDetector::MyLeakDetector(G4String name, G4int ntupleID, G4bool killTrack)
  : G4VSensitiveDetector(name), fNtupleID(ntupleID), fKillTrack(killTrack)
{}

MyLeakDetector::~MyLeakDetector()
{}

G4bool MyLeakDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *)
{
  G4Track *track = aStep->GetTrack();
  // Terminal counters kill the photon; pass-through counters let it continue
  // downstream (so the first-layer exit counter does not absorb the light).
  if (fKillTrack)
    track->SetTrackStatus(fStopAndKill);

  G4StepPoint *preStepPoint = aStep->GetPreStepPoint();
  G4ThreeVector pos  = preStepPoint->GetPosition();
  G4double      time = preStepPoint->GetGlobalTime();
  G4ThreeVector mom  = preStepPoint->GetMomentum();
  G4double      wl   = (1.239841939*eV / mom.mag()) * 1E+03;
  // Direction cosine along +z: >0 = travelling forward (into the gap / toward the
  // blue slab), <0 = back-reflected.  Lets analysis separate the two.
  G4double      cosTheta = mom.unit().z();
  // Explicit forward flag for trivial, self-documenting selection in analysis:
  // 1 = forward (out of layer 1, mom.z()>0), 0 = backward (reflected back toward the source).
  // Both directions are recorded — this only tags them.
  G4int         forward  = (mom.z() > 0.) ? 1 : 0;

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->FillNtupleIColumn(fNtupleID, 0, evt);
  man->FillNtupleDColumn(fNtupleID, 1, pos.x());
  man->FillNtupleDColumn(fNtupleID, 2, pos.y());
  man->FillNtupleDColumn(fNtupleID, 3, pos.z());
  man->FillNtupleDColumn(fNtupleID, 4, time);
  man->FillNtupleDColumn(fNtupleID, 5, wl);
  man->FillNtupleDColumn(fNtupleID, 6, cosTheta);
  man->FillNtupleIColumn(fNtupleID, 7, forward);
  man->AddNtupleRow(fNtupleID);

  if (fNtupleID == 4) { if (forward) ++RunCounters::Instance().nLayer1Forward; }
  else if (fNtupleID == 5) ++RunCounters::Instance().nLayer1Edges;

  return true;
}

// ---------------------------------------------------------------------------
MyPMTDetector::MyPMTDetector(G4String name, G4double qe, G4double wlMin_nm, G4double wlMax_nm)
  : G4VSensitiveDetector(name), fQE(qe), fWlMin(wlMin_nm), fWlMax(wlMax_nm)
{
  G4cout << "[MyPMTDetector] " << name << ": QE = " << fQE
         << " for " << fWlMin << " <= wl <= " << fWlMax << " nm (0 outside)" << G4endl;
}

MyPMTDetector::~MyPMTDetector()
{}

G4double MyPMTDetector::Efficiency(G4double wl_nm) const
{
  if (wl_nm < fWlMin || wl_nm > fWlMax) return 0.;
  return fQE;
}

G4bool MyPMTDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *)
{
  G4Track *track = aStep->GetTrack();
  track->SetTrackStatus(fStopAndKill);   // photocathode is opaque: terminal counter

  G4StepPoint *preStepPoint = aStep->GetPreStepPoint();   // entry into the photocathode
  G4ThreeVector pos  = preStepPoint->GetPosition();
  G4double      time = preStepPoint->GetGlobalTime();
  G4ThreeVector mom  = preStepPoint->GetMomentum();
  G4double      wl   = (1.239841939*eV / mom.mag()) * 1E+03;   // nm
  G4double      cosTheta = mom.unit().z();                      // +1 = normal incidence from the front
  G4int         primary  = (track->GetParentID() == 0) ? 1 : 0; // 1 = unshifted beam photon, 0 = WLS daughter

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  // Ntuple 6: every photon reaching the photocathode (pre-QE)
  man->FillNtupleIColumn(6, 0, evt);
  man->FillNtupleDColumn(6, 1, pos.x());
  man->FillNtupleDColumn(6, 2, pos.y());
  man->FillNtupleDColumn(6, 3, pos.z());
  man->FillNtupleDColumn(6, 4, time);
  man->FillNtupleDColumn(6, 5, wl);
  man->FillNtupleDColumn(6, 6, cosTheta);
  man->FillNtupleIColumn(6, 7, primary);
  man->AddNtupleRow(6);
  ++RunCounters::Instance().nPMTPhotons;
  if (primary) ++RunCounters::Instance().nPMTDirect;

  // Ntuple 7: detected photo-electrons (post-QE)
  if (G4UniformRand() < Efficiency(wl)) {
    man->FillNtupleIColumn(7, 0, evt);
    man->FillNtupleDColumn(7, 1, pos.x());
    man->FillNtupleDColumn(7, 2, pos.y());
    man->FillNtupleDColumn(7, 3, pos.z());
    man->FillNtupleDColumn(7, 4, time);
    man->FillNtupleDColumn(7, 5, wl);
    man->FillNtupleDColumn(7, 6, cosTheta);
    man->FillNtupleIColumn(7, 7, primary);
    man->AddNtupleRow(7);
    ++RunCounters::Instance().nPMTHits;
  }

  return true;
}
