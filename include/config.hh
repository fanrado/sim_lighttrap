#ifndef CONFIG_HH
#define CONFIG_HH

#include <string>

struct SimConfig {
    // ── Geometry (messenger: /detector/<param>) ─────────────────────────────
    int    nSiPMs                   = 30;
    double pTPlayerThickness_mm     = 0.002;  // pTP WLS film
    double uvAcrylicThickness_mm    = 3.0;    // UV-transparent acrylic carrier
    double pTPSubstrateThickness_mm = 6.0;    // blue WLS slab
    double LArThickness_mm          = 3.0;    // LAr gap
    double lightTrapSize_cm         = 15.0;   // square module side

    // ── Source (messenger: /gps/<param>) ────────────────────────────────────
    std::string particle      = "opticalphoton";
    double      energy_eV     = 9.68;
    std::string positionType  = "Plane";
    std::string positionShape = "Square";
    double centerX_cm         = 0.0;
    double centerY_cm         = 0.0;
    double centerZ_cm         = -2.0;
    double halfX_cm           = 7.5;
    double halfY_cm           = 7.5;
    double directionX         = 0.0;
    double directionY         = 0.0;
    double directionZ         = 1.0;

    // ── Run ─────────────────────────────────────────────────────────────────
    int nEvents = 10000;

    static SimConfig fromFile(const std::string& path);
};

#endif
