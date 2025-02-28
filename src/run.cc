#include "run.hh"

MyRunAction::MyRunAction()
{
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->CreateNtuple("Photons", "Photons");
  man->CreateNtupleIColumn("fEvent");
  man->CreateNtupleDColumn("fX");
  man->CreateNtupleDColumn("fY");
  man->CreateNtupleDColumn("fZ");
  man->CreateNtupleDColumn("fT");
  man->CreateNtupleDColumn("fwl");
  man->FinishNtuple(0);

  man->CreateNtuple("Hits", "Hits");
  man->CreateNtupleIColumn("fEvent");
  man->CreateNtupleDColumn("fX");
  man->CreateNtupleDColumn("fY");
  man->CreateNtupleDColumn("fZ");
  man->FinishNtuple(1);

  man->CreateNtuple("Energy", "Energy");
  man->CreateNtupleDColumn("fEdep");
  man->FinishNtuple(2);


  // Now add one for Primary particle information:
  man->CreateNtuple("Primary", "Primary Particle Information");
  man->CreateNtupleIColumn("eventID");
  man->CreateNtupleDColumn("posX"); // position
  man->CreateNtupleDColumn("posY");
  man->CreateNtupleDColumn("posZ");
  man->CreateNtupleDColumn("momX"); // momentum
  man->CreateNtupleDColumn("momY");
  man->CreateNtupleDColumn("momZ"); 
  man->CreateNtupleDColumn("wl"); // wavelength
  man->CreateNtupleIColumn("pdg"); // pdg code
  man->FinishNtuple(3);

}

MyRunAction::~MyRunAction()
{}

void MyRunAction::BeginOfRunAction(const G4Run* run)
{
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  G4int runNumber = run->GetRunID();
  std::stringstream strRunID;
  strRunID << runNumber;
  man->OpenFile("output_apexltsim"+strRunID.str()+".root");

}

void MyRunAction::EndOfRunAction(const G4Run*)
{
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->Write();
  man->CloseFile();
}
