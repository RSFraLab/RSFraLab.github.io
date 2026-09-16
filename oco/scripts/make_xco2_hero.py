#!/usr/bin/env python3
"""oco/img/xco2_hero.jpg — OCO-2 annual XCO2 composite (per-cell MEDIAN of good-quality Lite soundings on a coarse grid),
gap-filled and lightly smoothed, drawn over land only on a dark ocean; no axes, colorbar, or labels; 2400x1080."""
import sys, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, cartopy.crs as ccrs, cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap
from scipy import ndimage
npz, out = sys.argv[1], sys.argv[2]
z = np.load(npz, allow_pickle=True); X, N, res = z["median"].astype(float), z["N"], float(z["res"])
X[N < 5] = np.nan
# gap fill (nearest valid cell) then smooth; mask cells farther than 3 cells from any observation
idx = ndimage.distance_transform_edt(np.isnan(X), return_distances=True, return_indices=True)
dist, (ii, jj) = idx[0], idx[1]
Xf = X[ii, jj]; Xs = ndimage.gaussian_filter(Xf, sigma=0.7, mode=("nearest", "wrap"))
Xs[dist > 1] = np.nan
lat_c = -90 + res * (np.arange(Xs.shape[0]) + 0.5); Xs[lat_c < -62, :] = np.nan   # Antarctica: sparse, artefact-prone
lo, hi = np.nanpercentile(Xs, 1), np.nanpercentile(Xs, 99)
print("year", z["year"], "cells", int(np.isfinite(X).sum()), "range", round(lo, 2), round(hi, 2))
fig = plt.figure(figsize=(24, 10.8), dpi=100, facecolor="#0b1420")
ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Robinson(central_longitude=10))
ax.set_global(); ax.set_facecolor("#0b1420"); ax.spines["geo"].set_visible(False)
cmap = LinearSegmentedColormap.from_list("xco2", ["#1d4ed8", "#38bdf8", "#4ade80", "#fde047", "#fb923c", "#dc2626"])
lon = np.arange(-180, 180 + res/2, res); lat = np.arange(-90, 90 + res/2, res)
pm = ax.pcolormesh(lon, lat, np.ma.masked_invalid(Xs), transform=ccrs.PlateCarree(), cmap=cmap, vmin=lo, vmax=hi, shading="flat", zorder=2)
ax.add_feature(cfeature.OCEAN.with_scale("110m"), facecolor="#0b1420", edgecolor="none", zorder=3)   # ocean stays dark
ax.add_feature(cfeature.COASTLINE.with_scale("50m"), edgecolor="#e8edf2", linewidth=1.8, zorder=4)   # bold light outlines
fig.savefig(out, dpi=100, pil_kwargs={"quality": 62, "optimize": True, "progressive": True})
print("wrote", out, f"{os.path.getsize(out)/1e3:.0f} kB")
