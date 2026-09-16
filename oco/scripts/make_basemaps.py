#!/usr/bin/env python3
"""Static Web-Mercator basemaps for footprint-scale.html from OpenStreetMap standard raster tiles
(© OpenStreetMap contributors, ODbL; a one-off stitch of a few dozen tiles per view, committed as PNG so the
widget makes no third-party requests). CARTO light tiles were tried first but are watermarked without an API key.
Writes oco/img/basemap_{orbit,200km,12km,12km_oco3}.jpg and oco/data/basemaps.json with lon/lat bounds."""
import sys, io, json, math, time, urllib.request, numpy as np
from PIL import Image
out_img, out_json = sys.argv[1], sys.argv[2]
def ll2tile(lon, lat, z):
    n = 2 ** z; x = (lon + 180) / 360 * n; y = (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n
    return x, y
def tile2ll(x, y, z):
    n = 2 ** z; lon = x / n * 360 - 180; lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))); return lon, lat
def fetch(z, x, y):
    url = f"https://tile.openstreetmap.org/{z}/{x % (2**z)}/{y}.png"
    req = urllib.request.Request(url, headers={"User-Agent": "RSFraLab-site-build/1.0 (static basemap stitch; cfranken@caltech.edu)"})
    time.sleep(0.15)   # be polite to the OSM tile servers
    for k in range(3):
        try: return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())).convert("RGB")
        except Exception as e: time.sleep(1 + k)
    raise RuntimeError(url)
views = {  # name: (centre lon, lat, zoom, width px, height px)
    "orbit": (-120.0, 10.0, 2, 1024, 640),   # lat ±~76; the polar tip of the track is cut, the widget lifts the pen there   # centred on the Pacific so the dateline-crossing track does not wrap
    "200km": (-118.05, 34.05, 9, 1100, 760),
    "12km":  (-117.90, 34.12, 13, 1100, 760),
    "12km_oco3": (-118.20, 34.00, 13, 1100, 760),   # centre of the OCO-3 LA SAM (fossil0005, 2022-02-18); overwritten below from the data if present
}
try:
    import json as _j; _d = _j.load(open(out_json.replace("basemaps.json", "footprints_oco3_sam_la.json")))
    _pts = [v for f in _d["frames"] for fp in f["fp"] if fp for v in fp]
    views["12km_oco3"] = (sum(v[0] for v in _pts) / len(_pts), sum(v[1] for v in _pts) / len(_pts), 13, 1100, 760)
except Exception as e:
    print("oco3 centre fallback:", e)
meta = {"attribution": "© OpenStreetMap contributors (openstreetmap.org standard tiles, stitched offline; ODbL)", "projection": "Web Mercator (EPSG:3857)", "views": {}}
for name, (clon, clat, z, W, H) in views.items():
    cx, cy = ll2tile(clon, clat, z)
    x0 = cx - W / 512; y0 = cy - H / 512            # tile units (256 px per tile)
    tx0, ty0 = math.floor(x0), math.floor(y0); tx1, ty1 = math.floor(x0 + W / 256), math.floor(y0 + H / 256)
    mosaic = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            if 0 <= ty < 2 ** z: mosaic.paste(fetch(z, tx, ty), ((tx - tx0) * 256, (ty - ty0) * 256))
    px0 = int(round((x0 - tx0) * 256)); py0 = int(round((y0 - ty0) * 256))
    img = mosaic.crop((px0, py0, px0 + W, py0 + H)); img.save(f"{out_img}/basemap_{name}.jpg", quality=80, optimize=True, progressive=True)   # JPEG: 4-6x smaller than PNG for map tiles
    lon_w, lat_n = tile2ll(x0, y0, z); lon_e, lat_s = tile2ll(x0 + W / 256, y0 + H / 256, z)
    meta["views"][name] = {"file": f"basemap_{name}.jpg", "zoom": z, "width": W, "height": H, "lon_w": lon_w, "lon_e": lon_e, "lat_s": lat_s, "lat_n": lat_n,
                           "m_per_px_at_centre": 40075016.686 * math.cos(math.radians(clat)) / (256 * 2 ** z)}
    import os; print(name, f"{os.path.getsize(out_img+'/basemap_'+name+'.jpg')/1e3:.0f} kB", {k: round(v, 4) if isinstance(v, float) else v for k, v in meta["views"][name].items()})
json.dump(meta, open(out_json, "w"), indent=1)
