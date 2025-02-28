#include "generator.hh"

MyPrimaryGenerator::MyPrimaryGenerator()
{
  //fParticleGun = new G4ParticleGun(1); // particle per event
  G4ParticleTable *particleTable = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition *particle = particleTable->FindParticle("opticalphoton");  // examples: e-, e+, proton, gamma

  G4ThreeVector pos(0., 0., 24.5*cm);
  G4ThreeVector mom(0., 0., 1.);
  G4double energy = 9.68 * eV;
  //G4ThreeVector momentumUnitVector = G4RandomDirection();
  //fParticleGun->SetParticleMomentumDirection(momentumUnitVector);

  //fParticleGun->SetParticlePosition(pos);
  //fParticleGun->SetParticleMomentumDirection(mom);
  //fParticleGun->SetParticleMomentum(0.1*MeV);
  //fParticleGun->SetParticleDefinition(particle);

  fGPS = new G4GeneralParticleSource();
  fGPS->GetCurrentSource()->SetParticleDefinition(particle);
  fGPS->GetCurrentSource()->GetPosDist()->SetCentreCoords(pos);
  fGPS->GetCurrentSource()->GetPosDist()->SetPosDisType("Point");
  fGPS->GetCurrentSource()->GetAngDist()->SetParticleMomentumDirection(mom);
  fGPS->GetCurrentSource()->GetEneDist()->SetMonoEnergy(energy);

  // G4cout << "Primary particle generated in Constructor: pol: " << fGPS->GetCurrentSource()->GetParticlePolarization().mag2() << G4endl;

}

MyPrimaryGenerator::~MyPrimaryGenerator()
{
  //delete fParticleGun;
  delete fGPS;
}

void MyPrimaryGenerator::GeneratePrimaries(G4Event *anEvent)
{
  //fParticleGun->GeneratePrimaryVertex(anEvent);
  fGPS->GeneratePrimaryVertex(anEvent);

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
  G4double phi = G4UniformRand() * 2.0 * CLHEP::pi;

  // Rotate the perpendicular vector by phi around the momentum direction.
  // This gives a random polarization vector still perpendicular to momentumDir.
  G4ThreeVector randomPol = perp * std::cos(phi) + (momentumDir.cross(perp)) * std::sin(phi);

  // Set the random polarization vector for the optical photon
  fGPS->GetCurrentSource()->SetParticlePolarization(randomPol);

  // G4cout << "Primary particle generated:" 
  // << " pos: " << fGPS->GetCurrentSource()->GetParticlePosition()
  // << " pol: " << fGPS->GetCurrentSource()->GetParticlePolarization()
  // << G4endl;
}
