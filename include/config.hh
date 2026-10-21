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

struct AcrylicMcMasterConfig {
    std::vector<double> rindex;
};

struct BlueWLSConfig {
    std::vector<double>   rindex;
    std::vector<double>   wlsabslen_m;
    std::vector<double>   wlscomponent;          // optional inline 13-point spectrum
    std::optional<double> wlstimeconstant_ns;
    // Optional file-provided emission spectrum (arbitrary # of points), loaded
    // from materials.blueWLS.wlscomponent_file. Parallel arrays; empty if none.
    std::vector<double>   emissionWl_nm;         // wavelength [nm]
    std::vector<double>   emissionIntensity;     // relative intensity (auto-normalized)
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

struct VikuitiConfig {
    std::vector<double> reflectivity;
};

struct PTFEConfig {
    std::vector<double> reflectivity;   // diffuse (Lambertian) reflector; ~0.95
};

struct MgF2Config {
    // Optional VUV-transparent PMT entrance window (only built when
    // geometry.pmtWindowThickness_mm > 0 in PMT mode).
    std::vector<double> rindex;
    std::vector<double> abslen_m;
};

struct MaterialsConfig {
    PTPConfig             ptp;
    UVAcrylicConfig       uvAcrylic;
    AcrylicMcMasterConfig acrylicMcMaster;
    BlueWLSConfig         blueWLS;
    LArConfig             lar;
    VikuitiConfig         vikuiti;
    PTFEConfig            ptfe;
    MgF2Config            mgf2;
};

struct SimConfig {
    // ── Geometry (messenger: /detector/<param>) ─────────────────────────────
    int    nSiPMs                   = 30;
    double pTPlayerThickness_mm     = 0.002;  // pTP WLS film
    double uvAcrylicThickness_mm    = 3.0;    // UV-transparent acrylic carrier
    double pTPSubstrateThickness_mm = 6.0;    // blue WLS slab
    double LArThickness_mm          = 3.0;    // LAr gap
    double lightTrapSize_cm         = 15.0;   // square module side
    double pTPsigmaAlpha_rad        = 0.0;    // pTP surface facet-slope RMS; 0 = smooth
    // Backplane (+z) reflector foil selector: "vikuiti" (specular), "ptfe"
    // (diffuse/Lambertian), or "none" (no foil — full back-face escape).
    std::string backplaneFoil       = "vikuiti";

    // ── Readout stage selector ──────────────────────────────────────────────
    // "sipm": blue-WLS slab + edge SiPMs + reflector foils (original design).
    // "pmt" : the second layer is replaced by a PMT whose photocathode faces
    //         the first layer across the LAr gap (LArThickness_mm).
    std::string detectorType        = "sipm";
    double pmtDiameter_mm           = 23.0;   // photocathode (sensitive) diameter
    double pmtWindowThickness_mm    = 0.0;    // MgF2 entrance window; 0 = bare photocathode
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
