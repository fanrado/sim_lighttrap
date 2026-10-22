#include "construction.hh"
#include "G4VisAttributes.hh"
#include "G4Colour.hh"

#include <cmath>
#include <vector>
#include <algorithm>
#include <utility>

// ─────────────────────────────────────────────────────────────────────────────
// MyLightTrapConstruction
//
// Builds the LightTrap first layer in a selectable medium (argon gas by default,
// liquid argon or vacuum), read out by a PMT (bench-measurement configuration).
//
// Structure (photons travel in +z direction; PMT front face at z = 0):
//
//   [world medium] ► pTP film (2 µm)    ← WLS: VUV (128 nm) → 340–430 nm
//                   UV acrylic (3 mm)  ← mechanical carrier, UV-transparent
//                   [7 mm gap, world medium]
//                   PMT (Hamamatsu R6836-like cylinder, Ø 28.2 mm × 92 mm):
//                     MgF2 faceplate → photocathode disc (Ø 23 mm, terminal QE
//                     counter) → vacuum → opaque glass side wall + end cap
//                   + pass-through counters on the first-layer back face and ±x edges
// ─────────────────────────────────────────────────────────────────────────────

G4double* MyLightTrapConstruction::resolveArray(
    const std::vector<double>& cfg, double unitFactor,
    G4double (&buf)[13], G4double* fallback)
{
    if (!cfg.empty()) {
        for (int i = 0; i < 13; ++i)
            buf[i] = cfg[i] * unitFactor;
        return buf;
    }
    return fallback;
}

MyLightTrapConstruction::MyLightTrapConstruction(const SimConfig& cfg)
: EVUM(1.239841939*eV), fCfg(cfg)
{
  // ── Runtime messenger: /detector/<command> ──────────────────────────────────
  fMessenger = new G4GenericMessenger(this, "/detector/", "Light Trap Construction");
  fMessenger->DeclareProperty("worldMedium",
      fWorldMedium,         "World medium: gar (argon gas, 1 atm) | lar (liquid argon) | vacuum");
  fMessenger->DeclareProperty("withSample",
      fWithSample,          "Build the pTP-coated acrylic sample (true) or run the bare beam->PMT reference (false)");
  fMessenger->DeclareProperty("pTPlayerthickness",
      pTPlayerthickness,    "pTP WLS film thickness [default 2 µm]");
  fMessenger->DeclareProperty("uvAcrylicThick",
      uvAcrylicThickness,   "UV-transparent acrylic carrier thickness [default 3 mm]");
  fMessenger->DeclareProperty("LArthickness",
      LArthickness,         "LAr gap between the first-layer back face and the PMT faceplate [default 7 mm]");
  fMessenger->DeclareProperty("lighttrapsize",
      lighttrapsize,        "Square first-layer side length [default 15 cm]");
  fMessenger->DeclareProperty("worldHalfZ",
      worldHalfZ,           "World box half-length in z [mm]; 0 = automatic (0.6*side + PMT length)");
  fMessenger->DeclareProperty("pTPsigmaAlpha",
      pTPsigmaAlpha,        "pTP surface facet-slope RMS [rad]; 0 = perfectly smooth");
  fMessenger->DeclareProperty("pmtDiameter",
      pmtDiameter,          "PMT photocathode diameter [default 23 mm]");
  fMessenger->DeclareProperty("pmtTubeDiameter",
      pmtTubeDiameter,      "PMT tube / faceplate outer diameter [default 28.2 mm]");
  fMessenger->DeclareProperty("pmtLength",
      pmtLength,            "PMT length, faceplate front to end of the glass body [default 92 mm]");
  fMessenger->DeclareProperty("pmtWindowThick",
      pmtWindowThickness,   "PMT MgF2 faceplate thickness; 0 = bare photocathode [default 1.5 mm]");
  fMessenger->DeclareProperty("pmtWallThick",
      pmtWallThickness,     "PMT envelope side-wall / end-cap thickness [default 1 mm]");
  fMessenger->DeclareProperty("pmtQE",
      pmtQE,                "PMT flat quantum efficiency inside the QE band [default 1.0]");
  fMessenger->DeclareProperty("pmtQEmin",
      pmtQEmin_nm,          "PMT QE band lower edge [nm, default 110]");
  fMessenger->DeclareProperty("pmtQEmax",
      pmtQEmax_nm,          "PMT QE band upper edge [nm, default 500]");

  // ── Default geometry parameters ─────────────────────────────────────────────
  fWithSample           = true;     // sample in the beam by default
  fWorldMedium          = "gar";    // argon gas: bench transmission measurement
  pTPlayerthickness     = 0.002*mm; // 2 µm pTP film
  uvAcrylicThickness    = 3.*mm;    // 3 mm UV-transparent acrylic carrier
  LArthickness          = 7.*mm;    // 7 mm LAr gap between first layer and PMT faceplate
  lighttrapsize         = 15.*cm;   // 15 cm × 15 cm first layer (real detector size)
  worldHalfZ            = 0.;       // automatic world z half-length
  pTPsigmaAlpha         = 0.0;      // perfectly smooth pTP surface (no wiggle); rad
  pmtDiameter           = 23.*mm;   // photocathode min. effective area (Hamamatsu R6836)
  pmtTubeDiameter       = 28.2*mm;  // R6836 tube / faceplate diameter (28.2 ± 0.8 mm)
  pmtLength             = 92.*mm;   // R6836 body length (92 ± 2 mm), faceplate to end of glass
  pmtWindowThickness    = 1.5*mm;   // MgF2 faceplate (thickness not on the datasheet: assumption)
  pmtWallThickness      = 1.*mm;    // opaque envelope wall / end cap
  pmtQE                 = 1.0;      // ideal PMT: 100 % QE ...
  pmtQEmin_nm           = 110.;     // ... from 110 nm ...
  pmtQEmax_nm           = 500.;     // ... to 500 nm, 0 outside

  // ── Photon energy sampling points ───────────────────────────────────────────
  // 13 wavelengths [nm]: { 530, 425, 400, 340, 305, 160, 145, 135, 128, 125, 120, 115, 106 }
  // 115–145 nm sub-range densified to bracket the LAr scintillation peak at 128 nm
  // and avoid silent G4 extrapolation outside the table.
  G4double tmp[13] = {
    EVUM/0.530, EVUM/0.425, EVUM/0.400, EVUM/0.340, EVUM/0.305,
    EVUM/0.160, EVUM/0.145, EVUM/0.135, EVUM/0.128,
    EVUM/0.125, EVUM/0.120, EVUM/0.115, EVUM/0.106
  };
  std::copy(tmp, tmp+13, energy);

  DefineMaterials();
}

