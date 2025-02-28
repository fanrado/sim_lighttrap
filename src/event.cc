#include "event.hh"

#include "G4SystemOfUnits.hh"


MyEventAction::MyEventAction(MyRunAction*)
{
  fEdep = 0.;
}

MyEventAction::~MyEventAction()
{}

void MyEventAction::BeginOfEventAction(const G4Event*)
{
  fEdep = 0.;
}

void MyEventAction::EndOfEventAction(const G4Event* event)
{
  // G4cout << "Energy deposition: " << fEdep << G4endl;

  G4AnalysisManager *man = G4AnalysisManager::Instance();
  man->FillNtupleDColumn(2, 0, fEdep);
  man->AddNtupleRow(2);

  // Retrieve primary vertex and primary particle
  G4PrimaryVertex* vertex = event->GetPrimaryVertex(0);
  if (vertex) {
    G4ThreeVector pos = vertex->GetPosition();
    G4PrimaryParticle* particle = vertex->GetPrimary();
    
    // Extract momentum information:
    G4ThreeVector momentum = particle->GetMomentum();
    
    // For optical photons (massless), the momentum magnitude is equal to the energy,
    G4double energy = particle->GetKineticEnergy();
    G4double wavelength = (1.239841939 * eV / energy) * 1E+03;  // wavelength in nm
    
    G4int pdgCode = particle->GetPDGcode();

    // Fill the ntuple columns:
    man->FillNtupleIColumn(3, 0, event->GetEventID());
    man->FillNtupleDColumn(3, 1, pos.x());
    man->FillNtupleDColumn(3, 2, pos.y());
    man->FillNtupleDColumn(3, 3, pos.z());
    man->FillNtupleDColumn(3, 4, momentum.x());
    man->FillNtupleDColumn(3, 5, momentum.y());
    man->FillNtupleDColumn(3, 6, momentum.z());
    man->FillNtupleDColumn(3, 7, wavelength);
    man->FillNtupleIColumn(3, 8, pdgCode);

    man->AddNtupleRow(3);
  }


}
