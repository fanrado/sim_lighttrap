#include "construction.hh"

MyLightTrapConstruction::MyLightTrapConstruction()
: EVUM(1.239841939*eV)
{
  fMessenger = new G4GenericMessenger(this, "/detector/", "Light Trap Construction");

  fMessenger->DeclareProperty("nSiPMs", nSiPMs, "Number of SiPMs"); // vary number of photosensors
  fMessenger->DeclareProperty("pTPlayerthickness", pTPlayerthickness, "thickness of deposited pTP layer");
  fMessenger->DeclareProperty("pTPsubstratethickness", pTPsubstratethickness, "thickness of pTPsubstrate"); // vary thickness
  fMessenger->DeclareProperty("LArthickness", LArthickness, "thickness of LAr gap");
  fMessenger->DeclareProperty("lighttrapsize", lighttrapsize, "length of a square light trap");

  // define initial value
  nSiPMs = 30;
  pTPlayerthickness = 0.002*mm;
  pTPsubstratethickness = 6*mm;
  LArthickness = 2*mm;
  lighttrapsize = 50*cm;

  G4double tmp[8] = {EVUM/0.53, EVUM/0.425, EVUM/0.4, EVUM/0.34, EVUM/0.305, EVUM/0.16, EVUM/0.128, EVUM/0.106}; //wavelength in microns
  std::copy(tmp, tmp+8, energy);


  DefineMaterials();
}

MyLightTrapConstruction::~MyLightTrapConstruction()
{}

void MyLightTrapConstruction::DefinePTPMaterial() {
  G4NistManager *nist = G4NistManager::Instance();
  pTP = new G4Material("pTP", 1.23*g/cm3, 2);
  pTP->AddElement(nist->FindOrBuildElement("C"), 18);
  pTP->AddElement(nist->FindOrBuildElement("H"), 14);

  acrylicMcMaster = new G4Material("acrylicMcMaster", 1.19*g/cm3, 3);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("C"), 5);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("H"), 8);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("O"), 2);

  bluewlsacrylic = new G4Material("bluewlsacrylic", 1.023*g/cm3, 2); // https://eljentechnology.com/products/wavelength-shifting-plastics/ej-280-ej-282-ej-284-ej-286
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("C"), 9);
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("H"), 10);

  G4double energy[8] = {1.239841939*eV/0.53, 1.239841939*eV/0.425, 1.239841939*eV/0.4, 1.239841939*eV/0.34, 1.239841939*eV/0.305, 1.239841939*eV/0.16, 1.239841939*eV/0.128, 1.239841939*eV/0.106}; //wavelength in microns
  G4double rindexWorld[8] = {1.38, 1.38, 1.38, 1.38, 1.38, 1.38, 1.38, 1.38};
  G4double ffraction[8] = {0., 0., 0., 0., 0., 0.000238409, 0.0398859, 0.00422473};
  G4double LArabsorption[8] = {1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm};
  G4double LArRayleigh[8] = {90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm};

  G4double rindexpTP[8] = {1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65, 1.65}; // refractive index
  G4double AbspTP[8] = {10*m, 10*m, 10*m, 10*m, 0.1*mm, 0.0005*mm, 0.0005*mm, 0.0005*mm}; // absorption length
  G4double EmissionpTP[8] = {0., 0.0005, 0.002, 0.022, 0.0005, 0., 0., 0.}; // relative emission spectrum, unitless

  G4double rindexacrylicMcMaster[8] = {1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5};

  G4double rindexbluewlsacrylic[8] = {1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58};
  G4double Absbluewls[8] = {10*m, 10*m, 1.7*mm, 1*mm, 1.2*mm, 10*m, 10*m, 10*m}; // absorption length
  G4double Emissionbluewls[8] = {0.0005, 0.02, 0., 0., 0., 0., 0., 0.}; // relative emission spectrum, unitless

  G4double reflectivity[8] = {0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98};

  worldMat = nist->FindOrBuildMaterial("G4_lAr"); // other option: G4_lAr
  // worldMat = nist->FindOrBuildMaterial("G4_AIR");
  // 8 wavelengths [nm]: {530, 425, 400, 340, 305, 160, 128, 106}; 
  
  G4MaterialPropertiesTable *mptpTP = new G4MaterialPropertiesTable();
  mptpTP->AddProperty("RINDEX", energy, rindexpTP, 8);
  mptpTP->AddProperty("WLSABSLENGTH", energy, AbspTP, 8);
  mptpTP->AddProperty("WLSCOMPONENT", energy, EmissionpTP, 8);
  mptpTP->AddConstProperty("WLSTIMECONSTANT", 1.136*ns); // Nucl. Instr. Meth. Phys. Res. A 327 (1993) 354.
  pTP->SetMaterialPropertiesTable(mptpTP);
}