MyLightTrapConstruction::~MyLightTrapConstruction()
{}

G4double MyLightTrapConstruction::WorldHalfZ() const
{
  const G4double autoHalf = lighttrapsize * 0.6 + pmtLength;
  return (worldHalfZ > autoHalf) ? worldHalfZ : autoHalf;
}

// ─────────────────────────────────────────────────────────────────────────────
// Material definitions
// ─────────────────────────────────────────────────────────────────────────────

// Adds a WLS emission spectrum to `mpt`. WLSCOMPONENT is allowed its own energy
// grid, so a fine/arbitrary spectrum can be used regardless of the shared
// 13-point grid. Precedence: file table > inline 13-point > smooth Gaussian.
void MyLightTrapConstruction::addWLSEmission(
    G4MaterialPropertiesTable* mpt,
    const std::vector<double>& fileWl, const std::vector<double>& fileInt,
    const std::vector<double>& inline13,
    G4double peak, G4double sigBlue, G4double sigRed,
    G4double lamMin, G4double lamMax)
{
  if (!fileWl.empty()) {
    // File-provided spectrum: (wavelength nm, intensity) -> (energy, value),
    // sorted by strictly ascending energy (Geant4 requirement), dups dropped.
    std::vector<std::pair<G4double, G4double>> pts;
    pts.reserve(fileWl.size());
    for (std::size_t i = 0; i < fileWl.size(); ++i)
      pts.emplace_back(EVUM / (fileWl[i] / 1000.), fileInt[i]);   // nm -> µm -> eV
    std::sort(pts.begin(), pts.end());
    std::vector<G4double> eE, eV;
    eE.reserve(pts.size());
    eV.reserve(pts.size());
    for (const auto& p : pts) {
      if (!eE.empty() && p.first <= eE.back()) continue;
      eE.push_back(p.first);
      eV.push_back(p.second);
    }
    mpt->AddProperty("WLSCOMPONENT", eE.data(), eV.data(), static_cast<G4int>(eE.size()));
  } else if (!inline13.empty()) {
    // Explicit inline 13-point spectrum on the shared grid (back-compat).
    G4double v13[13];
    std::copy(inline13.begin(), inline13.begin() + 13, v13);
    mpt->AddProperty("WLSCOMPONENT", energy, v13, 13);
  } else {
    // Built-in smooth default: asymmetric Gaussian (longer red tail) on a
    // dedicated fine grid, avoiding the coarse-grid piecewise-linear artifact.
    constexpr G4int kNEm = 40;
    G4double emE[kNEm], emV[kNEm];
    for (G4int i = 0; i < kNEm; ++i) {
      // walk wavelength high -> low so photon energy is strictly ascending
      const G4double lam = lamMax - (lamMax - lamMin) * i / (kNEm - 1);  // nm
      const G4double sig = (lam >= peak) ? sigRed : sigBlue;
      const G4double d   = lam - peak;
      emE[i] = EVUM / (lam / 1000.);
      emV[i] = std::exp(-d * d / (2. * sig * sig));
    }
    mpt->AddProperty("WLSCOMPONENT", emE, emV, kNEm);
  }
}

