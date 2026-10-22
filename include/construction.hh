#ifndef CONSTRUCTION_HH
#define CONSTRUCTION_HH

#include "G4VUserDetectorConstruction.hh"
#include "G4VPhysicalVolume.hh"
#include "G4LogicalVolume.hh"
#include "G4Box.hh"
#include "G4Tubs.hh"
#include "G4PVPlacement.hh"
#include "G4NistManager.hh"
#include "G4SystemOfUnits.hh"
#include "G4GenericMessenger.hh"
#include "G4OpticalSurface.hh"
#include "G4LogicalBorderSurface.hh"

#include "detector.hh"
#include "config.hh"

class G4MaterialPropertiesTable;

class MyLightTrapConstruction : public G4VUserDetectorConstruction
{
public:
  explicit MyLightTrapConstruction(const SimConfig& cfg = SimConfig{});
  ~MyLightTrapConstruction();

  virtual G4VPhysicalVolume *Construct();

  // Read-only access for the end-of-run summary
  G4bool   WithSample()      const { return fWithSample; }
  G4String WorldMedium()     const { return fWorldMedium; }
  G4double GapThickness()    const { return LArthickness; }
  G4double WorldHalfZ()      const;   // effective value (auto resolved)
  G4double PMTDiameter()     const { return pmtDiameter; }
  G4double WindowThickness() const { return pmtWindowThickness; }
  G4String PMTQEDescription() const { return fPMTQEDescription; }

private:
  virtual void ConstructSDandField();

  // ── Tunable geometry parameters (set via /detector/ messenger or defaults) ──
  G4bool   fWithSample;           // build the pTP/acrylic sample? (false = reference run)
  G4String fWorldMedium;          // "gar" (argon gas, default) | "lar" | "vacuum"
  G4double pTPlayerthickness;     // pTP WLS film thickness           (default 2 µm)
  G4double uvAcrylicThickness;    // UV-transparent acrylic thickness  (default 3 mm)
  G4double LArthickness;          // LAr gap: first layer → PMT face   (default 7 mm)
  G4double lighttrapsize;         // square first-layer side length    (default 15 cm)
  G4double worldHalfZ;            // world half-length in z; 0 = auto   (default 0)
  G4double pTPsigmaAlpha;         // pTP surface facet-slope RMS [rad]  (default 0 = smooth)
  G4double pmtDiameter;           // PMT photocathode diameter            (default 23 mm)
  G4double pmtTubeDiameter;       // tube / faceplate outer diameter      (default 28.2 mm)
  G4double pmtLength;             // faceplate front → end of glass body  (default 92 mm)
  G4double pmtWindowThickness;    // MgF2 faceplate; 0 = bare cathode     (default 1.5 mm)
  G4double pmtWallThickness;      // opaque envelope wall / end cap       (default 1 mm)
  G4double pmtQE;                 // flat QE inside the band              (default 1.0)
  G4double pmtQEmin_nm;           // QE band lower edge [nm]              (default 110)
  G4double pmtQEmax_nm;           // QE band upper edge [nm]              (default 500)
  G4String fPMTQEFile;            // optional "<wl_nm> <QE>" table; empty = flat band

  // ── World ────────────────────────────────────────────────────────────────────
  G4Box             *solidWorld;
  G4LogicalVolume   *logicWorld;
  G4VPhysicalVolume *physWorld;

  // ── First layer: pTP WLS film + UV-transparent acrylic carrier ───────────────
  G4Box             *pTPlayer,      *uvAcrylicSlab;
  G4LogicalVolume   *logicpTPlayer, *logicUVAcrylic;
  G4VPhysicalVolume *physpTPlayer,  *physUVAcrylic;

  // ── PMT readout: Hamamatsu R6836-like cylinder ───────────────────────────────
  // MgF2 faceplate (full tube diameter) → photocathode disc (pmtDiameter) on its
  // inner face → vacuum interior → opaque glass side wall and end cap.  The
  // photocathode SD is a terminal QE counter.
  G4Tubs            *PMTWindow,      *PMTPhotocathode,      *PMTVacuum,      *PMTEnvelope,      *PMTEndCap;
  G4LogicalVolume   *logicPMTWindow, *logicPMTPhotocathode, *logicPMTVacuum, *logicPMTEnvelope, *logicPMTEndCap;
  G4VPhysicalVolume *physPMTWindow,  *physPMTPhotocathode,  *physPMTVacuum,  *physPMTEnvelope,  *physPMTEndCap;

  // ── First-layer backplane counter: pass-through counter in the LAr gap ───────
  G4Box             *FirstLayerExitDet;
  G4LogicalVolume   *logicFirstLayerExitDet;
  G4VPhysicalVolume *physFirstLayerExitDet;

  // ── First-layer edge counters: pass-through counters on the ±x faces of the
  //    first-layer (pTP/UV-acrylic) stack. One logical volume placed twice. ─────
  G4Box             *FirstLayerEdgeDet;
  G4LogicalVolume   *logicFirstLayerEdgeDet;
  G4VPhysicalVolume *physFirstLayerEdgeDet_pX, *physFirstLayerEdgeDet_nX;

  // ── Runtime messenger ────────────────────────────────────────────────────────
  G4GenericMessenger *fMessenger;
  G4String fPMTQEDescription;     // filled in ConstructSDandField for the run summary

  // ── Config snapshot (set at construction, used by DefineMaterials) ───────────
  SimConfig fCfg;

  // ── Materials ────────────────────────────────────────────────────────────────
  G4Material *pTP;             // p-terphenyl WLS film (VUV → 340–430 nm)
  G4Material *uvTransAcrylic;  // UV-transparent PMMA carrier for pTP film
  G4Material *worldMat;        // selected world medium (points to one of the three below)
  G4Material *larMat;          // liquid argon (G4_lAr + optical/scintillation properties)
  G4Material *garMat;          // argon gas, 1 atm (G4_Ar + optical properties)
  G4Material *mgf2;            // magnesium fluoride — VUV-transparent PMT window
  G4Material *pmtVacuum;       // PMT interior (G4_Galactic, RINDEX = 1)
  G4Material *pmtGlass;        // PMT envelope (borosilicate, no optical properties → opaque)

  void DefineMaterials();
  void DefinePTPMaterial();
  void DefineUVTransparentAcrylicMaterial();
  void DefineLArMaterial();
  void DefineGArMaterial();
  void DefineMgF2Material();
  void DefinePMTBodyMaterials();

  const G4double EVUM; // hc constant in eV·µm: 1.239841939 eV·µm (wavelength ↔ energy)
  G4double energy[13]; // 13 sampled photon energies covering VUV to visible (115–145 nm densified)

  // Returns buf (filled from cfg * unitFactor) if cfg is non-empty, else returns fallback.
  static G4double* resolveArray(const std::vector<double>& cfg, double unitFactor,
                                G4double (&buf)[13], G4double* fallback);

  // Adds "WLSCOMPONENT" to mpt with precedence:
  //   1. file spectrum   (fileWl [nm] / fileInt, arbitrary # of points)
  //   2. inline 13-point (inline13, on the shared `energy` grid)
  //   3. built-in smooth asymmetric Gaussian (peak / sigBlue / sigRed [nm]) on a
  //      dedicated fine grid spanning [lamMin, lamMax] nm.
  void addWLSEmission(G4MaterialPropertiesTable* mpt,
                      const std::vector<double>& fileWl,
                      const std::vector<double>& fileInt,
                      const std::vector<double>& inline13,
                      G4double peak, G4double sigBlue, G4double sigRed,
                      G4double lamMin, G4double lamMax);
};

#endif