void MyLightTrapConstruction::DefineAcrylicMaterial() {
  G4NistManager *nist = G4NistManager::Instance();
  acrylicMcMaster = new G4Material("acrylicMcMaster", 1.19*g/cm3, 3); // https://www.mcmaster.com/8560K224/
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("C"), 5);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("H"), 8);
  acrylicMcMaster->AddElement(nist->FindOrBuildElement("O"), 2);

  // 8 wavelengths [nm]: {530, 425, 400, 340, 305, 160, 128, 106}; 
  G4double rindexacrylicMcMaster[8] = {1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5}; // source: https://indico.fnal.gov/event/63097/contributions/283538/attachments/174977/237339/slides.pdf

  G4MaterialPropertiesTable *mptacrylicMcMaster = new G4MaterialPropertiesTable();
  mptacrylicMcMaster->AddProperty("RINDEX", energy, rindexacrylicMcMaster, 8);
  acrylicMcMaster->SetMaterialPropertiesTable(mptacrylicMcMaster);
}

void MyLightTrapConstruction::DefineBlueWLSMaterial() {
  G4NistManager *nist = G4NistManager::Instance();

  bluewlsacrylic = new G4Material("bluewlsacrylic", 1.023*g/cm3, 2); // https://eljentechnology.com/products/wavelength-shifting-plastics/ej-280-ej-282-ej-284-ej-286
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("C"), 9);
  bluewlsacrylic->AddElement(nist->FindOrBuildElement("H"), 10);

  // 8 wavelengths [nm]: {530, 425, 400, 340, 305, 160, 128, 106}; 
  G4double rindexbluewlsacrylic[8] = {1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58, 1.58}; // source: https://eljentechnology.com/products/wavelength-shifting-plastics/ej-280-ej-282-ej-284-ej-286
  // Absorption length:
  // 200cm @ 430nm (DUNE VD): https://agenda.infn.it/event/37876/contributions/214807/attachments/112678/161089/PhColl_DUNE_IT-1.pdf
  // 400nm -300nm: using result from DUNE HD small XA: https://indico.cern.ch/event/1485254/contributions/6359507/attachments/3013274/5314283/DRD2_250211-4.pdf
  // < 300 nm: guesses, VUV should be strongly absorbed - BUT they shouldn't cause reemission - How to code this????
  // what should we put for 300nm and below??? probably don't matter much since here don't expect much VUV light
  G4double Absbluewls[8] = {200*cm, 200*cm, 0.8*mm, 0.8*mm, 3*mm, 0.0001*mm, 0.0001*mm, 0.0001*mm};
  G4double Emissionbluewls[8] = {0.0005, 0.02, 0., 0., 0., 0., 0., 0.}; // relative emission spectrum, unitless, source: https://iopscience.iop.org/article/10.1088/1748-0221/19/02/C02021

  G4MaterialPropertiesTable *mptbluewlsacrylic = new G4MaterialPropertiesTable();
  mptbluewlsacrylic->AddProperty("RINDEX", energy, rindexbluewlsacrylic, 8);
  mptbluewlsacrylic->AddProperty("WLSABSLENGTH", energy, Absbluewls, 8);
  mptbluewlsacrylic->AddProperty("WLSCOMPONENT", energy, Emissionbluewls, 8);
  mptbluewlsacrylic->AddConstProperty("WLSTIMECONSTANT", 1.26*ns);
  bluewlsacrylic->SetMaterialPropertiesTable(mptbluewlsacrylic);
}

