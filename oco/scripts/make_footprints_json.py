#!/usr/bin/env python3
"""2.1 track_oco2_orbit.json and 2.2 footprints_oco2_la.json from one OCO-2 L1b granule.
Track: sub-satellite point every 10 s (every 30 frames at 3 Hz) = mean of footprints 4 and 5.
Footprints: 100 consecutive frames centred on the frame nearest (lat0, lon0), 8 footprints x 4 O2-band vertices."""
import sys, os, json, datetime, numpy as np, h5py
from pyproj import Geod
l1b, out, lat0, lon0 = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
NF = 100; g = Geod(ellps="WGS84")
H = h5py.File(l1b, "r")
lat = H["SoundingGeometry/sounding_latitude"][:]; lon = H["SoundingGeometry/sounding_longitude"][:]
t = H["SoundingGeometry/sounding_time_tai93"][:]
vlat = H["FootprintGeometry/footprint_vertex_latitude"][:, :, 0, :]; vlon = H["FootprintGeometry/footprint_vertex_longitude"][:, :, 0, :]
mode = b"".join(H["Metadata/OperationMode"][0]).decode().strip() if H["Metadata/OperationMode"].dtype.kind == "S" else str(H["Metadata/OperationMode"][0])
orbit = int(H["Metadata/StartOrbitNumber"][0]); date = b"".join(H["Metadata/RangeBeginningDate"][0]).decode() if H["Metadata/RangeBeginningDate"].dtype.kind == "S" else str(H["Metadata/RangeBeginningDate"][0])
tai93 = datetime.datetime(1993, 1, 1)
def hms(s): return (tai93 + datetime.timedelta(seconds=float(s))).strftime("%H:%M:%S.%f")[:-3]
def r5(x): return float(f"{x:.5f}")
# --- 2.1 track
nadir_lat = lat[:, 3:5].mean(axis=1); nadir_lon = lon[:, 3:5].mean(axis=1)
ok = np.isfinite(nadir_lat) & (np.abs(nadir_lat) <= 90)
idx = np.arange(0, lat.shape[0], 30); idx = idx[ok[idx]]
track = {"meta": {"orbit": orbit, "date": date, "mode": mode, "source": os.path.basename(l1b), "created": datetime.date.today().isoformat(),
                  "description": "sub-satellite point (mean of footprints 4-5) every 10 s over the daytime part of one OCO-2 orbit", "n_points": int(len(idx)),
                  "time_utc_first": hms(t[idx[0], 3]), "time_utc_last": hms(t[idx[-1], 3])},
         "lonlat": [[r5(nadir_lon[i]), r5(nadir_lat[i])] for i in idx]}
json.dump(track, open(f"{out}/track_oco2_orbit.json", "w"), separators=(",", ":"))
# --- 2.2 footprints
d = np.hypot(nadir_lat - lat0, (nadir_lon - lon0) * np.cos(np.radians(lat0))); c = int(np.nanargmin(d))
valid = np.isfinite(vlat).all(axis=2) & (np.abs(vlat) <= 90).all(axis=2)          # (frame, fp)
best, f0 = -1, None
for s0 in range(max(0, c - NF + 10), min(lat.shape[0] - NF, c - 9)):   # window must contain the target frame
    nv = int(valid[s0:s0 + NF].sum())
    if nv > best: best, f0 = nv, s0
frames = range(f0, f0 + NF)
print(f"window frames {f0}-{f0+NF-1} (closest-to-target frame {c}), valid footprints {best}/800")
def poly_dims(vlo, vla):
    # vertices ordered around the footprint: sides 0-1, 1-2, 2-3, 3-0; along/cross from the two side pairs
    s = [g.inv(vlo[i], vla[i], vlo[(i+1) % 4], vla[(i+1) % 4])[2] / 1e3 for i in range(4)]
    return sorted([np.mean([s[0], s[2]]), np.mean([s[1], s[3]])])   # (short, long)
short, long_, swath = [], [], []
fr = []
for f in frames:
    fps = []
    for k in range(8):
        vlo, vla = vlon[f, k, :], vlat[f, k, :]
        if not (np.all(np.isfinite(vlo)) and np.all(np.abs(vla) <= 90)): fps.append(None); continue
        fps.append([[r5(a), r5(b)] for a, b in zip(vlo, vla)])
        a, b = poly_dims(vlo, vla); short.append(a); long_.append(b)
    if fps[0] is not None and fps[7] is not None:
        # swath: distance between the outer edges of footprints 1 and 8 (across track), from vertex centroids
        c1 = (np.mean(vlon[f, 0, :]), np.mean(vlat[f, 0, :])); c8 = (np.mean(vlon[f, 7, :]), np.mean(vlat[f, 7, :]))
        swath.append(g.inv(c1[0], c1[1], c8[0], c8[1])[2] / 1e3 + np.mean(short[-8:]) if len(short) >= 8 else np.nan)
    fr.append({"t": hms(t[f, 3]), "fp": fps})
meta = {"file": os.path.basename(l1b), "date": date, "orbit": orbit, "mode": mode, "n_frames": NF, "n_footprints": int(sum(fp is not None for x in fr for fp in x["fp"])),
        "frame_rate_hz": 3, "centre_frame_lat": r5(nadir_lat[c]), "centre_frame_lon": r5(nadir_lon[c]),
        "crosstrack_km_median": r5(np.nanmedian(short)), "alongtrack_km_median": r5(np.nanmedian(long_)), "swath_km_median": r5(np.nanmedian(swath)),
        "vertices": "O2 A-band footprint vertices from L1b FootprintGeometry (geodetic, topography-corrected), [lon, lat]",
        "created": datetime.date.today().isoformat(),
        "missing_note": "footprints with fill-value vertices in the L1b file are null (see n_footprints)", "description": f"{NF} consecutive nadir frames over ({lat0}, {lon0}), window chosen with the fewest fill-value footprints; footprint dims are geodesic side lengths (short = across track, long = along track); swath = outer footprint centroid separation + one footprint width"}
json.dump({"meta": meta, "frames": fr}, open(f"{out}/footprints_oco2_la.json", "w"), separators=(",", ":"))
print("track:", len(idx), "points", track["meta"]["time_utc_first"], "->", track["meta"]["time_utc_last"], f"{os.path.getsize(out+'/track_oco2_orbit.json')/1e3:.0f} kB")
print("footprints:", meta["n_footprints"], "footprints, centre", meta["centre_frame_lat"], meta["centre_frame_lon"], "medians cross/along/swath km:", meta["crosstrack_km_median"], meta["alongtrack_km_median"], meta["swath_km_median"], f"{os.path.getsize(out+'/footprints_oco2_la.json')/1e3:.0f} kB")
