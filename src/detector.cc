#include "detector.hh"

MySensitiveDetector::MySensitiveDetector(G4String name) : G4VSensitiveDetector(name)
{
  QE = new G4PhysicsFreeVector();

  // Broadcom SiPM PDE table "<wavelength_nm> <pde>", read from the working
  // directory (CMake copies input/pde_broadcom.dat into the build directory).
  std::ifstream datafile("pde_broadcom.dat");
  if (!datafile) {
    // Must not hang (the old while(1)/eof() loop spun forever on a missing
    // file): warn loudly and leave the table empty, i.e. PDE = 0 everywhere.
    G4Exception("MySensitiveDetector::MySensitiveDetector", "SiPMPDEFile",
                JustWarning,
                "pde_broadcom.dat not found in the working directory; "
                "SiPM PDE table is empty (PDE = 0).");
    return;
  }

  G4double wl, pde;
  while (datafile >> wl >> pde) {
    G4cout << wl << " " << pde << G4endl;
    QE->InsertValues(wl, pde);
  }
  datafile.close();

  //QE->SetSpline(false); //linear interpolation b/t data points
}

MySensitiveDetector::~MySensitiveDetector()
{}

G4bool MySensitiveDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *ROhist)
{
  G4Track *track = aStep->GetTrack();
  track->SetTrackStatus(fStopAndKill); // kill track once photon reaches sipm

  G4StepPoint *preStepPoint = aStep->GetPreStepPoint(); // photon enters photosensor
  G4StepPoint *postStepPoint = aStep->GetPostStepPoint();

  G4ThreeVector posPhoton = preStepPoint->GetPosition();
  G4double time = preStepPoint->GetGlobalTime();
  G4ThreeVector polarizationPhoton = preStepPoint->GetPolarization();

  G4ThreeVector momPhoton = preStepPoint->GetMomentum();
  G4double wl = (1.239841939*eV/momPhoton.mag())*1E+03;
  // G4cout << "Photon wl: " << wl << ", polarization: "<< polarizationPhoton << G4endl;

  //G4cout << "Photon pos: " << posPhoton << G4endl;

  const G4VTouchable *touchable = aStep->GetPreStepPoint()->GetTouchable();

  G4int copyNo = touchable->GetCopyNumber(); // photon hit which sipm
  G4cout << "copyNo: " << copyNo << G4endl;

  G4VPhysicalVolume *physVol = touchable->GetVolume();
  G4ThreeVector posDetector = physVol->GetTranslation();
  G4cout << "posDetector: " << posDetector << G4endl;

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();

  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->FillNtupleIColumn(0, 0, evt);
  man->FillNtupleDColumn(0, 1, posPhoton[0]);
  man->FillNtupleDColumn(0, 2, posPhoton[1]);
  man->FillNtupleDColumn(0, 3, posPhoton[2]);
  man->FillNtupleDColumn(0, 4, time);
  man->FillNtupleDColumn(0, 5, wl);
  man->AddNtupleRow(0);

  // apply quantum efficiency (empty table, e.g. missing PDE file, means PDE = 0)
  const G4double pde = (QE->GetVectorLength() > 0) ? QE->Value(wl) : 0.;
  if( G4UniformRand() < pde ){
    man->FillNtupleIColumn(1, 0, evt);
    man->FillNtupleDColumn(1, 1, posDetector[0]);
    man->FillNtupleDColumn(1, 2, posDetector[1]);
    man->FillNtupleDColumn(1, 3, posDetector[2]);
    man->AddNtupleRow(1);
  }

  return true;
}

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
  // 1 = forward (out of layer 1, mom.z()>0), 0 = backward (e.g. Vikuiti-reflected).
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

  // Ntuple 9: every photon reaching the photocathode (pre-QE)
  man->FillNtupleIColumn(9, 0, evt);
  man->FillNtupleDColumn(9, 1, pos.x());
  man->FillNtupleDColumn(9, 2, pos.y());
  man->FillNtupleDColumn(9, 3, pos.z());
  man->FillNtupleDColumn(9, 4, time);
  man->FillNtupleDColumn(9, 5, wl);
  man->FillNtupleDColumn(9, 6, cosTheta);
  man->FillNtupleIColumn(9, 7, primary);
  man->AddNtupleRow(9);

  // Ntuple 10: detected photo-electrons (post-QE)
  if (G4UniformRand() < Efficiency(wl)) {
    man->FillNtupleIColumn(10, 0, evt);
    man->FillNtupleDColumn(10, 1, pos.x());
    man->FillNtupleDColumn(10, 2, pos.y());
    man->FillNtupleDColumn(10, 3, pos.z());
    man->FillNtupleDColumn(10, 4, time);
    man->FillNtupleDColumn(10, 5, wl);
    man->FillNtupleDColumn(10, 6, cosTheta);
    man->FillNtupleIColumn(10, 7, primary);
    man->AddNtupleRow(10);
  }

  return true;
}
