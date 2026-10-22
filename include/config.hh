#ifndef CONFIG_HH
#define CONFIG_HH

#include <string>
#include <vector>
#include <optional>
#include <stdexcept>

inline void validateOpticalArray(const std::vector<double>& v, const std::string& name)
{
    if (!v.empty() && v.size() != 13)
        throw std::runtime_error(
            "SimConfig: optical array '" + name + "' must have 13 entries, got " +
            std::to_string(v.size()));
}

struct PTPConfig {
    std::vector<double>   rindex;
    std::vector<double>   abslen_m;
    std::vector<double>   wlsabslen_m;
    std::vector<double>   wlscomponent;          // optional inline 13-point spectrum
    std::optional<double> wlstimeconstant_ns;
    // Optional file-provided emission spectrum (arbitrary # of points), loaded
    // from materials.ptp.wlscomponent_file. Parallel arrays; empty if no file.
    std::vector<double>   emissionWl_nm;         // wavelength [nm]
    std::vector<double>   emissionIntensity;     // relative intensity (auto-normalized)
};

struct UVAcrylicConfig {
    std::vector<double> rindex;
    std::vector<double> abslen_m;
};

struct LArConfig {
    std::vector<double>   rindex;
    std::vector<double>   abslen_m;
    std::vector<double>   rayleigh_m;
    std::vector<double>   scintcomponent;
    std::optional<double> scintillationyield;
    std::optional<double> scintillationyield1;
    std::optional<double> scintillationyield2;
    std::optional<double> resolutionscale;
    std::optional<double> scintillationtimeconstant1_ns;
    std::optional<double> scintillationtimeconstant2_ns;
};

struct GArConfig {
    // Argon gas (1 atm) filling the world when geometry.worldMedium = gar.
    std::vector<double> rindex;
    std::vector<double> abslen_m;
    std::vector<double> rayleigh_m;
};

struct MgF2Config {
    // Optional VUV-transparent PMT entrance window (only built when
    // geometry.pmtWindowThickness_mm > 0).
    std::vector<double> rindex;
    std::vector<double> abslen_m;
};

struct MaterialsConfig {
    PTPConfig             ptp;
    UVAcrylicConfig       uvAcrylic;
    LArConfig             lar;
    GArConfig             gar;
    MgF2Config            mgf2;
};

struct SimConfig {
    // ── Geometry (messenger: /detector/<param>) ─────────────────────────────
    // withSample = false removes the pTP film + UV acrylic (and the first-layer
    // edge counters) while keeping the beam, the PMT and the backplane
    // reference-counter plane in place: the "no sample" reference run for a
    // transmission measurement.  CLI: with_sample=on|off (overrides YAML).
    bool   withSample               = true;
    // World medium filling the beam path, the gap and the counters:
    //   "gar"    argon gas at 1 atm (bench measurement; default)
    //   "lar"    liquid argon (scintillating, Rayleigh length 0.9 m)
    //   "vacuum" G4_Galactic with n = 1
    // CLI: world_medium=gar|lar|vacuum (overrides YAML).
    std::string worldMedium         = "gar";
    double pTPlayerThickness_mm     = 0.002;  // pTP WLS film
    double uvAcrylicThickness_mm    = 3.0;    // UV-transparent acrylic carrier
    double LArThickness_mm          = 7.0;    // LAr gap: first-layer back face → PMT window front face
    double lightTrapSize_cm         = 15.0;   // square first-layer side
    double pTPsigmaAlpha_rad        = 0.0;    // pTP surface facet-slope RMS; 0 = smooth

    // ── PMT readout: Hamamatsu R6836-like cylinder facing the first layer ────
    // Datasheet (TPMH1264E): tube/faceplate Ø 28.2 ± 0.8 mm, photocathode
    // Ø 23 mm min. effective area, body length 92 ± 2 mm, MgF2 window, Cs-Te.
    double pmtDiameter_mm           = 23.0;   // photocathode (sensitive) diameter
    double pmtTubeDiameter_mm       = 28.2;   // tube / faceplate outer diameter
    double pmtLength_mm             = 92.0;   // faceplate front → end of the glass body
    double pmtWindowThickness_mm    = 1.5;    // MgF2 faceplate thickness (not on the datasheet: assumption); 0 = bare photocathode
    double pmtWallThickness_mm      = 1.0;    // envelope side-wall / end-cap thickness (opaque)
    double pmtQE                    = 1.0;    // flat quantum efficiency inside [pmtQEmin, pmtQEmax]
    double pmtQEmin_nm              = 110.0;  // QE window lower edge [nm]
    double pmtQEmax_nm              = 500.0;  // QE window upper edge [nm]

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
    double radius_cm          = 0.7;    // Circle shape only (14 mm beam): /gps/pos/radius
    double directionX         = 0.0;
    double directionY         = 0.0;
    double directionZ         = 1.0;

    // ── Run ─────────────────────────────────────────────────────────────────
    int nEvents = 10000;

    // ── Optical material properties ──────────────────────────────────────────
    MaterialsConfig materials;

    static SimConfig fromFile(const std::string& path);
};

#endif
