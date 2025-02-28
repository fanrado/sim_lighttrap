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

#include "detector.hh"

class MyLightTrapConstruction : public G4VUserDetectorConstruction
{
public:
  MyLightTrapConstruction();
  ~MyLightTrapConstruction();

  virtual G4VPhysicalVolume *Construct();

private:
  virtual void ConstructSDandField();

  G4int nSiPMs;
  G4double pTPlayerthickness;
  G4double pTPsubstratethickness;
  G4double LArthickness;
  G4double lighttrapsize;

  G4Box             *solidWorld, *pTPlayer,      *pTPsubstrate,      *BlueWLSplate,      *SiPMs,      *ReflectiveFoilBackPlane,      *ReflectiveFoilEdgeTop,      *ReflectiveFoilEdgeBot,      *ReflectiveFoilEdgeLeft,      *ReflectiveFoilEdgeRight;
  G4LogicalVolume   *logicWorld, *logicpTPlayer, *logicpTPsubstrate, *logicBlueWLSplate, *logicSiPMs, *logicReflectiveFoilBackPlane, *logicReflectiveFoilEdgeTop, *logicReflectiveFoilEdgeBot, *logicReflectiveFoilEdgeLeft, *logicReflectiveFoilEdgeRight;
  G4VPhysicalVolume *physWorld,  *physpTPlayer,  *physpTPsubstrate,  *physBlueWLSplate,  *physSiPMs,  *physReflectiveFoilBackPlane,  *physReflectiveFoilEdgeTop,  *physReflectiveFoilEdgeBot,  *physReflectiveFoilEdgeLeft,  *physReflectiveFoilEdgeRight;

  G4GenericMessenger *fMessenger;

  G4Material *pTP, *acrylicMcMaster, *bluewlsacrylic,  *worldMat;

  void DefineMaterials();
  void DefinePTPMaterial();
  void DefineAcrylicMaterial();
  void DefineBlueWLSMaterial();
  void DefineWorldMaterial();
  void DefineOpticalSurface();

  G4OpticalSurface *Vikuiti;
  const G4double EVUM; // eV to microns conversion factor 1.239841939*eV
};

#endif
