#!/usr/bin/env python3
"""2.3 footprints_oco3_sam_la.json — one OCO-3 SAM over Los Angeles from the L2 Lite FP file (all soundings in the
Lite file for that SAM; Lite files carry only soundings that passed L2 pre-screening, so this is not every L1b sounding)."""
import sys, os, json, datetime, numpy as np, netCDF4 as nc
from pyproj import Geod
lite, target_id, out = sys.argv[1], sys.argv[2], sys.argv[3]
g = Geod(ellps="WGS84"); d = nc.Dataset(lite)
tid = np.array([str(x) for x in d["Sounding/target_id"][:]]); m = tid == target_id
# the same target id can be attached to soundings far from the SAM (transition segments): keep the SAM's own area
lat_all, lon_all = d["latitude"][:], d["longitude"][:]; clat, clon = np.median(lat_all[m]), np.median(lon_all[m])
far = m & ((np.abs(lat_all - clat) > 1.0) | (np.abs(lon_all - clon) > 1.2)); n_far = int(far.sum()); m = m & ~far
name = str(np.unique(np.array([str(x) for x in d["Sounding/target_name"][:]])[m])[0])
t = d["time"][:][m]; vlat = d["vertex_latitude"][:][m]; vlon = d["vertex_longitude"][:][m]; sid = d["sounding_id"][:][m]
fpn = d["Sounding/footprint"][:][m]; qf = d["xco2_quality_flag"][:][m]; xco2 = d["xco2"][:][m]
o = np.argsort(t); t, vlat, vlon, sid, fpn, qf, xco2 = t[o], vlat[o], vlon[o], sid[o], fpn[o], qf[o], xco2[o]
# frames = soundings sharing a frame time (sounding_id without the footprint digit); swaths split at gaps > 2 s
frame_key = sid // 10; uniq, inv = np.unique(frame_key, return_inverse=True)
ft = np.array([t[inv == i].min() for i in range(len(uniq))]); gaps = np.diff(ft) > 2.0; swath_of_frame = np.concatenate([[0], np.cumsum(gaps)])
def r5(x): return float(f"{x:.5f}")
frames = []; short, long_ = [], []
for i, key in enumerate(uniq):
    sel = np.where(inv == i)[0]; fps = [None] * 8
    for s in sel:
        if not np.all(np.isfinite(vlon[s])): continue
        fps[int(fpn[s]) - 1] = [[r5(a), r5(b)] for a, b in zip(vlon[s], vlat[s])]
        sd = [g.inv(vlon[s][k], vlat[s][k], vlon[s][(k+1) % 4], vlat[s][(k+1) % 4])[2] / 1e3 for k in range(4)]
        a, b = sorted([np.mean([sd[0], sd[2]]), np.mean([sd[1], sd[3]])]); short.append(a); long_.append(b)
    ts = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=float(ft[i]))
    frames.append({"t": ts.strftime("%H:%M:%S.%f")[:-3], "swath": int(swath_of_frame[i]), "fp": fps})
meta = {"file": os.path.basename(lite), "date": (datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=float(t.min()))).strftime("%Y-%m-%d"),
        "sam_id": target_id, "target_name": name, "n_frames": len(frames), "n_footprints": int(sum(fp is not None for f in frames for fp in f["fp"])),
        "n_swaths": int(swath_of_frame.max() + 1), "n_dropped_far_from_sam": n_far, "n_good_quality": int((qf == 0).sum()), "xco2_median_good_ppm": float(np.median(xco2[qf == 0])) if (qf == 0).any() else None,
        "frame_rate_hz": 3, "crosstrack_km_median": r5(np.median(short)), "alongtrack_km_median": r5(np.median(long_)),
        "vertices": "L2 Lite FP vertex_longitude/vertex_latitude, [lon, lat]", "created": datetime.date.today().isoformat(),
        "description": "all soundings of one OCO-3 Snapshot Area Map present in the L2 Lite file (L2-prescreened, not the full L1b set); frames grouped by swath (gaps > 2 s)"}
json.dump({"meta": meta, "frames": frames}, open(out, "w"), separators=(",", ":"))
print({k: v for k, v in meta.items() if k not in ("vertices", "description")}); print("wrote", out, f"{os.path.getsize(out)/1e3:.0f} kB")
