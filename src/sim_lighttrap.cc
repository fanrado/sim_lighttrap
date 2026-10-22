#include <iostream>
#include <string>
#include <sstream>
#include <cctype>
#include <cstdlib>

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

// Parses the optional "with_sample=on|off" command-line argument (also
// accepts --with_sample=, --with-sample=, with-sample=, and true/false/1/0,
// case-insensitive).  Returns true if `arg` is such an argument; the parsed
// value is stored in `value`.
static bool parseWithSampleArg(const std::string& arg, bool& value)
{
    std::string key = arg, lower;
    while (!key.empty() && key[0] == '-') key.erase(0, 1);
    for (char c : key) lower += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    const std::string k1 = "with_sample=", k2 = "with-sample=";
    std::string v;
    if (lower.rfind(k1, 0) == 0)      v = lower.substr(k1.size());
    else if (lower.rfind(k2, 0) == 0) v = lower.substr(k2.size());
    else return false;
    if (v == "on" || v == "true" || v == "1" || v == "yes")       value = true;
    else if (v == "off" || v == "false" || v == "0" || v == "no") value = false;
    else {
        std::cerr << "error: " << arg << " -- expected with_sample=on|off\n";
        std::exit(2);
    }
    return true;
}

// Parses the optional "world_medium=gar|lar|vacuum" argument (also
// --world_medium=, --world-medium=, world-medium=; case-insensitive).
static bool parseWorldMediumArg(const std::string& arg, std::string& value)
{
    std::string key = arg, lower;
    while (!key.empty() && key[0] == '-') key.erase(0, 1);
    for (char c : key) lower += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
    const std::string k1 = "world_medium=", k2 = "world-medium=";
    std::string v;
    if (lower.rfind(k1, 0) == 0)      v = lower.substr(k1.size());
    else if (lower.rfind(k2, 0) == 0) v = lower.substr(k2.size());
    else return false;
    if (v == "gar" || v == "lar" || v == "vacuum") { value = v; return true; }
    std::cerr << "error: " << arg << " -- expected world_medium=gar|lar|vacuum\n";
    std::exit(2);
}

// Parses "pmt_qe=<file>" (also --pmt_qe=, --pmt-qe=, pmt-qe=): PMT QE table.
static bool parsePMTQEArg(const std::string& arg, std::string& value)
{
    std::string key = arg;
    while (!key.empty() && key[0] == '-') key.erase(0, 1);
    const std::string k1 = "pmt_qe=", k2 = "pmt-qe=";
    if (key.rfind(k1, 0) == 0)      { value = key.substr(k1.size()); return true; }
    else if (key.rfind(k2, 0) == 0) { value = key.substr(k2.size()); return true; }
    return false;
}

static void usage()
{
    std::cerr <<
        "usage: sim_lighttrap [config.yaml] [macro.mac] [with_sample=on|off] [world_medium=gar|lar|vacuum]\n"
        "  config.yaml        geometry/source/materials (applied first)\n"
        "  macro.mac          Geant4 macro (overrides YAML; a name containing 'vis' opens the Qt UI)\n"
        "  with_sample=on|off build the pTP-coated acrylic sample (on, default) or run the\n"
        "                     bare beam -> PMT reference with the identical geometry (off);\n"
        "                     overrides geometry.withSample in the YAML\n"
        "  world_medium=...   medium filling the beam path and the gap: gar (argon gas, 1 atm,\n"
        "                     default) | lar (liquid argon) | vacuum; overrides geometry.worldMedium\n"
        "  pmt_qe=<file>      PMT quantum-efficiency table '<wavelength_nm> <QE>' (fraction or %);\n"
        "                     replaces the flat QE band; overrides geometry.pmtQEFile\n";
}

static std::string d2s(double v)
{
    std::ostringstream os;
    os << v;
    return os.str();
}

