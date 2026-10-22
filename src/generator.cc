#include "generator.hh"
#include "G4TransportationManager.hh"
#include "G4Navigator.hh"
#include "G4VPhysicalVolume.hh"
#include "G4LogicalVolume.hh"
#include "G4VSolid.hh"
#include "G4Box.hh"
#include "G4Exception.hh"
#include "Randomize.hh"
#include <sstream>

MyPrimaryGenerator::MyPrimaryGenerator()
{
  // Default source (overridden by the /gps/ commands of the YAML or the macro):
  // a point source of 128 nm optical photons travelling along +z.
  G4ParticleTable *particleTable = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition *particle = particleTable->FindParticle("opticalphoton");

  G4ThreeVector pos(0., 0., 24.5*cm);
  G4ThreeVector mom(0., 0., 1.);
  G4double energy = 9.68 * eV;

  fGPS = new G4GeneralParticleSource();
  fGPS->GetCurrentSource()->SetParticleDefinition(particle);
  fGPS->GetCurrentSource()->GetPosDist()->SetCentreCoords(pos);
  fGPS->GetCurrentSource()->GetPosDist()->SetPosDisType("Point");
  fGPS->GetCurrentSource()->GetAngDist()->SetParticleMomentumDirection(mom);
  fGPS->GetCurrentSource()->GetEneDist()->SetMonoEnergy(energy);
}

MyPrimaryGenerator::~MyPrimaryGenerator()
{
  delete fGPS;
}

void MyPrimaryGenerator::GeneratePrimaries(G4Event *anEvent)
{
  fGPS->GeneratePrimaryVertex(anEvent);

  // ── Guard: the primary vertex must lie inside the world box ────────────────
  // Geant4 does NOT warn when a vertex is outside the world; the photon is
  // then tracked with a stale navigator state and crosses the sample without
  // interacting (observed: /gps/pos/centre -20 cm with an 18.2 cm world half-
  // length gave 0 WLS photons and 97 % of the beam on the photocathode).
  // Abort with a clear message instead of producing silently wrong physics.
  {
    const G4VPhysicalVolume* world =
        G4TransportationManager::GetTransportationManager()->GetNavigatorForTracking()->GetWorldVolume();
    const G4PrimaryVertex* vtx = anEvent->GetPrimaryVertex(0);
    if (world && vtx) {
      const G4ThreeVector pos = vtx->GetPosition();
      const G4VSolid* solid = world->GetLogicalVolume()->GetSolid();
      if (solid->Inside(pos) == kOutside) {
        std::ostringstream msg;
        msg << "Primary vertex at (" << pos.x()/cm << ", " << pos.y()/cm << ", " << pos.z()/cm
            << ") cm is OUTSIDE the world volume";
        if (const auto* box = dynamic_cast<const G4Box*>(solid))
          msg << " (world half-lengths: " << box->GetXHalfLength()/cm << " x " << box->GetYHalfLength()/cm
              << " x " << box->GetZHalfLength()/cm << " cm)";
        msg << ".\nGeant4 would track it without seeing the sample. Move the source "
               "(/gps/pos/centre, source.centerZ_cm) inside the world, or enlarge the world "
               "with geometry.worldHalfZ_mm / /detector/worldHalfZ.";
        G4Exception("MyPrimaryGenerator::GeneratePrimaries", "SourceOutsideWorld",
                    FatalException, msg.str().c_str());
      }
    }
  }

  // Generate a random polarization vector for optical photons (default GPS particle)
  // Retrieve the momentum direction (assumed to be normalized)
  G4ThreeVector momentumDir = fGPS->GetParticleMomentumDirection();

  // Choose a default vector to help compute a perpendicular vector
  G4ThreeVector refVec(0,0,1);
  if (std::fabs(momentumDir.dot(refVec)) > 0.999) {
      refVec = G4ThreeVector(1,0,0);
  }

  // Create an initial perpendicular vector
  G4ThreeVector perp = momentumDir.cross(refVec).unit();

  // Generate a random rotation angle
  // G4double phi = G4UniformRand() * 2.0 * CLHEP::pi;
  G4double phi = G4UniformRand() * 0.5 * CLHEP::pi;

  // Rotate the perpendicular vector by phi around the momentum direction.
  // This gives a random polarization vector still perpendicular to momentumDir.
  G4ThreeVector randomPol = perp * std::cos(phi) + (momentumDir.cross(perp)) * std::sin(phi);

  // Set the random polarization vector for the optical photon
  fGPS->GetCurrentSource()->SetParticlePolarization(randomPol);
}
