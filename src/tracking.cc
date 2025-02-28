#include "tracking.hh"

#include "G4Track.hh"
#include "G4AnalysisManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4VProcess.hh"
#include "G4RunManager.hh"
#include "G4Event.hh"

void MyTrackingAction::PreUserTrackingAction(const G4Track* track)
{
  // Check if the track is an optical photon.
  G4int eventId = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();

  if ( track->GetDefinition()->GetParticleName() == "opticalphoton" ) {
    // Check if the creator process exists and is "OpWLS" (i.e., produced by the pTP material)
    if ( track->GetCreatorProcess() &&
         track->GetCreatorProcess()->GetProcessName() == "OpWLS" ) {
      G4AnalysisManager* man = G4AnalysisManager::Instance();

      G4double energy = track->GetKineticEnergy();
      G4double wavelength = (1.239841939 * eV / energy) * 1E+03;  // wavelength in nm
      
      // Record the initial properties of the WLS photon.
      // Note: If you want to record it only once, this works well in PreUserTrackingAction.
      man->FillNtupleIColumn(4, 0, eventId);
      man->FillNtupleDColumn(4, 1, track->GetPosition().x());
      man->FillNtupleDColumn(4, 2, track->GetPosition().y());
      man->FillNtupleDColumn(4, 3, track->GetPosition().z());
      man->FillNtupleDColumn(4, 4, track->GetMomentum().x());
      man->FillNtupleDColumn(4, 5, track->GetMomentum().y());
      man->FillNtupleDColumn(4, 6, track->GetMomentum().z());
      man->FillNtupleDColumn(4, 7, track->GetGlobalTime());
      man->FillNtupleIColumn(4, 8, track->GetDefinition()->GetPDGEncoding());
      man->FillNtupleDColumn(4, 9, wavelength);
      man->AddNtupleRow(4);
    }
  }
}