void MyLightTrapConstruction::DefineWorldMaterial() {
  G4NistManager *nist = G4NistManager::Instance();
  worldMat = nist->FindOrBuildMaterial("G4_lAr");

  // 8 wavelengths [nm]: {530, 425, 400, 340, 305, 160, 128, 106}; 
  // LAr rindex:
  // 1) http://dx.doi.org/10.1016/j.nima.2017.06.031
  // 2) https://github.com/LArSoft/larg4/blob/c8505744f4ed2ddcd5c3f30f6ee4a6ef86dbccce/gdml/simpleLArTPC.gdml#L45
  G4double rindexWorld[8] = {1.23, 1.23, 1.23, 1.23, 1.235, 1.315, 1.45, 5.45};
  // cz: need to be sharper at 128 nm? 
  G4double ffraction[8] = {0., 0., 0., 0., 0., 0.000238409, 0.0398859, 0.00422473}; // source: https://github.com/LArSoft/larg4/blob/c8505744f4ed2ddcd5c3f30f6ee4a6ef86dbccce/gdml/simpleLArTPC.gdml#L18
  G4double LArabsorption[8] = {1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm, 1000.*cm}; // outside 106-160nm: guess, 106-160nm: https://github.com/LArSoft/larg4/blob/c8505744f4ed2ddcd5c3f30f6ee4a6ef86dbccce/gdml/simpleLArTPC.gdml#L20C23-L20C35
  G4double LArRayleigh[8] = {90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm, 90.*cm}; // outside 106-160nm: guess, 106-160nm: https://github.com/LArSoft/larg4/blob/c8505744f4ed2ddcd5c3f30f6ee4a6ef86dbccce/gdml/simpleLArTPC.gdml#L21

  G4MaterialPropertiesTable *mptWorld = new G4MaterialPropertiesTable();
  mptWorld->AddProperty("RINDEX", energy, rindexWorld, 8);
  mptWorld->AddProperty("SCINTILLATIONCOMPONENT1", energy, ffraction, 8);
  mptWorld->AddProperty("SCINTILLATIONCOMPONENT2", energy, ffraction, 8);
  mptWorld->AddConstProperty("SCINTILLATIONYIELD", 24000./MeV);
  mptWorld->AddConstProperty("SCINTILLATIONYIELD1", 0.75);
  mptWorld->AddConstProperty("SCINTILLATIONYIELD2", 0.25);
  mptWorld->AddConstProperty("RESOLUTIONSCALE", 1.0); // # of sigma
  mptWorld->AddConstProperty("SCINTILLATIONTIMECONSTANT1", 7.*ns);
  mptWorld->AddConstProperty("SCINTILLATIONTIMECONSTANT2", 1400.*ns);
  mptWorld->AddProperty("ABSLENGTH", energy, LArabsorption, 8);
  mptWorld->AddProperty("RAYLEIGH", energy, LArRayleigh, 8);

  worldMat->SetMaterialPropertiesTable(mptWorld);
  worldMat->GetIonisation()->SetBirksConstant(0.694*mm/MeV);

}

void MyLightTrapConstruction::DefineOpticalSurface() {
  G4double reflectivity[8] = {0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98, 0.98}; // source >98%: https://multimedia.3m.com/mws/media/1245089O/3m-enhanced-specular-reflector-films-3m-esr-tech-data-sheet.pdf

  Vikuiti = new G4OpticalSurface("Vikuiti");
  Vikuiti->SetType(dielectric_metal);
  Vikuiti->SetFinish(ground);
  Vikuiti->SetModel(unified);
  G4MaterialPropertiesTable *mpt3MVikuiti = new G4MaterialPropertiesTable();
  mpt3MVikuiti->AddProperty("REFLECTIVITY", energy, reflectivity, 8);
  Vikuiti->SetMaterialPropertiesTable(mpt3MVikuiti);
}

void MyLightTrapConstruction::DefineMaterials()
{
  DefinePTPMaterial();
  DefineAcrylicMaterial();
  DefineBlueWLSMaterial();
  DefineWorldMaterial();
  DefineOpticalSurface();
}

