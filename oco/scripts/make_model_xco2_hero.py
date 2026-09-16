#!/usr/bin/env python3
"""Hero image(s) from the AtmosTransport CATRINE C90 run (co2_natural = total CO2, dry mole fraction):
  1) JJA 2019 mean XCO2 (dry-air-mass weighted column) on a 0.25-degree grid -> oco/img/xco2_hero.jpg (2400x1080, dark)
  2) optional GIF: one frame per day at 12 UTC through JJA -> oco/img/xco2_hero_jja2019.gif
Usage: make_model_xco2_hero.py <run dir> <out jpg> [<out gif>]"""
import sys, glob, os, numpy as np, netCDF4 as nc, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, cartopy.crs as ccrs, cartopy.io.shapereader as shpreader
from matplotlib.colors import LinearSegmentedColormap, Normalize
from scipy.spatial import cKDTree
from scipy import ndimage
run, out_jpg = sys.argv[1], sys.argv[2]; out_gif = sys.argv[3] if len(sys.argv) > 3 else None
files = sorted(f for f in glob.glob(f"{run}/*_2019*.nc") if f[-11:-5][:4] == "2019" and f[-7:-5] in ("06", "07", "08"))
print(len(files), "files", os.path.basename(files[0]), "->", os.path.basename(files[-1]))
d0 = nc.Dataset(files[0]); lons = d0["lons"][:].ravel(); lats = d0["lats"][:].ravel()
def xyz(lo, la): lo, la = np.radians(lo), np.radians(la); return np.c_[np.cos(la) * np.cos(lo), np.cos(la) * np.sin(lo), np.sin(la)]
tree = cKDTree(xyz(lons, lats)); res = 0.25
glon = np.arange(-180 + res / 2, 180, res); glat = np.arange(-90 + res / 2, 90, res); GL, GA = np.meshgrid(glon, glat)
_, idx = tree.query(xyz(GL.ravel(), GA.ravel())); idx = idx.reshape(GA.shape)
area = d0["cell_area"][:].ravel(); d0.close()
def xco2_of(d, k):
    c = d["co2_natural"][k].reshape(66, -1); am = d["air_mass_per_area"][k].reshape(66, -1)
    return (c * am).sum(0) / am.sum(0) * 1e6                    # ppm, per C90 cell
S, n = None, 0; frames = []
for f in files:
    d = nc.Dataset(f); nt = len(d["time"][:])
    for k in range(nt):
        x = xco2_of(d, k); S = x if S is None else S + x; n += 1
        if out_gif and k == 4: frames.append((os.path.basename(f)[-11:-3], x[idx]))     # 12 UTC frame
    d.close()
mean_cell = S / n; M = mean_cell[idx]
gm = np.average(mean_cell, weights=area); print(f"JJA 2019 mean XCO2: global {gm:.2f} ppm, range {M.min():.2f}-{M.max():.2f}")
cmap = LinearSegmentedColormap.from_list("xco2", ["#10203f", "#1b3f7a", "#1f6f8b", "#3c9c8c", "#9cc07a", "#e6c65c", "#f5a742"])
coast = [g for g in shpreader.Reader(shpreader.natural_earth("50m", "physical", "coastline")).geometries()]
def render(field, lo, hi, path, quality=72, size=(24, 10.8), dpi=100, fmt="jpg"):
    fig = plt.figure(figsize=size, dpi=dpi, facecolor="#0b1420")
    ax = fig.add_axes([0, 0, 1, 1], projection=ccrs.Robinson(central_longitude=10)); ax.set_global(); ax.set_facecolor("#0b1420"); ax.spines["geo"].set_visible(False)
    sm = ndimage.gaussian_filter(field, sigma=1.0, mode=("nearest", "wrap"))
    ax.imshow(cmap(Normalize(lo, hi)(sm)), origin="lower", extent=(-180, 180, -90, 90), transform=ccrs.PlateCarree(), regrid_shape=2400, zorder=2, interpolation="bilinear")
    ax.add_geometries(coast, ccrs.PlateCarree(), facecolor="none", edgecolor="#e8edf2", linewidth=0.7, alpha=0.6, zorder=4)
    if fmt == "jpg": fig.savefig(path, dpi=dpi, pil_kwargs={"quality": quality, "optimize": True, "progressive": True})
    else: fig.canvas.draw(); img = np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(); plt.close(fig); return img
    plt.close(fig)
lo, hi = np.percentile(M, 1), np.percentile(M, 99)
render(M, lo, hi, out_jpg); print("wrote", out_jpg, f"{os.path.getsize(out_jpg)/1e3:.0f} kB", "range", round(lo, 2), round(hi, 2))
if out_gif and frames:
    from PIL import Image
    allv = np.concatenate([fr[1].ravel() for fr in frames]); lo2, hi2 = np.percentile(allv, 1), np.percentile(allv, 99)
    ims = []
    for name, fld in frames:
        img = render(fld, lo2, hi2, None, size=(12, 5.4), dpi=100, fmt="rgb"); im = Image.fromarray(img).convert("P", palette=Image.ADAPTIVE, colors=128); ims.append(im)
    ims[0].save(out_gif, save_all=True, append_images=ims[1:], duration=120, loop=0, optimize=True)
    print("wrote", out_gif, f"{os.path.getsize(out_gif)/1e6:.1f} MB", len(ims), "frames", "range", round(lo2, 2), round(hi2, 2))
