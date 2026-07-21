#include <iostream>
#include <string>
#include <sstream>

#include "G4RunManager.hh"
#include "G4UImanager.hh"
#include "G4VisManager.hh"
#include "G4VisExecutive.hh"
#include "G4UIExecutive.hh"

#include "construction.hh"
#include "physics.hh"
#include "action.hh"
#include "config.hh"

// Returns true for .yaml / .yml filenames
static bool isYamlFile(const std::string& s)
{
    return (s.size() >= 5 && s.substr(s.size()-5) == ".yaml") ||
           (s.size() >= 4 && s.substr(s.size()-4) == ".yml");
}

static std::string d2s(double v)
{
    std::ostringstream os;
    os << v;
    return os.str();
}

int main(int argc, char** argv)
{
    // Separate YAML config file from optional Geant4 macro file
    std::string configFile, macroFile;
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (isYamlFile(arg))
            configFile = arg;
        else
            macroFile = arg;
    }

    // Load YAML config (if provided)
    SimConfig cfg;
    const bool hasConfig = !configFile.empty();
    if (hasConfig)
        cfg = SimConfig::fromFile(configFile);

    // ── Geant4 initialisation ────────────────────────────────────────────────
    G4RunManager *runManager = new G4RunManager();
    runManager->SetUserInitialization(new MyLightTrapConstruction(cfg));
    runManager->SetUserInitialization(new MyPhysicsList());
    runManager->SetUserInitialization(new MyActionInitialization());
    runManager->Initialize();

    // Visualisation mode: interactive when no config and no macro (or "vis" macro)
    bool isVisMacro = !hasConfig &&
                      (macroFile.empty() || macroFile.find("vis") != std::string::npos);

    G4UIExecutive *ui = nullptr;
    if (isVisMacro)
        ui = new G4UIExecutive(argc, argv);

    G4VisManager *visManager = new G4VisExecutive();
    visManager->Initialize();

    G4UImanager *UImanager = G4UImanager::GetUIpointer();

    // ── Apply YAML settings via the existing messenger commands ──────────────
    // Geometry parameters (/detector/ messenger — DeclareProperty expects G4
    // internal units: mm for length).
    if (hasConfig) {
        // Geometry — lighttrapsize messenger stores value in mm (G4 unit)
        UImanager->ApplyCommand("/detector/nSiPMs "              + std::to_string(cfg.nSiPMs));
        UImanager->ApplyCommand("/detector/pTPlayerthickness "   + d2s(cfg.pTPlayerThickness_mm));
        UImanager->ApplyCommand("/detector/uvAcrylicThick "      + d2s(cfg.uvAcrylicThickness_mm));
        UImanager->ApplyCommand("/detector/pTPsubstratethickness " + d2s(cfg.pTPSubstrateThickness_mm));
        UImanager->ApplyCommand("/detector/LArthickness "        + d2s(cfg.LArThickness_mm));
        // lightTrapSize is in cm in YAML; convert to mm for the messenger
        UImanager->ApplyCommand("/detector/lighttrapsize "       + d2s(cfg.lightTrapSize_cm * 10.0));
        // pTP surface facet-slope RMS [rad]; 0 = perfectly smooth (no wiggle)
        UImanager->ApplyCommand("/detector/pTPsigmaAlpha "       + d2s(cfg.pTPsigmaAlpha_rad));
        // Backplane reflector foil: vikuiti | ptfe | none
        UImanager->ApplyCommand("/detector/backplaneFoil "       + cfg.backplaneFoil);
        UImanager->ApplyCommand("/run/reinitializeGeometry");

        // Source — GPS commands accept explicit unit tokens
        UImanager->ApplyCommand("/gps/particle "   + cfg.particle);
        UImanager->ApplyCommand("/gps/energy "     + d2s(cfg.energy_eV) + " eV");
        UImanager->ApplyCommand("/gps/pos/type "   + cfg.positionType);
        UImanager->ApplyCommand("/gps/pos/shape "  + cfg.positionShape);
        UImanager->ApplyCommand("/gps/pos/centre " + d2s(cfg.centerX_cm) + " "
                                                   + d2s(cfg.centerY_cm) + " "
                                                   + d2s(cfg.centerZ_cm) + " cm");
        UImanager->ApplyCommand("/gps/pos/halfx "  + d2s(cfg.halfX_cm) + " cm");
        UImanager->ApplyCommand("/gps/pos/halfy "  + d2s(cfg.halfY_cm) + " cm");
        UImanager->ApplyCommand("/gps/direction "  + d2s(cfg.directionX) + " "
                                                   + d2s(cfg.directionY) + " "
                                                   + d2s(cfg.directionZ));
    }

    // ── Run macro (can override YAML settings) or beam-on ───────────────────
    if (ui) {
        G4String mac = macroFile.empty() ? "vis.mac" : G4String(macroFile);
        UImanager->ApplyCommand("/control/execute " + mac);
        ui->SessionStart();
    } else if (!macroFile.empty()) {
        UImanager->ApplyCommand("/control/execute " + G4String(macroFile));
    } else if (hasConfig) {
        // YAML-only batch mode
        UImanager->ApplyCommand("/run/beamOn " + std::to_string(cfg.nEvents));
    }

    delete runManager;
    delete visManager;
    delete ui;

    return 0;
}
