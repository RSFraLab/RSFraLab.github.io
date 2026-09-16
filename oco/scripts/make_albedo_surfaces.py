#!/usr/bin/env python3
"""oco/data/albedo_surfaces.json — five surface reflectance spectra, 400-2200 nm at 5 nm,
from ECOSTRESS Spectral Library 1.0 entries (JHU/UCSB spectra), plus OCO band means.
Source copies: /kiwi-data/Data/groupMembers/sanghavi/ECOSTRESSlib (ecospeclib zips)."""
import json, sys, glob, os, datetime, numpy as np
SRC = sys.argv[1]; OUT = sys.argv[2]
ENTRIES = {  # role -> ECOSTRESS file stem
  "ocean":     "water.tapwater.none.liquid.all.tapwater.jhu.becknic",          # stand-in: liquid water (no seawater entry on disk)
  "desert":    "soil.aridisol.calciorthid.none.all.84p3721.jhu.becknic",       # light yellowish-brown loam, arid soil
  "snow":      "water.snow.finegranular.fine.all.fine_snw_.jhu.becknic",
  "conifer":   "vegetation.tree.pinus.ponderosa.vswir.vh067.ucsb.asd",
  "dry_grass": "nonphotosyntheticvegetation.leaves.unknown.unknown.all.drygrass.jhu.becknic",
}
BANDS = {"aband": (758, 772), "wco2": (1590, 1621), "sco2": (2042, 2082)}
wl = np.arange(400, 2201, 5, dtype=float)
def read_spec(stem):
    path = os.path.join(SRC, stem + ".spectrum.txt")
    x, y = [], []
    with open(path, encoding="latin-1") as f:
        for line in f:
            parts = line.split()
            if len(parts) == 2:
                try: a, b = float(parts[0]), float(parts[1])
                except ValueError: continue
                x.append(a); y.append(b)
    x = np.array(x) * 1000.0; y = np.array(y) / 100.0   # um -> nm, percent -> fraction
    o = np.argsort(x); x, y = x[o], y[o]
    keep = np.isfinite(y) & (y > 0.001)   # JHU spectra carry interleaved zero samples near 400-470 nm (instrument edge) — drop them
    return x[keep], np.clip(y[keep], 0, 1)
out = {"meta": {"library": "ECOSTRESS Spectral Library 1.0 (JHU Becknic / UCSB ASD spectra)",
                "source": "ecospeclib zips, local copy /kiwi-data/Data/groupMembers/sanghavi/ECOSTRESSlib",
                "created": datetime.date.today().isoformat(),
                "description": "Directional-hemispherical reflectance, linearly resampled to 400-2200 nm at 5 nm; band_means are plain means over each OCO band range",
                "entries": {k: v + ".spectrum.txt" for k, v in ENTRIES.items()},
                "notes": {"ocean": "ECOSTRESS has no seawater entry in the local copy; tapwater (liquid water, near-zero SWIR reflectance) is used as a stand-in for a flat calm ocean without glint"},
                "band_ranges_nm": BANDS},
       "wl": [float(v) for v in wl]}
band_means = {}
checks = []
for role, stem in ENTRIES.items():
    x, y = read_spec(stem)
    r = np.interp(wl, x, y)
    out[role] = [float(f"{v:.6g}") for v in r]
    band_means[role] = {b: float(f"{np.mean(np.interp(np.arange(lo, hi + 0.1, 1.0), x, y)):.6g}") for b, (lo, hi) in BANDS.items()}
    checks.append(f"{role:9s} n={len(r)} min={r.min():.4f} max={r.max():.4f} nan={int(np.isnan(r).sum())} src_range={x.min():.0f}-{x.max():.0f} nm band_means={band_means[role]}")
out["band_means"] = band_means
json.dump(out, open(OUT, "w"), separators=(",", ":"))
print(f"wrote {OUT} ({os.path.getsize(OUT)/1e3:.1f} kB)"); print("\n".join(checks))
