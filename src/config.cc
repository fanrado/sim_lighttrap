#include "config.hh"
#include <yaml-cpp/yaml.h>
#include <iostream>
#include <stdexcept>

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

    std::cout << "[SimConfig] Loaded: " << path << "\n";
    return cfg;
}