int main(int argc, char** argv)
{
    // Separate YAML config file, optional Geant4 macro file and with_sample flag
    std::string configFile, macroFile;
    bool withSampleArg = true, hasWithSampleArg = false;
    std::string worldMediumArg, pmtQEArg;
    bool hasPMTQEArg = false;
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "-h" || arg == "--help") { usage(); return 0; }
        if (parseWithSampleArg(arg, withSampleArg)) { hasWithSampleArg = true; continue; }
        if (parseWorldMediumArg(arg, worldMediumArg)) continue;
        if (parsePMTQEArg(arg, pmtQEArg)) { hasPMTQEArg = true; continue; }
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
    if (hasWithSampleArg)
        cfg.withSample = withSampleArg;          // CLI overrides YAML
    const bool hasWorldMediumArg = !worldMediumArg.empty();
    if (hasWorldMediumArg)
        cfg.worldMedium = worldMediumArg;        // CLI overrides YAML
    if (hasPMTQEArg)
        cfg.pmtQEFile = pmtQEArg;                // CLI overrides YAML ("" = flat band)
    if (!cfg.pmtQEFile.empty())
        std::cout << "[sim_lighttrap] pmt_qe = " << cfg.pmtQEFile
                  << (hasPMTQEArg ? " (command line)" : " (YAML)") << "\n";
    std::cout << "[sim_lighttrap] with_sample = " << (cfg.withSample ? "on" : "off")
              << (hasWithSampleArg ? " (command line)" : hasConfig ? " (YAML)" : " (default)") << "\n";
    std::cout << "[sim_lighttrap] world_medium = " << cfg.worldMedium
              << (hasWorldMediumArg ? " (command line)" : hasConfig ? " (YAML)" : " (default)") << "\n";

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
    if (!hasConfig && (hasWithSampleArg || hasWorldMediumArg || hasPMTQEArg)) {
        // No YAML: only the command-line switches change the default geometry.
        UImanager->ApplyCommand(std::string("/detector/withSample ") + (cfg.withSample ? "true" : "false"));
        UImanager->ApplyCommand("/detector/worldMedium " + cfg.worldMedium);
        UImanager->ApplyCommand("/detector/pmtQEFile " + cfg.pmtQEFile);
        UImanager->ApplyCommand("/run/reinitializeGeometry");
        // /run/reinitializeGeometry only flags the rebuild; force it now so the
        // sample-free geometry is what the viewer / volume dump / first run sees.
        UImanager->ApplyCommand("/run/initialize");
    }
    if (hasConfig) {
        UImanager->ApplyCommand(std::string("/detector/withSample ") + (cfg.withSample ? "true" : "false"));
        UImanager->ApplyCommand("/detector/worldMedium " + cfg.worldMedium);
        // Geometry — lighttrapsize messenger stores value in mm (G4 unit)
        UImanager->ApplyCommand("/detector/pTPlayerthickness "   + d2s(cfg.pTPlayerThickness_mm));
        UImanager->ApplyCommand("/detector/uvAcrylicThick "      + d2s(cfg.uvAcrylicThickness_mm));
        UImanager->ApplyCommand("/detector/LArthickness "        + d2s(cfg.LArThickness_mm));
        // lightTrapSize is in cm in YAML; convert to mm for the messenger
        UImanager->ApplyCommand("/detector/lighttrapsize "       + d2s(cfg.lightTrapSize_cm * 10.0));
        UImanager->ApplyCommand("/detector/worldHalfZ "          + d2s(cfg.worldHalfZ_mm));
        // pTP surface facet-slope RMS [rad]; 0 = perfectly smooth (no wiggle)
        UImanager->ApplyCommand("/detector/pTPsigmaAlpha "       + d2s(cfg.pTPsigmaAlpha_rad));
        // PMT readout
        UImanager->ApplyCommand("/detector/pmtDiameter "         + d2s(cfg.pmtDiameter_mm));
        UImanager->ApplyCommand("/detector/pmtTubeDiameter "     + d2s(cfg.pmtTubeDiameter_mm));
        UImanager->ApplyCommand("/detector/pmtLength "           + d2s(cfg.pmtLength_mm));
        UImanager->ApplyCommand("/detector/pmtWindowThick "      + d2s(cfg.pmtWindowThickness_mm));
        UImanager->ApplyCommand("/detector/pmtWallThick "        + d2s(cfg.pmtWallThickness_mm));
        UImanager->ApplyCommand("/detector/pmtQE "               + d2s(cfg.pmtQE));
        UImanager->ApplyCommand("/detector/pmtQEmin "            + d2s(cfg.pmtQEmin_nm));
        UImanager->ApplyCommand("/detector/pmtQEmax "            + d2s(cfg.pmtQEmax_nm));
        UImanager->ApplyCommand("/detector/pmtQEFile "           + cfg.pmtQEFile);
        UImanager->ApplyCommand("/run/reinitializeGeometry");
        // Rebuild immediately (reinitializeGeometry only flags it), so that a
        // macro drawing or dumping the geometry before /run/beamOn sees the
        // YAML geometry, not the default one built by runManager->Initialize().
        UImanager->ApplyCommand("/run/initialize");

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
        // Circle shape (e.g. the 14 mm lab beam) uses the radius instead of halfx/halfy
        UImanager->ApplyCommand("/gps/pos/radius " + d2s(cfg.radius_cm) + " cm");
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
