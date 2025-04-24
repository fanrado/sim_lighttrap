import numpy as np

# Load data
data = np.loadtxt('spectrum.txt')
wavelength = data[:, 0]  # nm
counts = data[:, 1]

# Convert wavelength to energy (MeV)
energy = 1239.841939 / wavelength

# Adjust negative values to zero
counts_adjusted = np.maximum(counts, 0)

# Normalize
normalized_counts = counts_adjusted / np.max(counts_adjusted)

# Create Geant4 macro
with open('../mac/spectrum_macro.mac', 'w') as f:
    f.write('/gps/particle gamma\n')
    f.write('/gps/ene/type Arb\n')
    f.write('/gps/hist/type arb\n')
    
    # Write all data points
    for e, p in zip(energy, normalized_counts):
        f.write(f'/gps/hist/point {e:.6f} {p:.6f}\n')
    
    f.write('/gps/hist/inter Lin\n')