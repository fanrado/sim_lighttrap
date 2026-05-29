#ifndef NameMap_HH
#define NameMap_HH

#include <unordered_map>
#include <string>

// A fixed mapping between material names and integer codes.
class NameMap {
public:
  // Encode: Look up the integer code for a given material name.
  // Returns 0 if the material is not found.
  static int Encode(const std::string& materialName) {
    auto it = GetMap().find(materialName);
    return (it != GetMap().end()) ? it->second : 0;
  }
  
  // Decode: Look up the material name given an integer code.
  // Returns "Unknown" if the code is not found.
  static std::string Decode(int code) {
    // Loop through the fixed map and return the matching key.
    for (const auto& pair : GetMap()) {
      if (pair.second == code)
        return pair.first;
    }
    return "Unknown";
  }

private:
  // Returns the fixed mapping as a const reference.
  static const std::unordered_map<std::string, int>& GetMap() {
    // Define your fixed mapping here.
    // Use unique codes for each material you expect.
    static const std::unordered_map<std::string, int> fixedMap = {
      {"pTP", 1},
      {"acrylicMcMaster", 2},
      {"bluewlsacrylic", 3},
      {"G4_lAr", 4},
      {"uvTransAcrylic", 5},    // UV-transparent PMMA carrier for pTP film

      {"Scintillation", 100},
      {"OpWLS", 101}

    };
    return fixedMap;
  }
};

#endif // NameMap_HH
