#!/usr/bin/env python3
"""1.3 sounding_oco2.json — one OCO-2 L1b sounding (three bands) with its L2 Lite values."""
import sys, os, json, datetime, numpy as np, h5py, netCDF4 as nc
l1b, lite, sid, out, surface = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
H = h5py.File(l1b, "r"); ids = H["SoundingGeometry/sounding_id"][:]
fr, fp = [int(v) for v in np.argwhere(ids == sid)[0]]
h, c = 6.62607015e-34, 2.99792458e8
bands = {"aband": (0, "o2"), "wco2": (1, "weak_co2"), "sco2": (2, "strong_co2")}
def r6(a): return [float(f"{v:.6g}") for v in a]
d = {}
for name, (bi, bn) in bands.items():
    coef = H["InstrumentHeader/dispersion_coef_samp"][bi, fp, :]; i = np.arange(1, 1017)
    wl_um = sum(coef[k] * i**k for k in range(6)); wl_nm = wl_um * 1e3
    rad_ph = H[f"SoundingMeasurements/radiance_{bn}"][fr, fp, :].astype(float)       # photons s-1 m-2 sr-1 um-1
    rad = rad_ph * h * c / (wl_um * 1e-6)                                              # W m-2 sr-1 um-1
    bad = H["InstrumentHeader/bad_sample_list"][bi, fp, :]
    good = (bad == 0) & np.isfinite(rad) & (rad > -1e-3)
    d[name] = {"wl": r6(wl_nm), "radiance": r6(np.where(np.isfinite(rad), rad, 0.0)), "good": [bool(v) for v in good]}
    print(f"{name}: wl {wl_nm[0]:.3f}-{wl_nm[-1]:.3f} nm, radiance max {np.nanmax(rad):.4g} W m-2 sr-1 um-1, good {int(good.sum())}/1016")
L = nc.Dataset(lite); k = int(np.argwhere(L["sounding_id"][:] == sid)[0][0])
tai93 = datetime.datetime(1993, 1, 1); t = tai93 + datetime.timedelta(seconds=float(H["SoundingGeometry/sounding_time_tai93"][fr, fp]))
meta = {"sounding_id": str(sid), "time_utc": t.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
        "lat": float(H["SoundingGeometry/sounding_latitude"][fr, fp]), "lon": float(H["SoundingGeometry/sounding_longitude"][fr, fp]),
        "sza": float(H["SoundingGeometry/sounding_solar_zenith"][fr, fp]), "vza": float(H["SoundingGeometry/sounding_zenith"][fr, fp]),
        "saz": float(H["SoundingGeometry/sounding_solar_azimuth"][fr, fp]), "vaz": float(H["SoundingGeometry/sounding_azimuth"][fr, fp]),
        "footprint": fp + 1, "frame": fr, "surface": surface, "l1b_file": os.path.basename(l1b), "l2_file": os.path.basename(lite),
        "operation_mode": "nadir", "xco2_l2_ppm": float(L["xco2"][k]), "xco2_uncertainty_ppm": float(L["xco2_uncertainty"][k]),
        "albedo_l2": {"aband": float(L["Retrieval/albedo_o2a"][k]), "wco2": float(L["Retrieval/albedo_wco2"][k]), "sco2": float(L["Retrieval/albedo_sco2"][k])},
        "albedo_slope_l2_per_wn": {"aband": float(L["Retrieval/albedo_slope_o2a"][k]), "wco2": float(L["Retrieval/albedo_slope_wco2"][k]), "sco2": float(L["Retrieval/albedo_slope_sco2"][k])},
        "surface_pressure_hpa": float(L["Retrieval/psurf"][k]), "aod_total_l2": float(L["Retrieval/aod_total"][k]), "aod_l2": float(L["Retrieval/aod_total"][k]), "xco2_quality_flag": int(L["xco2_quality_flag"][k]), "quality_flag": int(L["xco2_quality_flag"][k]),
        "radiance_units": "W m-2 sr-1 um-1 (L1b photon radiance x hc/lambda)", "polarization_note": "OCO-2 measures one linear polarization: the L1b radiance is that component, about half of the total intensity for an unpolarized scene. Compare with an unpolarized forward model L as polarization_factor * L.", "polarization_factor": 0.5, "wl_note": "L1b dispersion polynomial in the 1-based sample index, footprint-specific",
        "good_note": "good = L1b bad_sample_list == 0 and finite radiance", "created": datetime.date.today().isoformat(), "source": f"{os.path.basename(l1b)}, {os.path.basename(lite)}"}
json.dump({"meta": meta, **d}, open(out, "w"), separators=(",", ":"))
print(json.dumps(meta, indent=None)[:600]); print("wrote", out, f"{os.path.getsize(out)/1e3:.0f} kB")
