#include "detector.hh"
#include "counters.hh"
#include <algorithm>
#include <fstream>
#include <sstream>


// ---------------------------------------------------------------------------
MyLeakDetector::MyLeakDetector(G4String name, G4int ntupleID, G4bool killTrack)
  : G4VSensitiveDetector(name), fNtupleID(ntupleID), fKillTrack(killTrack)
{}

MyLeakDetector::~MyLeakDetector()
{}

G4bool MyLeakDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *)
{
  G4Track *track = aStep->GetTrack();
  // Terminal counters kill the photon; pass-through counters let it continue
  // downstream (so the first-layer exit counter does not absorb the light).
  if (fKillTrack)
    track->SetTrackStatus(fStopAndKill);

  G4StepPoint *preStepPoint = aStep->GetPreStepPoint();
  G4ThreeVector pos  = preStepPoint->GetPosition();
  G4double      time = preStepPoint->GetGlobalTime();
  G4ThreeVector mom  = preStepPoint->GetMomentum();
  G4double      wl   = (1.239841939*eV / mom.mag()) * 1E+03;
  // Direction cosine along +z: >0 = travelling forward (into the gap / toward the
  // blue slab), <0 = back-reflected.  Lets analysis separate the two.
  G4double      cosTheta = mom.unit().z();
  // Explicit forward flag for trivial, self-documenting selection in analysis:
  // 1 = forward (out of layer 1, mom.z()>0), 0 = backward (reflected back toward the source).
  // Both directions are recorded — this only tags them.
  G4int         forward  = (mom.z() > 0.) ? 1 : 0;

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  man->FillNtupleIColumn(fNtupleID, 0, evt);
  man->FillNtupleDColumn(fNtupleID, 1, pos.x());
  man->FillNtupleDColumn(fNtupleID, 2, pos.y());
  man->FillNtupleDColumn(fNtupleID, 3, pos.z());
  man->FillNtupleDColumn(fNtupleID, 4, time);
  man->FillNtupleDColumn(fNtupleID, 5, wl);
  man->FillNtupleDColumn(fNtupleID, 6, cosTheta);
  man->FillNtupleIColumn(fNtupleID, 7, forward);
  man->AddNtupleRow(fNtupleID);

  if (fNtupleID == 4) { if (forward) ++RunCounters::Instance().nLayer1Forward; }
  else if (fNtupleID == 5) ++RunCounters::Instance().nLayer1Edges;

  return true;
}

// ---------------------------------------------------------------------------
MyPMTDetector::MyPMTDetector(G4String name, G4double qe, G4double wlMin_nm, G4double wlMax_nm,
                             const G4String& qeFile)
  : G4VSensitiveDetector(name), fQE(qe), fWlMin(wlMin_nm), fWlMax(wlMax_nm), fQEFile(qeFile)
{
  if (!fQEFile.empty()) {
    if (!LoadQETable(fQEFile, fTableWl, fTableQE)) {
      G4Exception("MyPMTDetector::MyPMTDetector", "PMTQEFile", FatalException,
                  ("cannot read the PMT QE table '" + fQEFile +
                   "' (expected >= 2 rows of '<wavelength_nm> <QE>')").c_str());
    }
  }
  G4cout << "[MyPMTDetector] " << name << ": " << Description() << G4endl;
}

MyPMTDetector::~MyPMTDetector()
{}

G4bool MyPMTDetector::LoadQETable(const G4String& path, std::vector<double>& wl, std::vector<double>& qe)
{
  std::ifstream in(path);
  if (!in) return false;
  std::vector<std::pair<double,double>> rows;
  std::string line;
  while (std::getline(in, line)) {
    auto h = line.find('#');
    if (h != std::string::npos) line.erase(h);
    std::istringstream ss(line);
    double w, v;
    if (ss >> w >> v) rows.emplace_back(w, v);
  }
  if (rows.size() < 2) return false;
  std::sort(rows.begin(), rows.end());
  // values above 1 mean the table is in percent
  double vmax = 0.;
  for (const auto& r : rows) vmax = std::max(vmax, r.second);
  const double scale = (vmax > 1.0) ? 0.01 : 1.0;
  wl.clear(); qe.clear();
  for (const auto& r : rows) {
    if (!wl.empty() && r.first <= wl.back()) continue;   // drop duplicate wavelengths
    wl.push_back(r.first);
    qe.push_back(std::min(std::max(r.second * scale, 0.0), 1.0));
  }
  return wl.size() >= 2;
}

