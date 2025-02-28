#include "detector.hh"

MySensitiveDetector::MySensitiveDetector(G4String name) : G4VSensitiveDetector(name)
{
  QE = new G4PhysicsFreeVector();

  std::ifstream datafile;
  datafile.open("pde_broadcom.dat");

  while(1)
  {
    G4double wl, pde;
    datafile >> wl >> pde;

    if (datafile.eof())
      break;

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
  // G4cout << "copyNo: " << copyNo << G4endl;

  G4VPhysicalVolume *physVol = touchable->GetVolume();
  G4ThreeVector posDetector = physVol->GetTranslation();
  // G4cout << "posDetector: " << posDetector << G4endl;

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();

  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->FillNtupleIColumn(0, 0, evt);
  man->FillNtupleDColumn(0, 1, posPhoton[0]);
  man->FillNtupleDColumn(0, 2, posPhoton[1]);
  man->FillNtupleDColumn(0, 3, posPhoton[2]);
  man->FillNtupleDColumn(0, 4, time);
  man->FillNtupleDColumn(0, 5, wl);
  man->AddNtupleRow(0);

  if( G4UniformRand() < QE->Value(wl) ){ // apply quantum efficiency
    man->FillNtupleIColumn(1, 0, evt);
    man->FillNtupleDColumn(1, 1, posDetector[0]);
    man->FillNtupleDColumn(1, 2, posDetector[1]);
    man->FillNtupleDColumn(1, 3, posDetector[2]);
    man->AddNtupleRow(1);
  }

  return true;
}
