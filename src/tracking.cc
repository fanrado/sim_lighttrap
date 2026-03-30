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
    if ( track->GetCreatorProcess() ) {
      G4String processName = track->GetCreatorProcess()->GetProcessName();
      if (processName == "OpWLS" || processName == "Scintillation") {
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
              // G4cout << "WLS photon created in material: " << materialName 
              // << ", volume " << volume->GetName() << G4endl;
            }
          }
        }
  
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
        man->FillNtupleIColumn(4, 6, NameMap::Encode(processName));
        man->FillNtupleDColumn(4, 7, track->GetGlobalTime());
        man->FillNtupleIColumn(4, 8, track->GetDefinition()->GetPDGEncoding());
        man->FillNtupleDColumn(4, 9, wavelength);
        man->FillNtupleIColumn(4, 10, NameMap::Encode(materialName));
        man->AddNtupleRow(4);
      }
    }
  }

  //
  if (track->GetDefinition()->GetParticleName() == "opticalphoton") {
    
    // Track interface crossings
    G4VPhysicalVolume* currentVolume = track->GetVolume();
    
    if (currentVolume) {
      G4String currentMaterial = currentVolume->GetLogicalVolume()->GetMaterial()->GetName();
      
      // Check for transitions
      if (track->GetCreatorProcess() == nullptr) { // Primary photon
        G4AnalysisManager* man = G4AnalysisManager::Instance();
        
        // Record initial photon properties for validation
        G4double energy = track->GetKineticEnergy();
        G4double wavelength = (1.239841939 * eV / energy) * 1E+03;
        G4ThreeVector direction = track->GetMomentumDirection();
        
        // Calculate incident angle with respect to surface normal
        G4double incidentAngle = std::acos(std::abs(direction.z()));
        
        // Fill validation data (ntuple 5 created in MyRunAction)
        G4int eventId = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
        man->FillNtupleIColumn(5, 0, eventId);
        man->FillNtupleDColumn(5, 1, wavelength);
        man->FillNtupleDColumn(5, 2, incidentAngle * 180.0 / CLHEP::pi);
        man->FillNtupleSColumn(5, 3, currentMaterial);
        // column 4 (reflected) filled in PostUserTrackingAction once track ends
        man->FillNtupleDColumn(5, 5, track->GetPosition().x());
        man->FillNtupleDColumn(5, 6, track->GetPosition().y());
        man->FillNtupleDColumn(5, 7, track->GetPosition().z());
        // AddNtupleRow deferred to PostUserTrackingAction
      }
    }
  }
}

// Add this method to track boundary processes
void MyTrackingAction::PostUserTrackingAction(const G4Track* track)
{
  if (track->GetDefinition()->GetParticleName() == "opticalphoton"
      && track->GetCreatorProcess() == nullptr) { // primary photons only
    G4AnalysisManager* man = G4AnalysisManager::Instance();

    // reflected = 1 if photon ended up behind the source plane(z < 24.5)
    G4double finalZ = track->GetPosition().z();
    G4int reflected = (finalZ < 24.5) ? 1 : 0;

    man->FillNtupleIColumn(5, 4, reflected);
    man->AddNtupleRow(5);
  }
}