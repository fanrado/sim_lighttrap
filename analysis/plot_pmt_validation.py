"""
plot_pmt_validation.py — geometry/beam validation figure for a detectorType=pmt run.

Usage:
    python3.13 analysis/plot_pmt_validation.py <output_apexltsim0.root> [out.png]

Panels: (a) pTP WLS birth positions vs the 14 mm beam and 23 mm photocathode,
(b) photocathode hit map, (c) z of every recorded photon point, which should
line up with the source plane, the pTP film, the first-layer exit counter and
the PMT face.  Requires uproot + matplotlib.
"""
import os
import sys
import uproot, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

infile = sys.argv[1] if len(sys.argv) > 1 else "output_apexltsim0.root"
outfile = sys.argv[2] if len(sys.argv) > 2 else "pmt_validation.png"
f = uproot.open(infile)
pmt = f["PMTPhotons"].arrays(["fX","fY","fZ"], library="np")
wls = f["WLSPhoton"].arrays(["posX","posY","posZ"], library="np")
fl  = f["FirstLayerBackplane"].arrays(["fZ","forward"], library="np")
pri = f["Primary"].arrays(["posX","posY","posZ"], library="np")

TXT, TXT2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": GRID, "axes.labelcolor": TXT2,
                     "xtick.color": TXT2, "ytick.color": TXT2, "axes.titlecolor": TXT,
                     "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})

fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))

# (a) beam footprint on the pTP film (WLS birth positions) vs the 14 mm beam
ax = axes[0]
ax.scatter(wls["posX"], wls["posY"], s=4, color=C1, alpha=0.6, linewidths=0, label="pTP WLS photon births")
ax.add_patch(Circle((0,0), 7.0, fill=False, color=C2, lw=2, label="14 mm beam (r = 7 mm)"))
ax.add_patch(Circle((0,0), 11.5, fill=False, color=TXT2, lw=1.2, ls="--", label="23 mm photocathode"))
ax.set_aspect("equal"); ax.set_xlim(-14, 14); ax.set_ylim(-14, 14)
ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]"); ax.set_title("Beam footprint on the pTP film")
ax.legend(loc="upper right", fontsize=8, frameon=False)

# (b) photocathode hit map, single-hue sequential
ax = axes[1]
h = ax.hist2d(pmt["fX"], pmt["fY"], bins=46, range=[[-14,14],[-14,14]], cmap="Blues", cmin=1)
ax.add_patch(Circle((0,0), 11.5, fill=False, color=TXT2, lw=1.2, ls="--"))
ax.add_patch(Circle((0,0), 7.0, fill=False, color=C2, lw=1.5))
ax.set_aspect("equal"); ax.set_xlabel("x [mm]"); ax.set_ylabel("y [mm]")
ax.set_title(f"Photocathode hits (N = {len(pmt['fX'])})")
cb = fig.colorbar(h[3], ax=ax, shrink=0.85); cb.set_label("photons / bin", color=TXT2); cb.outline.set_edgecolor(GRID)

# (c) z of recorded photon points: validates the layer stack along the beam
ax = axes[2]
bins = np.linspace(-22, 2, 97)
for arr, c, lab in ((pri["posZ"], C4, "primary (source plane)"),
                    (wls["posZ"], C1, "pTP WLS births"),
                    (fl["fZ"][fl["forward"]==1], C3, "first-layer exit counter"),
                    (pmt["fZ"], C2, "photocathode entries")):
    ax.hist(arr, bins=bins, histtype="step", lw=2, color=c, label=lab)
for z, lab in ((-6.0, "pTP / acrylic front"), (-3.0, "acrylic back"), (0.0, "PMT face")):
    ax.axvline(z, color=GRID, lw=1)
    ax.text(z - 0.3, 0.02, lab, rotation=90, va="bottom", ha="right", fontsize=7,
            color=TXT2, transform=ax.get_xaxis_transform())
ax.set_yscale("log"); ax.set_xlabel("z [mm]"); ax.set_ylabel("entries")
ax.set_title("Where photons are recorded along z"); ax.legend(fontsize=8, frameon=False, loc="upper left")
for a in axes:
    a.grid(color=GRID, lw=0.6); a.set_axisbelow(True)
    for sp in ("top","right"): a.spines[sp].set_visible(False)
fig.suptitle(f"PMT mode validation — {len(pri['posZ'])} beam photons ({os.path.basename(infile)})", color=TXT, fontsize=12)
fig.tight_layout()
fig.savefig(outfile, dpi=130)
print("wrote", outfile)
print("pTP birth z range:", wls["posZ"].min(), wls["posZ"].max())
print("PMT entry z range:", pmt["fZ"].min(), pmt["fZ"].max())
print("exit-counter z range:", fl["fZ"].min(), fl["fZ"].max())
print("primary z:", np.unique(pri["posZ"]))
print("WLS births r>7.1 mm:", int((np.hypot(wls["posX"], wls["posY"])>7.1).sum()), "of", len(wls["posX"]))
