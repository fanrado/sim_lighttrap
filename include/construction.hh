#ifndef CONSTRUCTION_HH
#define CONSTRUCTION_HH

#include "G4VUserDetectorConstruction.hh"
#include "G4VPhysicalVolume.hh"
#include "G4LogicalVolume.hh"
#include "G4Box.hh"
#include "G4PVPlacement.hh"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4GenericMessenger.hh"
#include "G4OpticalSurface.hh"
#include "G4LogicalSkinSurface.hh"
#include "G4LogicalBorderSurface.hh"

#include "detector.hh"

class MyLightTrapConstruction : public G4VUserDetectorConstruction
{
public:
  MyLightTrapConstruction();
  ~MyLightTrapConstruction();

  virtual G4VPhysicalVolume *Construct();

private:
  virtual void ConstructSDandField();

  // ── Tunable geometry parameters (set via /detector/ messenger or defaults) ──
  G4int    nSiPMs;                // total SiPMs (split equally between ±y edges)
  G4double pTPlayerthickness;     // pTP WLS film thickness           (default 2 µm)
  G4double uvAcrylicThickness;    // UV-transparent acrylic thickness  (default 3 mm)
  G4double pTPsubstratethickness; // blue WLS slab thickness           (default 6 mm)
  G4double LArthickness;          // LAr gap: first layer → blue WLS   (default 3 mm)
  G4double lighttrapsize;         // square module side length         (default 15 cm)

  // ── World ────────────────────────────────────────────────────────────────────
  G4Box             *solidWorld;
  G4LogicalVolume   *logicWorld;
  G4VPhysicalVolume *physWorld;

  // ── First layer: pTP WLS film + UV-transparent acrylic carrier ───────────────
  G4Box             *pTPlayer,      *uvAcrylicSlab;
  G4LogicalVolume   *logicpTPlayer, *logicUVAcrylic;
  G4VPhysicalVolume *physpTPlayer,  *physUVAcrylic;

  // ── Blue WLS substrate ───────────────────────────────────────────────────────
  G4Box             *pTPsubstrate;
  G4LogicalVolume   *logicpTPsubstrate;
  G4VPhysicalVolume *physpTPsubstrate;

  // ── SiPM photosensors (edge-coupled at ±y faces of blue WLS slab) ────────────
  G4Box             *SiPMs;
  G4LogicalVolume   *logicSiPMs;
  G4VPhysicalVolume *physSiPMs;   // pointer reused in placement loop

  // ── Vikuiti reflective foils ─────────────────────────────────────────────────
  // Backplane foil: covers the +z (back) face of the blue WLS slab
  G4Box             *ReflectiveFoilBackPlane;
  G4LogicalVolume   *logicReflectiveFoilBackPlane;
  G4VPhysicalVolume *physReflectiveFoilBackPlane;
  // Lateral foils: cover the ±x faces of the blue WLS slab (the edges without SiPMs)
  G4Box             *VikuitiEdge;
  G4LogicalVolume   *logicVikuitiEdge;
  G4VPhysicalVolume *physVikuitiEdge_pX, *physVikuitiEdge_nX;

  // ── Validation detector: backplane photon-leak counter ───────────────────────
  G4Box             *BackplaneLeakDet;
  G4LogicalVolume   *logicBackplaneLeakDet;
  G4VPhysicalVolume *physBackplaneLeakDet;

  // ── Runtime messenger ────────────────────────────────────────────────────────
  G4GenericMessenger *fMessenger;

  // ── Materials ────────────────────────────────────────────────────────────────
  G4Material *pTP;             // p-terphenyl WLS film (1st WLS stage)
  G4Material *uvTransAcrylic;  // UV-transparent PMMA carrier for pTP film
  G4Material *acrylicMcMaster; // standard PMMA (used for Vikuiti foil body material)
  G4Material *bluewlsacrylic;  // blue-shifting WLS acrylic slab (2nd WLS stage)
  G4Material *worldMat;        // liquid argon (LAr)

  void DefineMaterials();
  void DefinePTPMaterial();
  void DefineUVTransparentAcrylicMaterial();
  void DefineAcrylicMaterial();
  void DefineBlueWLSMaterial();
  void DefineWorldMaterial();
  void DefineOpticalSurface();

  G4OpticalSurface *Vikuiti;
  const G4double EVUM; // hc constant in eV·µm: 1.239841939 eV·µm (wavelength ↔ energy)
  G4double energy[13]; // 13 sampled photon energies covering VUV to visible (115–145 nm densified)
};

#endif
