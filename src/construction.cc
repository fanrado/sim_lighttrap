#include "construction.hh"
#include "G4VisAttributes.hh"
#include "G4Colour.hh"

// ─────────────────────────────────────────────────────────────────────────────
// MyLightTrapConstruction
//
// Builds the LightTrap detector module immersed in liquid argon (LAr).
//
// Module structure (photons travel in +z direction):
//
//   [LAr world] ──► pTP film (2 µm)   ← 1st WLS: 128 nm VUV → 340–430 nm
//                   UV acrylic (3 mm)  ← mechanical carrier, UV-transparent
//                   [3 mm LAr gap]
//                   Blue WLS slab (15 cm × 15 cm × 6 mm) ← 2nd WLS: → ~430 nm
//                     SiPMs at ±y edges (15 per side, 6 mm × 6 mm face)
//                     Vikuiti foils at ±x edges (lateral reflectors)
//                   Vikuiti foil (backplane, +z face)
//                   Backplane leak detector (validation, 100 % efficiency)
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
  fMessenger->DeclareProperty("nSiPMs",
      nSiPMs,               "Total SiPMs (split equally across ±y edges)");
  fMessenger->DeclareProperty("pTPlayerthickness",
      pTPlayerthickness,    "pTP WLS film thickness [default 2 µm]");
  fMessenger->DeclareProperty("uvAcrylicThick",
      uvAcrylicThickness,   "UV-transparent acrylic carrier thickness [default 3 mm]");
  fMessenger->DeclareProperty("pTPsubstratethickness",
      pTPsubstratethickness,"Blue WLS slab thickness [default 6 mm]");
  fMessenger->DeclareProperty("LArthickness",
      LArthickness,         "LAr gap between first layer and blue WLS [default 3 mm]");
  fMessenger->DeclareProperty("lighttrapsize",
      lighttrapsize,        "Square module side length [default 15 cm]");

  // ── Default geometry parameters ─────────────────────────────────────────────
  nSiPMs                = 30;       // 15 per ±y edge
  pTPlayerthickness     = 0.002*mm; // 2 µm pTP film
  uvAcrylicThickness    = 3.*mm;    // 3 mm UV-transparent acrylic carrier
  pTPsubstratethickness = 6.*mm;    // 6 mm blue WLS acrylic slab
  LArthickness          = 3.*mm;    // 3 mm LAr gap between first layer and blue WLS
  lighttrapsize         = 15.*cm;   // 15 cm × 15 cm module (real detector size)

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

// ─────────────────────────────────────────────────────────────────────────────
// Material definitions
// ─────────────────────────────────────────────────────────────────────────────

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
  G4double abslen[13]   = {10*m, 10*m, 10*m, 10*m, 0.1*mm, 0.0005*mm, 0.0005*mm, 0.0005*mm,
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
  mpt->AddProperty("WLSCOMPONENT", energy, p_emission, 13);
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

void MyLightTrapConstruction::DefineAcrylicMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();

  // Standard optical-grade PMMA (McMaster-Carr #8560K224), Vikuiti foil body material.
  // Ref: https://www.mcmaster.com/8560K224/
  acrylicMcMaster = new G4Material("acrylicMcMaster", 1.19*g/cm3, 3);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("C"), 5);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("H"), 8);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("O"), 2);

  // Wavelengths [nm]: { 530,  425,  400,  340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  G4double rindex[13] = {1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50, 1.50};

  G4double buf_ri[13];
  G4double* p_rindex = resolveArray(fCfg.materials.acrylicMcMaster.rindex, 1., buf_ri, rindex);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX", energy, p_rindex, 13);
  acrylicMcMaster->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineBlueWLSMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();

  // Blue-shifting WLS acrylic (EJ-280/282/284/286 type), second WLS stage.
  // Ref: https://eljentechnology.com/products/wavelength-shifting-plastics/ej-280-ej-282-ej-284-ej-286
  bluewlsacrylic = new G4Material("bluewlsacrylic", 1.023*g/cm3, 2);
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("C"), 9);
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("H"), 10);

  // Wavelengths [nm]: {  530,   425,   400,   340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  G4double rindex[13]   = {1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58};
  G4double abslen[13]   = {200*cm, 200*cm, 0.8*mm, 0.8*mm, 3*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm,
                           0.0001*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm};
  G4double emission[13] = {0.0005, 0.02, 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.};

  G4double buf_ri[13], buf_abs[13], buf_em[13];
  G4double* p_rindex   = resolveArray(fCfg.materials.blueWLS.rindex,      1., buf_ri,  rindex);
  G4double* p_wlsabs   = resolveArray(fCfg.materials.blueWLS.wlsabslen_m, m,  buf_abs, abslen);
  G4double* p_emission = resolveArray(fCfg.materials.blueWLS.wlscomponent, 1., buf_em, emission);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("RINDEX",       energy, p_rindex,   13);
  mpt->AddProperty("WLSABSLENGTH", energy, p_wlsabs,   13);
  mpt->AddProperty("WLSCOMPONENT", energy, p_emission, 13);
  mpt->AddConstProperty("WLSTIMECONSTANT",
      fCfg.materials.blueWLS.wlstimeconstant_ns.value_or(1.26) * ns);
  bluewlsacrylic->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineWorldMaterial()
{
  G4NistManager *nist = G4NistManager::Instance();
  worldMat = nist->FindOrBuildMaterial("G4_lAr");

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

  worldMat->SetMaterialPropertiesTable(mpt);
  worldMat->GetIonisation()->SetBirksConstant(0.694*mm/MeV);
}

