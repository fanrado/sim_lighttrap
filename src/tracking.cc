#include "tracking.hh"
#include "namemap.hh"

#include "G4Track.hh"
#include "G4AnalysisManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4VProcess.hh"
#include "G4RunManager.hh"
#include "G4Event.hh"
#include "G4VTouchable.hh"
#include "G4VPhysicalVolume.hh"
#include "G4LogicalVolume.hh"
#include "G4Material.hh"

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

      // Retrieve the touchable and then the physical volume.
      const G4VTouchable* touchable = track->GetTouchable();
      G4String materialName = "Unknown";
      if (touchable) {
        G4VPhysicalVolume* volume = touchable->GetVolume();
        if (volume) {
          // Get the material from the volume's logical volume.
          G4Material* material = volume->GetLogicalVolume()->GetMaterial();
          if (material) {
            materialName = material->GetName();
            G4cout << "WLS photon created in material: " << materialName 
            << ", volume " << volume->GetName() << G4endl;
          }
        }
      }
      G4int materialCode = NameMap::Encode(materialName);

      // Compute the zenith and azimuth angles from the momentum direction.
      G4ThreeVector direction = track->GetMomentumDirection();
      double cosTheta = direction.z();             // Zenith angle [rad]
      double phi   = std::atan2(direction.y(), direction.x()); // Azimuth angle [rad]
      
      
      // Record the initial properties of the WLS photon.
      // Note: If you want to record it only once, this works well in PreUserTrackingAction.
      man->FillNtupleIColumn(4, 0, eventId);
      man->FillNtupleDColumn(4, 1, track->GetPosition().x());
      man->FillNtupleDColumn(4, 2, track->GetPosition().y());
      man->FillNtupleDColumn(4, 3, track->GetPosition().z());
      man->FillNtupleDColumn(4, 4, cosTheta);
      man->FillNtupleDColumn(4, 5, phi);
      man->FillNtupleDColumn(4, 6, track->GetMomentum().z());
      man->FillNtupleDColumn(4, 7, track->GetGlobalTime());
      man->FillNtupleIColumn(4, 8, track->GetDefinition()->GetPDGEncoding());
      man->FillNtupleDColumn(4, 9, wavelength);
      man->FillNtupleIColumn(4, 10, materialCode);
      man->AddNtupleRow(4);
    }
  }
}