G4VPhysicalVolume *MyLightTrapConstruction::Construct()
{
  solidWorld = new G4Box("solidWorld", lighttrapsize*.6, lighttrapsize*.6, lighttrapsize*.6);
  logicWorld = new G4LogicalVolume(solidWorld, worldMat, "logicWorld");
  physWorld = new G4PVPlacement(0, G4ThreeVector(0., 0., 0.), logicWorld, "physWorld", 0, false, 0, true);

  pTPlayer =  new G4Box("pTPlayer", lighttrapsize/2., lighttrapsize/2., pTPlayerthickness/2.);
  logicpTPlayer = new G4LogicalVolume(pTPlayer, pTP, "logicpTPlayer");
  physpTPlayer = new G4PVPlacement(0, G4ThreeVector(0., 0., lighttrapsize/2. - pTPsubstratethickness/2. - pTPlayerthickness/2.), logicpTPlayer, "physpTPlayer", logicWorld, false, 0, true);

  pTPsubstrate =  new G4Box("pTPsubstrate", lighttrapsize/2., lighttrapsize/2., pTPsubstratethickness/2.);
  pTPsubstrate =  new G4Box("pTPsubstrate", lighttrapsize/2., lighttrapsize/2., pTPsubstratethickness);
  logicpTPsubstrate = new G4LogicalVolume(pTPsubstrate, acrylicMcMaster, "logicpTPsubstrate");
  physpTPsubstrate = new G4PVPlacement(0, G4ThreeVector(0., 0., lighttrapsize/2.), logicpTPsubstrate, "physpTPsubstrate", logicWorld, false, 0, true);

  // BlueWLSplate =  new G4Box("BlueWLSplate", lighttrapsize/2., lighttrapsize/2., 3*mm);
  // logicBlueWLSplate = new G4LogicalVolume(BlueWLSplate, bluewlsacrylic, "logicBlueWLSplate");
  // physBlueWLSplate = new G4PVPlacement(0, G4ThreeVector(0., 0., lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicBlueWLSplate, "physBlueWLSplate", logicWorld, false, 0, true);

  // // photosensors
  // SiPMs = new G4Box("SiPMs", 3*mm, 0.5*mm, 3*mm);
  // logicSiPMs = new G4LogicalVolume(SiPMs, worldMat, "logicSiPMs");
  // // create an array of sensitive det
  // for (G4int i = 0; i < nSiPMs; i++) {
  //   physSiPMs = new G4PVPlacement(0, G4ThreeVector(-1*lighttrapsize/2. + lighttrapsize/(nSiPMs+1)/2. + i*lighttrapsize/(nSiPMs+1), lighttrapsize/2. + 1*mm, lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicSiPMs, "physSiPMs", logicWorld, false, i, true);
  // }
  // photosensors
  SiPMs = new G4Box("SiPMs", 3*mm, 0.5*mm, 3*mm);
  logicSiPMs = new G4LogicalVolume(SiPMs, worldMat, "logicSiPMs");
  // create an array of sensitive det
  for (G4int i = 0; i < nSiPMs; i++) {
    physSiPMs = new G4PVPlacement(0, G4ThreeVector(-1*lighttrapsize/2. + lighttrapsize/(nSiPMs+1)/2. + i*lighttrapsize/(nSiPMs+1), lighttrapsize/2. + 1*mm, lighttrapsize/2. + 1.5*mm), logicSiPMs, "physSiPMs", logicWorld, false, i, true);
  }

  // apply vikuiti to backplane of first acrylic layer
  ReflectiveFoilBackPlane =  new G4Box("ReflectiveFoilBackPlane", lighttrapsize/2., lighttrapsize/2., 0.065*mm/2);
  logicReflectiveFoilBackPlane = new G4LogicalVolume(ReflectiveFoilBackPlane, acrylicMcMaster, "logicReflectiveFoilBackPlane");
  G4LogicalSkinSurface *skin = new G4LogicalSkinSurface("skin", logicReflectiveFoilBackPlane, Vikuiti);
  physReflectiveFoilBackPlane = new G4PVPlacement(0, G4ThreeVector(0., 0., lighttrapsize/2. + pTPsubstratethickness/2. + 6.033/2.*mm), logicReflectiveFoilBackPlane, "physReflectiveFoilBackPlane", logicWorld, false, 0, true);

  // // apply vikuiti to backplane
  // ReflectiveFoilBackPlane =  new G4Box("ReflectiveFoilBackPlane", lighttrapsize/2., lighttrapsize/2., 0.065*mm/2);
  // logicReflectiveFoilBackPlane = new G4LogicalVolume(ReflectiveFoilBackPlane, acrylicMcMaster, "logicReflectiveFoilBackPlane");
  // G4LogicalSkinSurface *skin = new G4LogicalSkinSurface("skin", logicReflectiveFoilBackPlane, Vikuiti);
  // physReflectiveFoilBackPlane = new G4PVPlacement(0, G4ThreeVector(0., 0., lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 6.033*mm), logicReflectiveFoilBackPlane, "physReflectiveFoilBackPlane", logicWorld, false, 0, true);

  // // apply vikuiti to small edges of bluewlsplate
  // ReflectiveFoilEdgeTop =  new G4Box("ReflectiveFoilEdgeTop", lighttrapsize/2., 0.065*mm/2, 3*mm);
  // ReflectiveFoilEdgeBot =  new G4Box("ReflectiveFoilEdgeBot", lighttrapsize/2., 0.065*mm/2, 3*mm);
  // ReflectiveFoilEdgeLeft  =  new G4Box("ReflectiveFoilEdgeLeft",  0.065*mm/2, lighttrapsize/2., 3*mm);
  // ReflectiveFoilEdgeRight =  new G4Box("ReflectiveFoilEdgeRight", 0.065*mm/2, lighttrapsize/2., 3*mm);

  // logicReflectiveFoilEdgeTop = new G4LogicalVolume(ReflectiveFoilEdgeTop, acrylicMcMaster, "logicReflectiveFoilEdgeTop"); // it's actually polymer, not acrylic, but may be not critical as it's reflective
  // logicReflectiveFoilEdgeBot = new G4LogicalVolume(ReflectiveFoilEdgeBot, acrylicMcMaster, "logicReflectiveFoilEdgeBot");
  // logicReflectiveFoilEdgeLeft  = new G4LogicalVolume(ReflectiveFoilEdgeLeft, acrylicMcMaster, "logicReflectiveFoilEdgeLeft");
  // logicReflectiveFoilEdgeRight = new G4LogicalVolume(ReflectiveFoilEdgeRight, acrylicMcMaster, "logicReflectiveFoilEdgeRight");

  // G4LogicalSkinSurface *skinedgetop = new G4LogicalSkinSurface("skinedgetop", logicReflectiveFoilEdgeTop, Vikuiti);
  // G4LogicalSkinSurface *skinedgebot = new G4LogicalSkinSurface("skinedgebot", logicReflectiveFoilEdgeBot, Vikuiti);
  // G4LogicalSkinSurface *skinedgeleft  = new G4LogicalSkinSurface("skinedgeleft", logicReflectiveFoilEdgeLeft, Vikuiti);
  // G4LogicalSkinSurface *skinedgeright = new G4LogicalSkinSurface("skinedgeright", logicReflectiveFoilEdgeRight, Vikuiti);

  // physReflectiveFoilEdgeTop   = new G4PVPlacement(0, G4ThreeVector(0., lighttrapsize/2. + 1.533*mm, lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicReflectiveFoilEdgeTop, "physReflectiveFoilEdgeTop", logicWorld, false, 0, true);
  // physReflectiveFoilEdgeBot   = new G4PVPlacement(0, G4ThreeVector(0., -(lighttrapsize/2. + 0.033*mm), lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicReflectiveFoilEdgeBot, "physReflectiveFoilEdgeBot", logicWorld, false, 0, true);
  // physReflectiveFoilEdgeLeft  = new G4PVPlacement(0, G4ThreeVector(lighttrapsize/2. + 0.033*mm, 0., lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicReflectiveFoilEdgeLeft, "physReflectiveFoilEdgeLeft", logicWorld, false, 0, true);
  // physReflectiveFoilEdgeRight = new G4PVPlacement(0, G4ThreeVector(-(lighttrapsize/2. + 0.033*mm), 0., lighttrapsize/2. + LArthickness + pTPsubstratethickness/2. + 3*mm), logicReflectiveFoilEdgeRight, "physReflectiveFoilEdgeRight", logicWorld, false, 0, true);


  return physWorld;
}

void MyLightTrapConstruction::ConstructSDandField()
{
  MySensitiveDetector *sensDet = new MySensitiveDetector("SensitiveDetector");
  logicSiPMs->SetSensitiveDetector(sensDet);
}
