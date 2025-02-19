#include "generator.hh"

MyPrimaryGenerator::MyPrimaryGenerator()
{
  //fParticleGun = new G4ParticleGun(1); // particle per event
  G4ParticleTable *particleTable = G4ParticleTable::GetParticleTable();
  G4ParticleDefinition *particle = particleTable->FindParticle("gamma");  // examples: e-, e+, proton, gamma

  G4ThreeVector pos(0., 0., 0.2*m);
  G4ThreeVector mom(0., 0., 1.);
  //G4ThreeVector momentumUnitVector = G4RandomDirection();
  //fParticleGun->SetParticleMomentumDirection(momentumUnitVector);

  //fParticleGun->SetParticlePosition(pos);
  //fParticleGun->SetParticleMomentumDirection(mom);
  //fParticleGun->SetParticleMomentum(0.1*MeV);
  //fParticleGun->SetParticleDefinition(particle);

  fGPS = new G4GeneralParticleSource();
  fGPS->SetParticleDefinition(particle);
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
}
