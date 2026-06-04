#include "config.hh"
#include <yaml-cpp/yaml.h>
#include <iostream>
#include <stdexcept>

static std::vector<double> readVec(const YAML::Node& node, const std::string& key)
{
    std::vector<double> v;
    if (node[key])
        v = node[key].as<std::vector<double>>();
    return v;
}

static MaterialsConfig parseMaterials(const YAML::Node& mat)
{
    MaterialsConfig m;

    if (auto n = mat["ptp"]) {
        m.ptp.rindex       = readVec(n, "rindex");
        m.ptp.abslen_m     = readVec(n, "abslen_m");
        m.ptp.wlsabslen_m  = readVec(n, "wlsabslen_m");
        m.ptp.wlscomponent = readVec(n, "wlscomponent");
        if (n["wlstimeconstant_ns"])
            m.ptp.wlstimeconstant_ns = n["wlstimeconstant_ns"].as<double>();
        validateOpticalArray(m.ptp.rindex,       "ptp.rindex");
        validateOpticalArray(m.ptp.abslen_m,     "ptp.abslen_m");
        validateOpticalArray(m.ptp.wlsabslen_m,  "ptp.wlsabslen_m");
        validateOpticalArray(m.ptp.wlscomponent, "ptp.wlscomponent");
    }

    if (auto n = mat["uvAcrylic"]) {
        m.uvAcrylic.rindex   = readVec(n, "rindex");
        m.uvAcrylic.abslen_m = readVec(n, "abslen_m");
        validateOpticalArray(m.uvAcrylic.rindex,   "uvAcrylic.rindex");
        validateOpticalArray(m.uvAcrylic.abslen_m, "uvAcrylic.abslen_m");
    }

    if (auto n = mat["acrylicMcMaster"]) {
        m.acrylicMcMaster.rindex = readVec(n, "rindex");
        validateOpticalArray(m.acrylicMcMaster.rindex, "acrylicMcMaster.rindex");
    }

    if (auto n = mat["blueWLS"]) {
        m.blueWLS.rindex       = readVec(n, "rindex");
        m.blueWLS.wlsabslen_m  = readVec(n, "wlsabslen_m");
        m.blueWLS.wlscomponent = readVec(n, "wlscomponent");
        if (n["wlstimeconstant_ns"])
            m.blueWLS.wlstimeconstant_ns = n["wlstimeconstant_ns"].as<double>();
        validateOpticalArray(m.blueWLS.rindex,       "blueWLS.rindex");
        validateOpticalArray(m.blueWLS.wlsabslen_m,  "blueWLS.wlsabslen_m");
        validateOpticalArray(m.blueWLS.wlscomponent, "blueWLS.wlscomponent");
    }

    if (auto n = mat["lar"]) {
        m.lar.rindex         = readVec(n, "rindex");
        m.lar.abslen_m       = readVec(n, "abslen_m");
        m.lar.rayleigh_m     = readVec(n, "rayleigh_m");
        m.lar.scintcomponent = readVec(n, "scintcomponent");
        if (n["scintillationyield"])
            m.lar.scintillationyield = n["scintillationyield"].as<double>();
        if (n["scintillationyield1"])
            m.lar.scintillationyield1 = n["scintillationyield1"].as<double>();
        if (n["scintillationyield2"])
            m.lar.scintillationyield2 = n["scintillationyield2"].as<double>();
        if (n["resolutionscale"])
            m.lar.resolutionscale = n["resolutionscale"].as<double>();
        if (n["scintillationtimeconstant1_ns"])
            m.lar.scintillationtimeconstant1_ns = n["scintillationtimeconstant1_ns"].as<double>();
        if (n["scintillationtimeconstant2_ns"])
            m.lar.scintillationtimeconstant2_ns = n["scintillationtimeconstant2_ns"].as<double>();
        validateOpticalArray(m.lar.rindex,         "lar.rindex");
        validateOpticalArray(m.lar.abslen_m,       "lar.abslen_m");
        validateOpticalArray(m.lar.rayleigh_m,     "lar.rayleigh_m");
        validateOpticalArray(m.lar.scintcomponent, "lar.scintcomponent");
    }

    if (auto n = mat["vikuiti"]) {
        m.vikuiti.reflectivity = readVec(n, "reflectivity");
        validateOpticalArray(m.vikuiti.reflectivity, "vikuiti.reflectivity");
    }

    return m;
}

SimConfig SimConfig::fromFile(const std::string& path)
{
    YAML::Node doc;
    try {
        doc = YAML::LoadFile(path);
    } catch (const YAML::Exception& e) {
        throw std::runtime_error("SimConfig: cannot parse '" + path + "': " + e.what());
    }

    SimConfig cfg;

    if (auto geo = doc["geometry"]) {
        if (geo["nSiPMs"])                   cfg.nSiPMs                   = geo["nSiPMs"].as<int>();
        if (geo["pTPlayerThickness_mm"])      cfg.pTPlayerThickness_mm     = geo["pTPlayerThickness_mm"].as<double>();
        if (geo["uvAcrylicThickness_mm"])     cfg.uvAcrylicThickness_mm    = geo["uvAcrylicThickness_mm"].as<double>();
        if (geo["pTPSubstrateThickness_mm"])  cfg.pTPSubstrateThickness_mm = geo["pTPSubstrateThickness_mm"].as<double>();
        if (geo["LArThickness_mm"])           cfg.LArThickness_mm          = geo["LArThickness_mm"].as<double>();
        if (geo["lightTrapSize_cm"])          cfg.lightTrapSize_cm         = geo["lightTrapSize_cm"].as<double>();
    }

    if (auto src = doc["source"]) {
        if (src["particle"])       cfg.particle      = src["particle"].as<std::string>();
        if (src["energy_eV"])      cfg.energy_eV     = src["energy_eV"].as<double>();
        if (src["positionType"])   cfg.positionType  = src["positionType"].as<std::string>();
        if (src["positionShape"])  cfg.positionShape = src["positionShape"].as<std::string>();
        if (src["centerX_cm"])     cfg.centerX_cm    = src["centerX_cm"].as<double>();
        if (src["centerY_cm"])     cfg.centerY_cm    = src["centerY_cm"].as<double>();
        if (src["centerZ_cm"])     cfg.centerZ_cm    = src["centerZ_cm"].as<double>();
        if (src["halfX_cm"])       cfg.halfX_cm      = src["halfX_cm"].as<double>();
        if (src["halfY_cm"])       cfg.halfY_cm      = src["halfY_cm"].as<double>();
        if (src["directionX"])     cfg.directionX    = src["directionX"].as<double>();
        if (src["directionY"])     cfg.directionY    = src["directionY"].as<double>();
        if (src["directionZ"])     cfg.directionZ    = src["directionZ"].as<double>();
    }

    if (auto run = doc["run"]) {
        if (run["nEvents"]) cfg.nEvents = run["nEvents"].as<int>();
    }

    if (auto mat = doc["materials"])
        cfg.materials = parseMaterials(mat);

    std::cout << "[SimConfig] Loaded: " << path << "\n";
    return cfg;
}
