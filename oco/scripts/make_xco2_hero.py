#!/usr/bin/env python3
"""oco/img/xco2_hero.jpg — OCO-2 XCO2, June–August 2021–2024, per-cell medians of good-quality Lite soundings on a
1-degree grid (land and ocean glint), nearest-neighbour gap fill, Gaussian smoothing (sigma 1 cell), perceptual
dark-blue -> gold ramp, subtle coastlines, no axes/labels/colorbar, 2400x1080, dark background."""
import sys, os, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, cartopy.crs as ccrs, cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap
from scipy import ndimage
npz, out = sys.argv[1], sys.argv[2]
z = np.load(npz, allow_pickle=True); X, N, res = z["median"].astype(float), z["N"], float(z["res"])
X[N < 3] = np.nan
dist, (ii, jj) = ndimage.distance_transform_edt(np.isnan(X), return_distances=True, return_indices=True)
Xf = X[ii, jj]; Xs = ndimage.gaussian_filter(Xf, sigma=2.0, mode=("nearest", "wrap"))   # 2 cells: removes the glint streaks
Xs[dist > 5] = np.nan                                  # keep the polar-night gaps dark instead of inventing values
lat_c = -90 + res * (np.arange(Xs.shape[0]) + 0.5); Xs[lat_c < -60, :] = np.nan          # Antarctica removed for now
lo, hi = np.nanpercentile(Xs, 2), np.nanpercentile(Xs, 98)
print(z["years"], list(z["months"]), "cells", int(np.isfinite(X).sum()), "range", round(lo, 2), round(hi, 2))
fig = plt.figure(figsize=(24, 10.8), dpi=100, facecolor="#0b1420")
ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Robinson(central_longitude=10)); ax.set_global(); ax.set_facecolor("#0b1420"); ax.spines["geo"].set_visible(False)
# dark blue -> teal -> gold, in the spirit of img/blend_v9_small.jpg
cmap = LinearSegmentedColormap.from_list("xco2", ["#10203f", "#1b3f7a", "#1f6f8b", "#3c9c8c", "#9cc07a", "#e6c65c", "#f5a742"])
# Render the field as an RGBA image (colour from the ramp, alpha = smooth data mask) and let cartopy warp it:
# no mesh seams in Robinson, and the data edge fades instead of stair-stepping.
from matplotlib.colors import Normalize
up = 4                                                 # upsample before warping so the bilinear regrid stays smooth
Xu = ndimage.zoom(np.where(np.isfinite(Xs), Xs, lo), up, order=1)
valid = np.isfinite(Xs).astype(float); valid = ndimage.gaussian_filter(ndimage.zoom(valid, up, order=1), sigma=1.5 * up)
rgba = cmap(Normalize(lo, hi)(Xu)); rgba[..., 3] = np.clip((valid - 0.35) / 0.4, 0, 1)
ax.imshow(rgba, origin="lower", extent=(-180, 180, -90, 90), transform=ccrs.PlateCarree(), regrid_shape=2400, zorder=2, interpolation="bilinear")
import cartopy.io.shapereader as shpreader, shapely.geometry as sgeom
coast = [g for g in shpreader.Reader(shpreader.natural_earth("50m", "physical", "coastline")).geometries() if g.centroid.y > -60]
ax.add_geometries(coast, ccrs.PlateCarree(), facecolor="none", edgecolor="#e8edf2", linewidth=0.7, alpha=0.6, zorder=4)
fig.savefig(out, dpi=100, pil_kwargs={"quality": 70, "optimize": True, "progressive": True})
print("wrote", out, f"{os.path.getsize(out)/1e3:.0f} kB")
