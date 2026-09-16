#!/usr/bin/env python3
"""Per-cell MEDIAN of OCO-2 L2 Lite FP (v11.2r) good-quality XCO2 on a coarse grid for one year.
Writes an .npz (median, count, cell size) used by make_xco2_hero.py. Illustration only, not a product."""
import glob, sys, numpy as np, netCDF4 as nc
year, out, res = sys.argv[1], sys.argv[2], float(sys.argv[3])
files = sorted(glob.glob(f"/kiwi-data/Data/satellite/OCO2/L2_Lite_FP/11.2r/raw/{year}/oco2_LtCO2_*.nc4"))
ny, nx = int(180 / res), int(360 / res); cells, vals = [], []; nf = 0
for f in files:
    try:
        d = nc.Dataset(f); m = d["xco2_quality_flag"][:] == 0
        lat = d["latitude"][:][m]; lon = d["longitude"][:][m]; x = d["xco2"][:][m].astype(np.float32); d.close()
    except Exception as e:
        print("ERR", f, e); continue
    i = np.clip(((lat + 90) // res).astype(np.int32), 0, ny - 1); j = np.clip(((lon + 180) // res).astype(np.int32), 0, nx - 1)
    cells.append(i * nx + j); vals.append(x); nf += 1
cells = np.concatenate(cells); vals = np.concatenate(vals); o = np.argsort(cells, kind="stable"); cells, vals = cells[o], vals[o]
uniq, start, cnt = np.unique(cells, return_index=True, return_counts=True)
med = np.full(ny * nx, np.nan, np.float32); N = np.zeros(ny * nx, np.int32)
for u, s, c in zip(uniq, start, cnt): med[u] = np.median(vals[s:s + c]); N[u] = c
np.savez(out, median=med.reshape(ny, nx), N=N.reshape(ny, nx), res=res, year=year, n_files=nf)
print(f"{nf} files, {len(vals)} soundings, {int((N>0).sum())} of {ny*nx} {res}-deg cells filled, global median {np.median(vals):.2f} ppm")