void MyLightTrapConstruction::DefineOpticalSurface()
{
  // 3M Enhanced Specular Reflector (Vikuiti / ESR): ≥98 % specular reflectivity.
  // Ref: https://multimedia.3m.com/mws/media/1245089O/3m-enhanced-specular-reflector-films-3m-esr-tech-data-sheet.pdf

  // Wavelengths [nm]: { 530,  425,  400,  340,  305,  160,  145,  135,  128,  125,  120,  115,  106 }
  G4double reflectivity[13] = {0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98};

  G4double buf_refl[13];
  G4double* p_refl = resolveArray(fCfg.materials.vikuiti.reflectivity, 1., buf_refl, reflectivity);

  Vikuiti = new G4OpticalSurface("Vikuiti");
  Vikuiti->SetType(dielectric_metal);
  Vikuiti->SetFinish(ground);
  Vikuiti->SetModel(unified);

  G4MaterialPropertiesTable *mpt = new G4MaterialPropertiesTable();
  mpt->AddProperty("REFLECTIVITY", energy, p_refl, 13);
  Vikuiti->SetMaterialPropertiesTable(mpt);
}

void MyLightTrapConstruction::DefineMaterials()
{
  DefinePTPMaterial();
  DefineUVTransparentAcrylicMaterial();
  DefineAcrylicMaterial();
  DefineBlueWLSMaterial();
  DefineWorldMaterial();
  DefineOpticalSurface();
}

// ─────────────────────────────────────────────────────────────────────────────
// Geometry construction
// ─────────────────────────────────────────────────────────────────────────────