void MyLightTrapConstruction::DefinePTPMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();

  // p-terphenyl (pTP): C18H14, first WLS stage.
  // Absorbs VUV (106–305 nm) and re-emits at 340–430 nm.
  // Ref: Nucl. Instr. Meth. Phys. Res. A 327 (1993) 354.
  pTP = new G4Material("pTP", 1.23*g/cm3, 2);
  pTP->AddElement(nist->FindOrBuildElement("C"), 18);
  pTP->AddElement(nist->FindOrBuildElement("H"), 14);

  // Wavelengths [nm]: { 530,  425,  400,   340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  G4double rindex[13]   = {1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65};
  // WLS absorption: transparent at >= 340 nm, 0.5 µm from 305 nm down so a
  // 2 µm film captures UV up to ~300 nm (kept identical to sim_config.yaml,
  // which is the documented source of truth; macro-only runs use this table).
  G4double abslen[13]   = {10*m, 10*m, 10*m, 10*m, 0.0005*mm, 0.0005*mm, 0.0005*mm, 0.0005*mm,
                           0.0005*mm, 0.0005*mm, 0.0005*mm, 0.0005*mm, 0.0005*mm};
  G4double emission[13] = {0., 0.0005, 0.002, 0.022, 0.0005, 0., 0., 0., 0., 0., 0., 0., 0.};
  G4double bulkabs[13]  = {1*m, 1*m, 1*m, 1*m, 100*m, 100*m, 100*m, 100*m,
                           100*m, 100*m, 100*m, 100*m, 100*m};

  G4double buf_ri[13], buf_abs[13], buf_wls[13], buf_em[13];
  G4double* p_rindex   = resolveArray(fCfg.materials.ptp.rindex,      1., buf_ri,  rindex);
  G4double* p_bulkabs  = resolveArray(fCfg.materials.ptp.abslen_m,    m,  buf_abs, bulkabs);
  G4double* p_wlsabs   = resolveArray(fCfg.materials.ptp.wlsabslen_m, m,  buf_wls, abslen);
  G4double* p_emission = resolveArray(fCfg.materials.ptp.wlscomponent, 1., buf_em, emission);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",       energy, p_rindex,   13);
  mpt->AddProperty("ABSLENGTH",    energy, p_bulkabs,  13);
  mpt->AddProperty("WLSABSLENGTH", energy, p_wlsabs,   13);

  // ── WLS emission spectrum ──────────────────────────────────────────────────
  // File (materials.ptp.wlscomponent_file) > inline 13-pt (wlscomponent) >
  // built-in smooth default: asymmetric Gaussian peaking at 340 nm (blue σ=18,
  // red σ=30 nm), avoiding the coarse-grid piecewise-linear artifact. Real pTP
  // emission is not Gaussian — supply measured data via the file for accuracy.
  (void)p_emission;  // superseded by addWLSEmission()
  addWLSEmission(mpt,
      fCfg.materials.ptp.emissionWl_nm, fCfg.materials.ptp.emissionIntensity,
      fCfg.materials.ptp.wlscomponent,
      /*peak*/340., /*sigBlue*/18., /*sigRed*/30., /*lamMin*/305., /*lamMax*/460.);

  mpt->AddConstProperty("WLSTIMECONSTANT",
      fCfg.materials.ptp.wlstimeconstant_ns.value_or(1.136) * ns);
  pTP->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineUVTransparentAcrylicMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();

  // UV-transparent PMMA (e.g., Plexiglas UVT / Spartech Polycast UVT).
  // Ref: Plexiglas UVT datasheet (Röhm GmbH).
  uvTransAcrylic = new G4Material("uvTransAcrylic", 1.19*g/cm3, 3);
  uvTransAcrylic->AddElement(nist->FindOrBuildElement("C"), 5);
  uvTransAcrylic->AddElement(nist->FindOrBuildElement("H"), 8);
  uvTransAcrylic->AddElement(nist->FindOrBuildElement("O"), 2);

  // Wavelengths [nm]: { 530,  425,  400,  340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  G4double rindex[13] = {1.49, 1.49, 1.49, 1.50, 1.51, 1.53, 1.54, 1.545, 1.55, 1.55, 1.55, 1.55, 1.55};
  G4double abslen[13] = {10*m, 5*m, 1*m, 10*cm, 1*cm, 0.1*mm, 0.001*mm, 0.0001*mm,
                         0.0001*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm};

  G4double buf_ri[13], buf_abs[13];
  G4double* p_rindex = resolveArray(fCfg.materials.uvAcrylic.rindex,   1., buf_ri,  rindex);
  G4double* p_abslen = resolveArray(fCfg.materials.uvAcrylic.abslen_m, m,  buf_abs, abslen);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",    energy, p_rindex, 13);
  mpt->AddProperty("ABSLENGTH", energy, p_abslen, 13);
  uvTransAcrylic->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineLArMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();
  larMat = nist->FindOrBuildMaterial("G4_lAr");

  // Wavelengths [nm]: { 530,  425,  400,  340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  // Refractive index of liquid argon:
  //   Ref 1: http://dx.doi.org/10.1016/j.nima.2017.06.031
  //   Ref 2: https://github.com/LArSoft/larg4/.../simpleLArTPC.gdml#L45
  G4double rindex[13]    = {1.23, 1.23, 1.23, 1.23, 1.235, 1.315,
                            1.378, 1.420, 1.45,
                            1.995, 2.904, 3.814, 5.45};
  // Scintillation spectrum (peaks at 128 nm):
  // Ref: https://github.com/LArSoft/larg4/.../simpleLArTPC.gdml#L18
  G4double ffraction[13] = {0., 0., 0., 0., 0., 0.000238409,
                            1.34e-5, 0.01030, 0.0398859,
                            0.03107, 0.00681, 3.73e-4, 0.00422473};
  // Bulk absorption length (very long in pure LAr):
  G4double abslen[13]    = {1000*cm, 1000*cm, 1000*cm, 1000*cm, 1000*cm, 1000*cm,
                            1000*cm, 1000*cm, 1000*cm, 1000*cm, 1000*cm, 1000*cm, 1000*cm};
  // Rayleigh scattering length (~90 cm at 128 nm):
  // Ref: https://github.com/LArSoft/larg4/.../simpleLArTPC.gdml#L21
  G4double rayleigh[13]  = {90*cm, 90*cm, 90*cm, 90*cm, 90*cm, 90*cm,
                            90*cm, 90*cm, 90*cm, 90*cm, 90*cm, 90*cm, 90*cm};

  G4double buf_ri[13], buf_abs[13], buf_ray[13], buf_sc[13];
  G4double* p_rindex    = resolveArray(fCfg.materials.lar.rindex,       1., buf_ri,  rindex);
  G4double* p_abslen    = resolveArray(fCfg.materials.lar.abslen_m,     m,  buf_abs, abslen);
  G4double* p_rayleigh  = resolveArray(fCfg.materials.lar.rayleigh_m,   m,  buf_ray, rayleigh);
  G4double* p_scint     = resolveArray(fCfg.materials.lar.scintcomponent, 1., buf_sc, ffraction);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",                  energy, p_rindex,  13);
  mpt->AddProperty("SCINTILLATIONCOMPONENT1", energy, p_scint,   13);
  mpt->AddProperty("SCINTILLATIONCOMPONENT2", energy, p_scint,   13);
  mpt->AddConstProperty("SCINTILLATIONYIELD",
      fCfg.materials.lar.scintillationyield.value_or(24000.) / MeV);
  mpt->AddConstProperty("SCINTILLATIONYIELD1",
      fCfg.materials.lar.scintillationyield1.value_or(0.75));
  mpt->AddConstProperty("SCINTILLATIONYIELD2",
      fCfg.materials.lar.scintillationyield2.value_or(0.25));
  mpt->AddConstProperty("RESOLUTIONSCALE",
      fCfg.materials.lar.resolutionscale.value_or(1.0));
  mpt->AddConstProperty("SCINTILLATIONTIMECONSTANT1",
      fCfg.materials.lar.scintillationtimeconstant1_ns.value_or(7.) * ns);
  mpt->AddConstProperty("SCINTILLATIONTIMECONSTANT2",
      fCfg.materials.lar.scintillationtimeconstant2_ns.value_or(1400.) * ns);
  mpt->AddProperty("ABSLENGTH", energy, p_abslen,   13);
  mpt->AddProperty("RAYLEIGH",  energy, p_rayleigh, 13);

  larMat->SetMaterialPropertiesTable(mpt);
  larMat->GetIonisation()->SetBirksConstant(0.694*mm/MeV);
}

