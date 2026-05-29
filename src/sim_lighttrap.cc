#include <iostream>

#include "G4RunManager.hh"
#include "G4UImanager.hh"
#include "G4VisManager.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"
#include "G4GDMLParser.hh"
// #include "G4TransportationManager.hh"
// #include "G4LogicalVolume.hh"

#include "construction.hh"
#include "physics.hh"
#include "action.hh"

int main(int argc, char** argv)
{
  // standard interface for all G4 applications
  G4RunManager *runManager = new G4RunManager();

  runManager->SetUserInitialization(new MyLightTrapConstruction());
  runManager->SetUserInitialization(new MyPhysicsList());
  runManager->SetUserInitialization(new MyActionInitialization());

  runManager->Initialize();

  G4String macroFile = (argc > 1) ? G4String(argv[1]) : G4String("");
  bool isVisMacro = (argc == 1) || (macroFile.find("vis") != std::string::npos);

  G4UIExecutive *ui = 0;
  if (isVisMacro) {
    ui = new G4UIExecutive(argc, argv);
  }

  G4VisManager *visManager = new G4VisExecutive();
  visManager->Initialize();

  G4UImanager *UImanager = G4UImanager::GetUIpointer();
  if (ui) {
    G4String mac = macroFile.empty() ? "vis.mac" : macroFile;
    UImanager->ApplyCommand("/control/execute " + mac);
    ui->SessionStart();
  } else {
    UImanager->ApplyCommand("/control/execute " + macroFile);
  }


  // Export the geometry to GDML
  // G4GDMLParser parser;
  // G4VPhysicalVolume* worldPhysical = G4TransportationManager::GetTransportationManager()
  //                                       ->GetNavigatorForTracking()->GetWorldVolume();
  // parser.Write("detector.gdml", worldPhysical->GetLogicalVolume());

  delete runManager;
  delete visManager;
  if (ui) {
    delete ui;
  }

  return 0;
}