G4double MyPMTDetector::Efficiency(G4double wl_nm) const
{
  if (!fTableWl.empty()) {
    if (wl_nm < fTableWl.front() || wl_nm > fTableWl.back()) return 0.;
    auto it = std::upper_bound(fTableWl.begin(), fTableWl.end(), wl_nm);
    if (it == fTableWl.end()) return fTableQE.back();
    const std::size_t i = static_cast<std::size_t>(it - fTableWl.begin());   // fTableWl[i-1] <= wl < fTableWl[i]
    if (i == 0) return fTableQE.front();
    const double t = (wl_nm - fTableWl[i-1]) / (fTableWl[i] - fTableWl[i-1]);
    return fTableQE[i-1] + t * (fTableQE[i] - fTableQE[i-1]);
  }
  if (wl_nm < fWlMin || wl_nm > fWlMax) return 0.;
  return fQE;
}

G4String MyPMTDetector::Description() const
{
  std::ostringstream os;
  if (!fTableWl.empty()) {
    double qmax = 0., wmax = 0.;
    for (std::size_t i = 0; i < fTableQE.size(); ++i) if (fTableQE[i] > qmax) { qmax = fTableQE[i]; wmax = fTableWl[i]; }
    os << "QE table " << fQEFile << " (" << fTableWl.size() << " points, "
       << fTableWl.front() << "-" << fTableWl.back() << " nm, peak " << 100.*qmax << " % at " << wmax << " nm)";
  } else {
    os << "flat QE = " << fQE << " for " << fWlMin << " <= wl <= " << fWlMax << " nm (0 outside)";
  }
  return os.str();
}

G4bool MyPMTDetector::ProcessHits(G4Step *aStep, G4TouchableHistory *)
{
  G4Track *track = aStep->GetTrack();
  track->SetTrackStatus(fStopAndKill);   // photocathode is opaque: terminal counter

  G4StepPoint *preStepPoint = aStep->GetPreStepPoint();   // entry into the photocathode
  G4ThreeVector pos  = preStepPoint->GetPosition();
  G4double      time = preStepPoint->GetGlobalTime();
  G4ThreeVector mom  = preStepPoint->GetMomentum();
  G4double      wl   = (1.239841939*eV / mom.mag()) * 1E+03;   // nm
  G4double      cosTheta = mom.unit().z();                      // +1 = normal incidence from the front
  G4int         primary  = (track->GetParentID() == 0) ? 1 : 0; // 1 = unshifted beam photon, 0 = WLS daughter

  G4int evt = G4RunManager::GetRunManager()->GetCurrentEvent()->GetEventID();
  G4AnalysisManager *man = G4AnalysisManager::Instance();

  // Ntuple 6: every photon reaching the photocathode (pre-QE)
  man->FillNtupleIColumn(6, 0, evt);
  man->FillNtupleDColumn(6, 1, pos.x());
  man->FillNtupleDColumn(6, 2, pos.y());
  man->FillNtupleDColumn(6, 3, pos.z());
  man->FillNtupleDColumn(6, 4, time);
  man->FillNtupleDColumn(6, 5, wl);
  man->FillNtupleDColumn(6, 6, cosTheta);
  man->FillNtupleIColumn(6, 7, primary);
  man->AddNtupleRow(6);
  ++RunCounters::Instance().nPMTPhotons;
  if (primary) ++RunCounters::Instance().nPMTDirect;

  // Ntuple 7: detected photo-electrons (post-QE)
  if (G4UniformRand() < Efficiency(wl)) {
    man->FillNtupleIColumn(7, 0, evt);
    man->FillNtupleDColumn(7, 1, pos.x());
    man->FillNtupleDColumn(7, 2, pos.y());
    man->FillNtupleDColumn(7, 3, pos.z());
    man->FillNtupleDColumn(7, 4, time);
    man->FillNtupleDColumn(7, 5, wl);
    man->FillNtupleDColumn(7, 6, cosTheta);
    man->FillNtupleIColumn(7, 7, primary);
    man->AddNtupleRow(7);
    ++RunCounters::Instance().nPMTHits;
  }

  return true;
}