void MyLightTrapConstruction::DefineGArMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();
  // Argon gas at NIST conditions (1.66 mg/cm3, ~1 atm) — the medium of the
  // bench transmission measurement.
  garMat = nist->FindOrBuildMaterial("G4_Ar");

  // Wavelengths [nm]: { 530, 425, 400, 340, 305, 160, 145, 135, 128, 125, 120, 115, 106 }
  // Refractive index: Bideau-Méhu et al., JQSRT 25 (1981) 395, three-term
  // Sellmeier for Ar at 0 °C / 1 atm (valid 140–568 nm; extrapolated below
  // 140 nm and only indicative at 106 nm, next to the 104.8/106.7 nm resonances).
  G4double rindex[13]   = {1.000283, 1.000286, 1.000287, 1.000291, 1.000295, 1.000357,
                           1.000384, 1.000413, 1.000444, 1.000462, 1.000504, 1.000581, 1.001209};
  // Pure argon gas is transparent above its 106 nm absorption edge; Rayleigh
  // scattering at 1 atm is ~3 orders of magnitude weaker than in the liquid.
  G4double abslen[13]   = {1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m,
                           1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m};
  G4double rayleigh[13] = {1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m,
                           1000*m, 1000*m, 1000*m, 1000*m, 1000*m, 1000*m};

  G4double buf_ri[13], buf_abs[13], buf_ray[13];
  G4double* p_rindex   = resolveArray(fCfg.materials.gar.rindex,     1., buf_ri,  rindex);
  G4double* p_abslen   = resolveArray(fCfg.materials.gar.abslen_m,   m,  buf_abs, abslen);
  G4double* p_rayleigh = resolveArray(fCfg.materials.gar.rayleigh_m, m,  buf_ray, rayleigh);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",    energy, p_rindex,   13);
  mpt->AddProperty("ABSLENGTH", energy, p_abslen,   13);
  mpt->AddProperty("RAYLEIGH",  energy, p_rayleigh, 13);
  garMat->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineMgF2Material()
{
  G4NistManager *nist = G4NistManager::Instance();

  // Magnesium fluoride: VUV-transparent PMT entrance window (cut-off ≈ 110 nm).
  // Only built when pmtWindowThickness > 0.
  // Refractive index (ordinary ray) ref: M. J. Dodge, Appl. Opt. 23, 1980 (1984).
  // Absorption lengths are approximate: transparent from the visible down to
  // ~140 nm, then rolling off steeply towards the 110 nm cut-off.
  mgf2 = nist->FindOrBuildMaterial("G4_MAGNESIUM_FLUORIDE");

  // Wavelengths [nm]: { 530,   425,   400,   340,   305,   160,   145,   135,   128,   125,   120,   115,   106 }
  G4double rindex[13] = {1.379, 1.384, 1.386, 1.392, 1.397, 1.468, 1.490, 1.510, 1.530, 1.540, 1.560, 1.600, 1.650};
  G4double abslen[13] = {1*m, 1*m, 1*m, 1*m, 1*m, 1*m, 0.5*m, 0.2*m, 0.1*m, 0.05*m, 10*mm, 1*mm, 0.001*mm};

  G4double buf_ri[13], buf_abs[13];
  G4double* p_rindex = resolveArray(fCfg.materials.mgf2.rindex,   1., buf_ri,  rindex);
  G4double* p_abslen = resolveArray(fCfg.materials.mgf2.abslen_m, m,  buf_abs, abslen);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",    energy, p_rindex, 13);
  mpt->AddProperty("ABSLENGTH", energy, p_abslen, 13);
  mgf2->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefinePMTBodyMaterials()
{
  G4NistManager *nist = G4NistManager::Instance();

  // PMT interior: vacuum with RINDEX = 1 so optical photons that enter it
  // (e.g. through the faceplate outside the photocathode) keep propagating
  // until they hit the envelope.
  pmtVacuum = nist->FindOrBuildMaterial("G4_Galactic");
  G4double rindex[13] = {1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1., 1.};
  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX", energy, rindex, 13);
  pmtVacuum->SetMaterialPropertiesTable(mpt);

  // PMT envelope (side wall, end cap): borosilicate glass with NO optical
  // properties table.  G4OpBoundaryProcess kills optical photons entering a
  // material without RINDEX, so the envelope is perfectly absorbing — the
  // dynode stack and the opaque tube wall swallow whatever reaches it.
  pmtGlass = nist->FindOrBuildMaterial("G4_Pyrex_Glass");
}

void MyLightTrapConstruction::DefineMaterials()
{
  DefinePTPMaterial();
  DefineUVTransparentAcrylicMaterial();
  DefineLArMaterial();
  DefineGArMaterial();
  DefineMgF2Material();
  DefinePMTBodyMaterials();
  worldMat = garMat;   // default; Construct() re-selects from fWorldMedium
}

// ─────────────────────────────────────────────────────────────────────────────
// Geometry construction
// ─────────────────────────────────────────────────────────────────────────────

G4VPhysicalVolume *MyLightTrapConstruction::Construct()
{
  // ╔═══════════════════════════════════════════════════════════════════════════╗
  // ║  GEOMETRY — PARAMETER SUMMARY                                             ║
  // ║  Tunable via /detector/ messenger; defaults set in the constructor.       ║
  // ║                                                                           ║
  // ║  lighttrapsize         = 15 cm   → square first-layer side in x and y     ║
  // ║  pTPlayerthickness     = 2 µm    → pTP WLS film                           ║
  // ║  uvAcrylicThickness    = 3 mm    → UV-transparent acrylic carrier         ║
  // ║  LArthickness          = 7 mm    → LAr gap: first layer → PMT faceplate   ║
  // ║  pmtDiameter           = 23 mm   → photocathode (sensitive) diameter      ║
  // ║  pmtTubeDiameter       = 28.2 mm → tube / faceplate outer diameter        ║
  // ║  pmtLength             = 92 mm   → faceplate front → end of glass body    ║
  // ║  pmtWindowThickness    = 1.5 mm  → MgF2 faceplate (0 = bare cathode)      ║
  // ║  pmtWallThickness      = 1 mm    → opaque envelope wall / end cap         ║
  // ║                                                                           ║
  // ║  Photon path (VUV beam → PMT):                                            ║
  // ║  LAr ──► pTP film ──► UV acrylic ──► [LAr gap] ──► faceplate ──► cathode  ║
  // ╚═══════════════════════════════════════════════════════════════════════════╝

  // ── World medium selection ──────────────────────────────────────────────────
  // Everything built from worldMat (world box, gap, the optically invisible
  // counters, a bare photocathode) follows this choice.
  if      (fWorldMedium == "gar")    worldMat = garMat;
  else if (fWorldMedium == "lar")    worldMat = larMat;
  else if (fWorldMedium == "vacuum") worldMat = pmtVacuum;
  else {
    G4cerr << "[Construction] Unknown worldMedium '" << fWorldMedium
           << "'; falling back to 'gar'." << G4endl;
    fWorldMedium = "gar";
    worldMat = garMat;
  }
  G4cout << "[Construction] world medium: " << fWorldMedium
         << " (" << worldMat->GetName() << ")" << G4endl;

  // ── Fixed component thicknesses ─────────────────────────────────────────────
  const G4double kGapDetThick   = 0.1*mm;   // first-layer backplane counter slab (world medium)
  const G4double kEdgeDetThick  = 0.1*mm;   // first-layer ±x edge counter LAr slab
  const G4double kPhotocathodeThick = 0.1*mm;   // thin sensitive disc (terminal counter)
  // Standoff between the first-layer back (+z) face and the backplane counter's
  // front face.  A photon TIR-reflected at the back face never crosses this LAr
  // gap, so only photons that actually escape layer 1 are counted (TIR-aware).
  const G4double kFirstLayerBackplaneStandoff = 0.01*mm;

  // ── Derived z-positions ──────────────────────────────────────────────────────
  // Reference: the front (−z) face of the PMT faceplate (or of the bare
  // photocathode if the faceplate is disabled) is at z = 0.  All positions are derived from the messenger
  // parameters — changing any thickness shifts all upstream components.
  const G4double kPMTFrontZ           = 0.;
  // Gap (world medium) between the first-layer back face and the PMT faceplate:
  const G4double kUVAcrylBackZ   = kPMTFrontZ - LArthickness;
  const G4double kUVAcrylCenterZ = kUVAcrylBackZ  - uvAcrylicThickness / 2.;
  const G4double kUVAcrylFrontZ  = kUVAcrylBackZ  - uvAcrylicThickness;
  // pTP film is on the front (LAr-facing) face of the UV acrylic:
  const G4double kPTPCenterZ     = kUVAcrylFrontZ - pTPlayerthickness / 2.;
  // First-layer backplane counter: thin LAr slab in the gap, its front face set
  // kFirstLayerBackplaneStandoff (0.01 mm) behind the acrylic back (+z) face so
  // TIR-reflected photons are not counted — only those that cross the standoff.
  const G4double kGapDetCenterZ  = kUVAcrylBackZ + kFirstLayerBackplaneStandoff
                                                 + kGapDetThick / 2.;
  // First-layer stack (pTP film + UV acrylic) z-extent, used to size the lateral
  // ±x edge counters so they span the full first layer.
  const G4double kFirstLayerThick   = uvAcrylicThickness + pTPlayerthickness;
  const G4double kFirstLayerCenterZ = kUVAcrylBackZ - kFirstLayerThick / 2.;

  // ══ WORLD VOLUME ════════════════════════════════════════════════════════════
  // Box of the selected medium (argon gas by default), 60 % larger than the
  // first layer in x and y; in z it is extended by the PMT length so the whole
  // tube fits behind the first layer, or more if /detector/worldHalfZ asks for
  // it (e.g. to put the beam source farther away).  The beam source MUST lie
  // inside this box: MyPrimaryGenerator aborts otherwise.
  solidWorld = new G4Box("solidWorld",
      lighttrapsize * 0.6, lighttrapsize * 0.6, WorldHalfZ());
  G4cout << "[Construction] world box half-lengths: " << lighttrapsize*0.6/cm << " x "
         << lighttrapsize*0.6/cm << " x " << WorldHalfZ()/cm << " cm (z); sources must be inside" << G4endl;
  logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicWorld");
  physWorld  = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.),
      logicWorld, "physWorld", 0, false, 0, true);

  // ══ SAMPLE: pTP-COATED UV ACRYLIC (skipped when withSample = false) ═════════
  // with_sample=off is the reference run of the transmission measurement: the
  // same beam, gap, PMT and backplane reference-counter plane, but no sample.
  pTPlayer = nullptr;      logicpTPlayer = nullptr;  physpTPlayer = nullptr;
  uvAcrylicSlab = nullptr; logicUVAcrylic = nullptr; physUVAcrylic = nullptr;
  FirstLayerEdgeDet = nullptr; logicFirstLayerEdgeDet = nullptr;
  physFirstLayerEdgeDet_pX = nullptr; physFirstLayerEdgeDet_nX = nullptr;
  if (!fWithSample)
    G4cout << "[Construction] withSample = false: no pTP film / acrylic in the beam "
              "(reference run); beam, PMT and reference-counter plane unchanged." << G4endl;

  if (fWithSample) {
  // ══ FIRST LAYER: pTP WLS FILM ═══════════════════════════════════════════════
  // Thin WLS film deposited on the LAr-facing (−z) front surface of the UV
  // acrylic carrier.  Absorbs incoming 128 nm VUV photons and re-emits at
  // 340–430 nm (near-UV / blue).
  pTPlayer      = new G4Box("pTPlayer",
      lighttrapsize/2., lighttrapsize/2., pTPlayerthickness/2.);
  logicpTPlayer = new G4LogicalVolume(pTPlayer, pTP, "logicpTPlayer");
  physpTPlayer  = new G4PVPlacement(0, G4ThreeVector(0., 0., kPTPCenterZ),
      logicpTPlayer, "physpTPlayer", logicWorld, false, 0, true);

  // ══ FIRST LAYER: UV-TRANSPARENT ACRYLIC CARRIER ═════════════════════════════
  // Mechanical substrate on which the pTP film is deposited.  Transparent at
  // 340–430 nm so pTP-shifted photons propagate through toward the PMT.
  // Also absorbs any residual VUV photons that bypass the pTP film.
  // The LAr gap between this slab and the PMT is implicit (no volume needed;
  // the world LAr fills the space between kUVAcrylBackZ and kPMTFrontZ).
  uvAcrylicSlab  = new G4Box("uvAcrylicSlab",
      lighttrapsize/2., lighttrapsize/2., uvAcrylicThickness/2.);
  logicUVAcrylic = new G4LogicalVolume(uvAcrylicSlab, uvTransAcrylic, "logicUVAcrylic");
  physUVAcrylic  = new G4PVPlacement(0, G4ThreeVector(0., 0., kUVAcrylCenterZ),
      logicUVAcrylic, "physUVAcrylic", logicWorld, false, 0, true);
  } // fWithSample

  // ══ PMT READOUT (Hamamatsu R6836-like cylinder) ════════════════════════════
  // The PMT axis is the z axis; its faceplate front is at z = kPMTFrontZ (0):
  //
  //   z = 0 .. t_win             MgF2 faceplate, full tube diameter
  //   z = t_win .. t_win+0.1 mm  photocathode disc (Ø pmtDiameter) on the inner
  //                              faceplate surface — terminal QE counter
  //   z = t_win .. L - wall      vacuum interior (RINDEX 1), r < R_tube - wall
  //   r = R_tube - wall .. R_tube, z = t_win .. L   opaque glass side wall
  //   z = L - wall .. L          opaque glass end cap
  //
  // The photocathode is made of the same material as the volume in front of
  // it (MgF2 behind the faceplate, LAr if the faceplate is disabled), so its
  // front face adds no optical boundary: every photon reaching it enters and
  // is counted by MyPMTDetector (QE applied there), then killed.  Faceplate
  // light outside the 23 mm photocathode refracts into the vacuum and dies on
  // the envelope.  Dynodes and pins are not modelled.
  PMTWindow = nullptr; logicPMTWindow = nullptr; physPMTWindow = nullptr;
  {
    const G4double rTube   = pmtTubeDiameter / 2.;
    const G4double rInner  = rTube - pmtWallThickness;
    const G4double rCath   = pmtDiameter / 2.;
    const G4double tWin    = pmtWindowThickness;
    const G4double zVacA   = kPMTFrontZ + tWin;                 // vacuum front
    const G4double zVacB   = kPMTFrontZ + pmtLength - pmtWallThickness; // vacuum back = end-cap front
    const G4double halfVac = (zVacB - zVacA) / 2.;

    if (tWin > 0.) {
      PMTWindow      = new G4Tubs("PMTWindow", 0., rTube, tWin/2., 0., 360.*deg);
      logicPMTWindow = new G4LogicalVolume(PMTWindow, mgf2, "logicPMTWindow");
      physPMTWindow  = new G4PVPlacement(0, G4ThreeVector(0., 0., kPMTFrontZ + tWin/2.),
          logicPMTWindow, "physPMTWindow", logicWorld, false, 0, true);
    }

    // Vacuum interior (mother of the photocathode)
    PMTVacuum      = new G4Tubs("PMTVacuum", 0., rInner, halfVac, 0., 360.*deg);
    logicPMTVacuum = new G4LogicalVolume(PMTVacuum, pmtVacuum, "logicPMTVacuum");
    physPMTVacuum  = new G4PVPlacement(0, G4ThreeVector(0., 0., (zVacA + zVacB) / 2.),
        logicPMTVacuum, "physPMTVacuum", logicWorld, false, 0, true);

    // Photocathode disc flush against the inner faceplate surface (local z of
    // the vacuum mother: front face at -halfVac)
    G4Material *cathodeMat = (tWin > 0.) ? mgf2 : worldMat;
    PMTPhotocathode      = new G4Tubs("PMTPhotocathode", 0., rCath, kPhotocathodeThick/2., 0., 360.*deg);
    logicPMTPhotocathode = new G4LogicalVolume(PMTPhotocathode, cathodeMat, "logicPMTPhotocathode");
    physPMTPhotocathode  = new G4PVPlacement(0, G4ThreeVector(0., 0., -halfVac + kPhotocathodeThick/2.),
        logicPMTPhotocathode, "physPMTPhotocathode", logicPMTVacuum, false, 0, true);

    // Opaque glass side wall (hollow tube) and end cap
    PMTEnvelope      = new G4Tubs("PMTEnvelope", rInner, rTube, (pmtLength - tWin)/2., 0., 360.*deg);
    logicPMTEnvelope = new G4LogicalVolume(PMTEnvelope, pmtGlass, "logicPMTEnvelope");
    physPMTEnvelope  = new G4PVPlacement(0, G4ThreeVector(0., 0., kPMTFrontZ + tWin + (pmtLength - tWin)/2.),
        logicPMTEnvelope, "physPMTEnvelope", logicWorld, false, 0, true);

    PMTEndCap      = new G4Tubs("PMTEndCap", 0., rInner, pmtWallThickness/2., 0., 360.*deg);
    logicPMTEndCap = new G4LogicalVolume(PMTEndCap, pmtGlass, "logicPMTEndCap");
    physPMTEndCap  = new G4PVPlacement(0, G4ThreeVector(0., 0., kPMTFrontZ + pmtLength - pmtWallThickness/2.),
        logicPMTEndCap, "physPMTEndCap", logicWorld, false, 0, true);
  }

  // ══ FIRST-LAYER BACKPLANE COUNTER ═══════════════════════════════════════════
  // Thin (0.1 mm) LAr slab in the LAr gap, its front face standing 0.01 mm behind
  // the acrylic back (+z) face (kFirstLayerBackplaneStandoff).  Built from worldMat
  // (LAr) — identical refractive index to the surrounding world, so it introduces
  // no optical boundary (no Fresnel/TIR): it is optically invisible and only
  // *counts* photons that have already escaped the first-layer back face and
  // crossed the standoff — photons TIR-reflected at that face never reach it.
  // Its SD is a pass-through counter (does NOT kill the track), so photons
  // continue on toward the PMT. Records region (b) FirstLayerBackplane (ntuple 4).
  // Built in both with- and without-sample runs: without the sample it is the
  // reference-counter plane at the position of the acrylic back face.
  FirstLayerExitDet      = new G4Box("FirstLayerExitDet",
      lighttrapsize/2., lighttrapsize/2., kGapDetThick/2.);
  logicFirstLayerExitDet = new G4LogicalVolume(
      FirstLayerExitDet, worldMat, "logicFirstLayerExitDet");
  physFirstLayerExitDet  = new G4PVPlacement(0,
      G4ThreeVector(0., 0., kGapDetCenterZ),
      logicFirstLayerExitDet, "physFirstLayerExitDet", logicWorld, false, 0, true);

  // ══ FIRST-LAYER EDGE COUNTERS ═══════════════════════════════════════════════
  // Thin (0.1 mm) LAr slabs flush against the ±x faces of the first-layer stack,
  // spanning y (lighttrapsize) and the full first-layer z-extent.  Like the
  // backplane counter they are worldMat (LAr) — optically invisible, introducing
  // no boundary — and only *count* photons reaching the first layer's lateral
  // edges.  One logical volume placed twice (+x = copy 0, −x = copy 1); the SD is
  // a pass-through counter (killTrack=false) → region (c) FirstLayerEdges.
  // Only built together with the sample.
  if (fWithSample) {
  FirstLayerEdgeDet      = new G4Box("FirstLayerEdgeDet",
      kEdgeDetThick/2., lighttrapsize/2., kFirstLayerThick/2.);
  logicFirstLayerEdgeDet = new G4LogicalVolume(
      FirstLayerEdgeDet, worldMat, "logicFirstLayerEdgeDet");
  physFirstLayerEdgeDet_pX = new G4PVPlacement(0,
      G4ThreeVector(+(lighttrapsize/2. + kEdgeDetThick/2.), 0., kFirstLayerCenterZ),
      logicFirstLayerEdgeDet, "physFirstLayerEdgeDet_pX", logicWorld, false, 0, true);
  physFirstLayerEdgeDet_nX = new G4PVPlacement(0,
      G4ThreeVector(-(lighttrapsize/2. + kEdgeDetThick/2.), 0., kFirstLayerCenterZ),
      logicFirstLayerEdgeDet, "physFirstLayerEdgeDet_nX", logicWorld, false, 1, true);
  } // fWithSample

  // ══ pTP INTERFACE SURFACES ══════════════════════════════════════════════════
  // Both pTP faces (outer LAr-facing, inner acrylic-facing) share one ground/
  // unified optical surface whose facet-slope RMS is pTPsigmaAlpha (radians),
  // configurable via geometry.pTPsigmaAlpha_rad / "/detector/pTPsigmaAlpha".
  //   pTPsigmaAlpha = 0   → perfectly smooth, specular Fresnel (no wiggle).
  //                         Note: a smooth film TIR-traps ~55 % of WLS photons
  //                         in the 2 µm layer; raise sigmaAlpha to model
  //                         evaporated-film roughness / coating waviness so those
  //                         guided modes scatter out (0.1 rad ≈ 6°).
  if (fWithSample) {
    G4OpticalSurface *pTPRoughSurf = new G4OpticalSurface("pTPRoughSurface");
    pTPRoughSurf->SetType(dielectric_dielectric);
    pTPRoughSurf->SetFinish(ground);
    pTPRoughSurf->SetModel(unified);
    pTPRoughSurf->SetSigmaAlpha(pTPsigmaAlpha); // facet-slope RMS [rad]; 0 = smooth

    // pTP ↔ LAr (outer face)
    new G4LogicalBorderSurface("pTP_to_LAr",  physpTPlayer, physWorld,    pTPRoughSurf);
    new G4LogicalBorderSurface("LAr_to_pTP",  physWorld,    physpTPlayer, pTPRoughSurf);
    // pTP ↔ UV acrylic (inner face)
    new G4LogicalBorderSurface("pTP_to_UVac", physpTPlayer, physUVAcrylic, pTPRoughSurf);
    new G4LogicalBorderSurface("UVac_to_pTP", physUVAcrylic, physpTPlayer, pTPRoughSurf);
  }

  // ══ VISUALISATION ATTRIBUTES ════════════════════════════════════════════════
  {
    // World (LAr): invisible wireframe — daughters still shown
    auto *vaWorld = new G4VisAttributes(false);
    logicWorld->SetVisAttributes(vaWorld);

    // pTP WLS film: yellow; UV-transparent acrylic: light blue (sample only)
    auto *vaPTP = new G4VisAttributes(G4Colour(1.0, 1.0, 0.0, 0.8));
    if (logicpTPlayer) logicpTPlayer->SetVisAttributes(vaPTP);
    auto *vaUV = new G4VisAttributes(G4Colour(0.5, 0.8, 1.0, 0.4));
    if (logicUVAcrylic) logicUVAcrylic->SetVisAttributes(vaUV);

    // PMT faceplate: pale grey, transparent; photocathode: dark red;
    // vacuum: invisible; envelope / end cap: grey
    auto *vaPMTWin = new G4VisAttributes(G4Colour(0.9, 0.9, 0.9, 0.3));
    if (logicPMTWindow) logicPMTWindow->SetVisAttributes(vaPMTWin);
    auto *vaPMTCat = new G4VisAttributes(G4Colour(0.7, 0.1, 0.1, 0.9));
    logicPMTPhotocathode->SetVisAttributes(vaPMTCat);
    logicPMTVacuum->SetVisAttributes(new G4VisAttributes(false));
    auto *vaPMTBody = new G4VisAttributes(G4Colour(0.55, 0.55, 0.6, 0.6));
    logicPMTEnvelope->SetVisAttributes(vaPMTBody);
    logicPMTEndCap->SetVisAttributes(vaPMTBody);

    // First-layer backplane counter: cyan, semi-transparent
    auto *vaGap = new G4VisAttributes(G4Colour(0.0, 0.8, 1.0, 0.3));
    logicFirstLayerExitDet->SetVisAttributes(vaGap);

    // First-layer edge counters: orange, semi-transparent
    auto *vaEdge = new G4VisAttributes(G4Colour(1.0, 0.5, 0.0, 0.3));
    if (logicFirstLayerEdgeDet) logicFirstLayerEdgeDet->SetVisAttributes(vaEdge);
  }

  return physWorld;
}