G4VPhysicalVolume *MyLightTrapConstruction::Construct()
{
  // ╔═══════════════════════════════════════════════════════════════════════════╗
  // ║  MODULE GEOMETRY — PARAMETER SUMMARY                                     ║
  // ║  Tunable via /detector/ messenger; defaults set in the constructor.      ║
  // ║                                                                          ║
  // ║  lighttrapsize         = 15 cm   → square module side in x and y        ║
  // ║  pTPlayerthickness     = 2 µm    → pTP WLS film (1st WLS stage)         ║
  // ║  uvAcrylicThickness    = 3 mm    → UV-transparent acrylic carrier       ║
  // ║  LArthickness          = 3 mm    → LAr gap: first layer → blue WLS      ║
  // ║  pTPsubstratethickness = 6 mm    → blue WLS acrylic slab (2nd WLS)      ║
  // ║  nSiPMs                = 30      → 15 per ±y edge                       ║
  // ║                                                                          ║
  // ║  Photon path (VUV → SiPMs):                                             ║
  // ║  LAr ──► pTP film ──► UV acrylic ──► [LAr gap] ──► blue WLS ──► SiPMs  ║
  // ║                                                 Vikuiti backplane (+z)  ║
  // ║                                                 Vikuiti edge foils (±x) ║
  // ╚═══════════════════════════════════════════════════════════════════════════╝

  // ── Fixed component thicknesses ─────────────────────────────────────────────
  const G4double kVikuitiThick  = 0.065*mm; // 3M Vikuiti ESR foil
  const G4double kLeakDetThick  = 0.1*mm;   // backplane leak-detector LAr slab

  // ── SiPM dimensions ─────────────────────────────────────────────────────────
  // Each SiPM presents a 6 mm × 6 mm face against the ±y edge of the blue WLS
  // slab.  The 1 mm depth (kSiPMDepthHalf × 2) extends outward in ±y.
  const G4double kSiPMFaceHalf  = 3.*mm;                       // ½ of 6 mm face (x and z)
  const G4double kSiPMDepthHalf = 0.5*mm;                      // ½ of 1 mm depth (y)
  const G4double kSiPMZHalf     = pTPsubstratethickness / 2.;  // spans full slab thickness

  // ── Derived z-positions ──────────────────────────────────────────────────────
  // Reference: the back (+z) face of the blue WLS slab is at z = 0.
  // All positions are derived from the messenger parameters — changing any
  // thickness automatically shifts all downstream components correctly.
  const G4double kBlueWLSBackZ   = 0.;
  const G4double kBlueWLSCenterZ = kBlueWLSBackZ  - pTPsubstratethickness / 2.;
  const G4double kBlueWLSFrontZ  = kBlueWLSBackZ  - pTPsubstratethickness;
  // LAr gap sits between the first layer back face and the blue WLS front face:
  const G4double kUVAcrylBackZ   = kBlueWLSFrontZ - LArthickness;
  const G4double kUVAcrylCenterZ = kUVAcrylBackZ  - uvAcrylicThickness / 2.;
  const G4double kUVAcrylFrontZ  = kUVAcrylBackZ  - uvAcrylicThickness;
  // pTP film is on the front (LAr-facing) face of the UV acrylic:
  const G4double kPTPCenterZ     = kUVAcrylFrontZ - pTPlayerthickness / 2.;
  // Vikuiti backplane foil flush against the +z face of the blue WLS slab:
  const G4double kVikuitiCenterZ = kBlueWLSBackZ  + kVikuitiThick / 2.;
  // Backplane leak detector immediately behind the Vikuiti foil:
  const G4double kLeakDetCenterZ = kBlueWLSBackZ  + kVikuitiThick + kLeakDetThick / 2.;

  // ══ WORLD VOLUME ════════════════════════════════════════════════════════════
  // Liquid argon box, 60 % larger than the module on each side.
  // LAr is both the scintillating medium and the propagation medium for photons
  // between the source and the detector module.
  solidWorld = new G4Box("solidWorld",
      lighttrapsize * 0.6, lighttrapsize * 0.6, lighttrapsize * 0.6);
  logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicWorld");
  physWorld  = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.),
      logicWorld, "physWorld", 0, false, 0, true);

  // ══ FIRST LAYER: pTP WLS FILM ═══════════════════════════════════════════════
  // Thin WLS film deposited on the LAr-facing (−z) front surface of the UV
  // acrylic carrier.  Absorbs incoming 128 nm VUV photons and re-emits at
  // 340–430 nm (near-UV / blue), initiating the two-stage WLS chain.
  pTPlayer      = new G4Box("pTPlayer",
      lighttrapsize/2., lighttrapsize/2., pTPlayerthickness/2.);
  logicpTPlayer = new G4LogicalVolume(pTPlayer, pTP, "logicpTPlayer");
  physpTPlayer  = new G4PVPlacement(0, G4ThreeVector(0., 0., kPTPCenterZ),
      logicpTPlayer, "physpTPlayer", logicWorld, false, 0, true);

  // ══ FIRST LAYER: UV-TRANSPARENT ACRYLIC CARRIER ═════════════════════════════
  // Mechanical substrate on which the pTP film is deposited.  Transparent at
  // 340–430 nm so pTP-shifted photons propagate through toward the blue WLS
  // slab.  Also absorbs any residual VUV photons that bypass the pTP film.
  // The 3 mm LAr gap between this slab and the blue WLS is implicit (no volume
  // needed; the world LAr fills the space between kUVAcrylBackZ and kBlueWLSFrontZ).
  uvAcrylicSlab  = new G4Box("uvAcrylicSlab",
      lighttrapsize/2., lighttrapsize/2., uvAcrylicThickness/2.);
  logicUVAcrylic = new G4LogicalVolume(uvAcrylicSlab, uvTransAcrylic, "logicUVAcrylic");
  physUVAcrylic  = new G4PVPlacement(0, G4ThreeVector(0., 0., kUVAcrylCenterZ),
      logicUVAcrylic, "physUVAcrylic", logicWorld, false, 0, true);

  // ══ BLUE WLS SUBSTRATE ════════════════════════════════════════════════════
  // Second WLS stage: absorbs 340–430 nm photons (from pTP) and re-emits at
  // ~430 nm (blue), well-matched to SiPM peak PDE.
  // Photons propagate inside the slab by WLS re-emission and total internal
  // reflection until they exit through one of the ±y edge faces toward SiPMs.
  // The ±x edge faces are covered by Vikuiti foils (lateral reflectors, below).
  // The +z (back) face is covered by a Vikuiti backplane foil (below).
  pTPsubstrate      = new G4Box("pTPsubstrate",
      lighttrapsize/2., lighttrapsize/2., pTPsubstratethickness/2.);
  logicpTPsubstrate = new G4LogicalVolume(pTPsubstrate, bluewlsacrylic, "logicpTPsubstrate");
  physpTPsubstrate  = new G4PVPlacement(0, G4ThreeVector(0., 0., kBlueWLSCenterZ),
      logicpTPsubstrate, "physpTPsubstrate", logicWorld, false, 0, true);

  // ══ SIPM ARRAY (±y edge coupling) ══════════════════════════════════════════
  // 30 SiPMs total, split equally between the +y and −y edges of the blue WLS
  // slab (15 per edge).  Each SiPM presents a 6 mm × 6 mm sensitive face
  // directly against the slab edge; its 1 mm depth extends outward in ±y.
  //
  // The SiPM z half-size equals the blue WLS half-thickness so each SiPM face
  // spans the full edge area of the slab.
  //
  // Copy number assignment:
  //   0  to nPerEdge−1   → +y edge
  //   nPerEdge to nSiPMs−1 → −y edge
  {
    const G4int    nPerEdge = nSiPMs / 2;
    const G4double pitchX   = lighttrapsize / nPerEdge;          // uniform x-spacing
    const G4double edgeY    = lighttrapsize/2. + kSiPMDepthHalf; // face flush to slab edge

    SiPMs      = new G4Box("SiPMs", kSiPMFaceHalf, kSiPMDepthHalf, kSiPMZHalf);
    logicSiPMs = new G4LogicalVolume(SiPMs, worldMat, "logicSiPMs");

    for (G4int i = 0; i < nPerEdge; i++) {
      G4double xPos = -lighttrapsize/2. + pitchX * (i + 0.5); // centre of SiPM i in x

      // +y edge: face normal points in −y (toward slab)
      new G4PVPlacement(0, G4ThreeVector(xPos, +edgeY, kBlueWLSCenterZ),
          logicSiPMs, "physSiPMs", logicWorld, false, i, true);

      // −y edge: face normal points in +y (toward slab)
      new G4PVPlacement(0, G4ThreeVector(xPos, -edgeY, kBlueWLSCenterZ),
          logicSiPMs, "physSiPMs", logicWorld, false, nPerEdge + i, true);
    }
  }

  // ══ VIKUITI FOIL — BACKPLANE (+z face of blue WLS) ══════════════════════════
  // 3M ESR foil on the back face of the blue WLS slab.
  // Reflects ~98 % of photons back toward the SiPM edges; ~2 % transmitted
  // (monitored by the backplane leak detector below).
  ReflectiveFoilBackPlane      = new G4Box("ReflectiveFoilBackPlane",
      lighttrapsize/2., lighttrapsize/2., kVikuitiThick/2.);
  logicReflectiveFoilBackPlane = new G4LogicalVolume(
      ReflectiveFoilBackPlane, acrylicMcMaster, "logicReflectiveFoilBackPlane");
  new G4LogicalSkinSurface("skinBackplane", logicReflectiveFoilBackPlane, Vikuiti);
  physReflectiveFoilBackPlane  = new G4PVPlacement(0,
      G4ThreeVector(0., 0., kVikuitiCenterZ),
      logicReflectiveFoilBackPlane, "physReflectiveFoilBackPlane",
      logicWorld, false, 0, true);

  // ══ VIKUITI FOILS — LATERAL EDGES (±x faces of blue WLS) ════════════════════
  // Two foils covering the ±x faces of the blue WLS slab — the two edges that
  // have no SiPMs.  They reflect photons trying to escape laterally in x and
  // redirect them back toward the SiPM edges, improving light collection.
  // Each foil face area = lighttrapsize (y) × pTPsubstratethickness (z).
  VikuitiEdge      = new G4Box("VikuitiEdge",
      kVikuitiThick/2., lighttrapsize/2., pTPsubstratethickness/2.);
  logicVikuitiEdge = new G4LogicalVolume(VikuitiEdge, acrylicMcMaster, "logicVikuitiEdge");
  new G4LogicalSkinSurface("skinEdge", logicVikuitiEdge, Vikuiti);

  // +x lateral edge foil
  physVikuitiEdge_pX = new G4PVPlacement(0,
      G4ThreeVector(+(lighttrapsize/2. + kVikuitiThick/2.), 0., kBlueWLSCenterZ),
      logicVikuitiEdge, "physVikuitiEdge_pX", logicWorld, false, 0, true);
  // −x lateral edge foil
  physVikuitiEdge_nX = new G4PVPlacement(0,
      G4ThreeVector(-(lighttrapsize/2. + kVikuitiThick/2.), 0., kBlueWLSCenterZ),
      logicVikuitiEdge, "physVikuitiEdge_nX", logicWorld, false, 1, true);

  // ══ BACKPLANE LEAK DETECTOR ═════════════════════════════════════════════════
  // Thin (0.1 mm) LAr slab immediately behind the Vikuiti backplane foil.
  // 100 %-efficient optical counter: records every photon transmitted through
  // the backplane (~2 % of those hitting it).  Used for optical validation only.
  BackplaneLeakDet      = new G4Box("BackplaneLeakDet",
      lighttrapsize/2., lighttrapsize/2., kLeakDetThick/2.);
  logicBackplaneLeakDet = new G4LogicalVolume(
      BackplaneLeakDet, worldMat, "logicBackplaneLeakDet");
  physBackplaneLeakDet  = new G4PVPlacement(0,
      G4ThreeVector(0., 0., kLeakDetCenterZ),
      logicBackplaneLeakDet, "physBackplaneLeakDet", logicWorld, false, 0, true);

  // ══ pTP INTERFACE SURFACES ══════════════════════════════════════════════════
  // The pTP film is vacuum-evaporated, so both its outer (LAr-facing) and inner
  // (acrylic-facing) surfaces have nanometre-scale roughness.  Without a surface
  // defined here Geant4 uses perfectly smooth Fresnel boundaries, which TIR-traps
  // ~55 % of WLS-emitted photons forever in the 2 µm film.  A ground/unified
  // surface with sigmaAlpha = 0.1 rad (≈ 6°) scatters those guided modes so they
  // can escape within a few bounces — physically motivated by evaporated-film
  // surface roughness measured at 10–100 nm RMS.
  {
    G4OpticalSurface *pTPRoughSurf = new G4OpticalSurface("pTPRoughSurface");
    pTPRoughSurf->SetType(dielectric_dielectric);
    pTPRoughSurf->SetFinish(ground);
    pTPRoughSurf->SetModel(unified);
    pTPRoughSurf->SetSigmaAlpha(0.1); // radians

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

    // pTP WLS film: yellow
    auto *vaPTP = new G4VisAttributes(G4Colour(1.0, 1.0, 0.0, 0.8));
    logicpTPlayer->SetVisAttributes(vaPTP);

    // UV-transparent acrylic: light blue, semi-transparent
    auto *vaUV = new G4VisAttributes(G4Colour(0.5, 0.8, 1.0, 0.4));
    logicUVAcrylic->SetVisAttributes(vaUV);

    // Blue WLS slab: blue, semi-transparent
    auto *vaWLS = new G4VisAttributes(G4Colour(0.1, 0.3, 1.0, 0.5));
    logicpTPsubstrate->SetVisAttributes(vaWLS);

    // SiPMs: green
    auto *vaSiPM = new G4VisAttributes(G4Colour(0.0, 0.8, 0.2, 0.9));
    logicSiPMs->SetVisAttributes(vaSiPM);

    // Vikuiti foils: silver/grey
    auto *vaVikuiti = new G4VisAttributes(G4Colour(0.8, 0.8, 0.8, 0.9));
    logicReflectiveFoilBackPlane->SetVisAttributes(vaVikuiti);
    logicVikuitiEdge->SetVisAttributes(vaVikuiti);

    // Leak detector: magenta, semi-transparent
    auto *vaLeak = new G4VisAttributes(G4Colour(1.0, 0.0, 1.0, 0.3));
    logicBackplaneLeakDet->SetVisAttributes(vaLeak);
  }

  return physWorld;
}

void MyLightTrapConstruction::ConstructSDandField()
{
  // SiPM array: applies Broadcom PDE table (pde_broadcom.dat) per photon
  MySensitiveDetector *sensDet = new MySensitiveDetector("SensitiveDetector");
  logicSiPMs->SetSensitiveDetector(sensDet);

  // Backplane leak detector: 100 %-efficiency counter → ntuple 6
  MyLeakDetector *backplaneDet = new MyLeakDetector("BackplaneLeakDetector", 6);
  logicBackplaneLeakDet->SetSensitiveDetector(backplaneDet);
}