void MyLightTrapConstruction::ConstructSDandField()
{
  // PMT photocathode: terminal counter, flat QE inside [pmtQEmin, pmtQEmax] nm
  // (default 100 % over 110–500 nm) → ntuples 6 (PMTPhotons) / 7 (PMTHits)
  MyPMTDetector *pmtDet = new MyPMTDetector("PMTDetector", pmtQE, pmtQEmin_nm, pmtQEmax_nm);
  logicPMTPhotocathode->SetSensitiveDetector(pmtDet);

  // First-layer backplane counter: pass-through counter (killTrack=false) → ntuple 4.
  // Sits 0.01 mm behind the first-layer back face (TIR-aware); records photons that
  // escaped layer 1 without absorbing them, so they continue on to the PMT.
  MyLeakDetector *gapEntryDet = new MyLeakDetector("FirstLayerBackplaneDetector", 4, false);
  logicFirstLayerExitDet->SetSensitiveDetector(gapEntryDet);

  // First-layer edge counters: pass-through counter (killTrack=false) → ntuple 5.
  // One SD serves both ±x edge placements (set on the shared logical volume).
  if (logicFirstLayerEdgeDet) {
    MyLeakDetector *edgeDet = new MyLeakDetector("FirstLayerEdgeDetector", 5, false);
    logicFirstLayerEdgeDet->SetSensitiveDetector(edgeDet);
  }
}
