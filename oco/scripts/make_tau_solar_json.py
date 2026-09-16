#!/usr/bin/env python3
"""oco/data/tau_{aband,wco2,sco2}.json and solar_{...}.json.
Inputs: line-by-line tau (tau_lbl.jl) and solar (make_solar_lbl.py) text files at 0.01 cm^-1;
ILS from an OCO-2 L1b granule (per-pixel ils_delta_lambda / ils_relative_response, footprint FP)
or a Gaussian fallback. Convolution at line-by-line resolution, THEN interpolation to the output grid."""
import sys, os, json, datetime, numpy as np
lbl, out, l1b, fp = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])  # l1b path or 'gauss'
N = 4000
BANDS = {"aband": (758.0, 772.0, 0, "o2"), "wco2": (1590.0, 1621.0, 1, "weak_co2"), "sco2": (2042.0, 2082.0, 2, "strong_co2")}
GAUSS_FWHM_NM = {"aband": 0.042, "wco2": 0.076, "sco2": 0.10}
ils_src = "Gaussian"
if l1b != "gauss":
    import h5py
    H = h5py.File(l1b, "r")
    ils_src = f"OCO-2 L1b ILS ({os.path.basename(l1b)}, footprint {fp+1}, nearest spectral sample's ILS)"
def r6(a): return [float(f"{v:.6g}") for v in a]
def convolve(wl_lbl, y_lbl, wl_out, band_i, lam_pix):
    """ILS convolution evaluated at each wl_out (nm). y_lbl on an ascending nm grid."""
    res = np.empty_like(wl_out)
    if l1b == "gauss":
        s = GAUSS_FWHM_NM[name] / 2.3548
        dl = np.linspace(-4*GAUSS_FWHM_NM[name], 4*GAUSS_FWHM_NM[name], 201); w = np.exp(-0.5*(dl/s)**2)
        for k, lam in enumerate(wl_out):
            res[k] = np.trapezoid(np.interp(lam + dl, wl_lbl, y_lbl) * w, dl) / np.trapezoid(w, dl)
        return res
    DL = H["InstrumentHeader/ils_delta_lambda"][band_i, fp, :, :] * 1e3   # um -> nm
    RR = H["InstrumentHeader/ils_relative_response"][band_i, fp, :, :]
    for k, lam in enumerate(wl_out):
        p = int(np.argmin(np.abs(lam_pix - lam)))
        dl, w = DL[p], RR[p]
        res[k] = np.trapezoid(np.interp(lam + dl, wl_lbl, y_lbl) * w, dl) / np.trapezoid(w, dl)
    return res
checks = []
for name, (lo, hi, bi, l1bname) in BANDS.items():
    T = np.loadtxt(f"{lbl}/tau_{name}_lbl.txt"); hdr = open(f"{lbl}/tau_{name}_lbl.txt").readline().strip("# \n").split()
    Sn = np.loadtxt(f"{lbl}/solar_{name}_lbl.txt")
    nu = T[:, 0]; wl_lbl = 1e7 / nu; o = np.argsort(wl_lbl); wl_lbl = wl_lbl[o]
    wl_out = np.linspace(lo, hi, N)
    lam_pix = None
    if l1b != "gauss":
        c = H["InstrumentHeader/dispersion_coef_samp"][bi, fp, :]; i = np.arange(1, 1017)
        lam_pix = sum(c[k] * i**k for k in range(6)) * 1e3     # nm, 1-based sample index
    tau = {}
    for j, key in enumerate(hdr):
        if key == "nu_cm-1": continue
        tau[key] = convolve(wl_lbl, T[o, j], wl_out, bi, lam_pix)
    e0 = convolve(wl_lbl, Sn[o, 1], wl_out, bi, lam_pix)
    fwhm = GAUSS_FWHM_NM[name]
    if l1b != "gauss":
        p = 508; dl = H["InstrumentHeader/ils_delta_lambda"][bi, fp, p, :]*1e3; rr = H["InstrumentHeader/ils_relative_response"][bi, fp, p, :]
        fwhm = float(np.ptp(dl[rr > rr.max()/2]))
    meta = {"band": name, "band_range_nm": [lo, hi], "n_points": N,
            "ils": ils_src + f"; FWHM at band centre {fwhm:.4f} nm",
            "atmosphere": "US Standard Atmosphere 1976 (T, p), 60 layers 1013.25-0.05 hPa; H2O = 50 % RH in the troposphere (column 15.7 kg m-2); XCO2 reference 420 ppm dry; O2 0.20946; CH4 1.9 ppm",
            "line_list": "ABSCO v5.2 (CO2, O2, H2O; JPL/AER tables, includes line mixing and continua); CH4 from HITRAN2020 line-by-line (Voigt, 40 cm-1 wing cutoff)",
            "code": "RSFraLab.github.io/oco/scripts/tau_lbl.jl (AtmosphericAbsorption.jl) + make_tau_solar_json.py",
            "convolution": "optical depths and irradiance convolved with the ILS at 0.01 cm-1 line-by-line resolution, then linearly interpolated to the output grid (as requested; note exp(-m*tau_conv) is an approximation of the ILS-convolved transmittance)",
            "created": datetime.date.today().isoformat(),
            "source": f"{lbl}/tau_{name}_lbl.txt, solar_{name}_lbl.txt"}
    dj = {"meta": dict(meta, description="Vertical (airmass 1) optical depths per absorber; client scales tau_co2 by XCO2/420"),
          "wl": r6(wl_out), "tau_co2": r6(tau["tau_co2"]), "tau_o2": r6(tau["tau_o2"]), "tau_h2o": r6(tau["tau_h2o"])}
    if "tau_ch4" in tau: dj["tau_ch4"] = r6(tau["tau_ch4"])
    json.dump(dj, open(f"{out}/tau_{name}.json", "w"), separators=(",", ":"))
    sj = {"meta": dict(meta, description="Solar irradiance at 1 AU, W m-2 um-1: Toon disk-integrated solar transmittance (solar_merged_20240731) x Planck continuum at 5772 K scaled by (R_sun/AU)^2 (~ -10 % vs measured continuum at 1.6 um, +1 % at 0.76 um)",
                        source="/kiwi-data/Data/groupMembers/cfranken/solar/toon/solar_merged_20240731_600_33300_100.out.gz"),
          "wl": r6(wl_out), "e0": r6(e0)}
    json.dump(sj, open(f"{out}/solar_{name}.json", "w"), separators=(",", ":"))
    for key, arr in list(tau.items()) + [("e0", e0)]:
        checks.append(f"{name} {key}: n={len(arr)} min={arr.min():.4g} max={arr.max():.4g} nan={int(np.isnan(arr).sum())}")
    checks.append(f"{name}: wl {lo}-{hi} nm, ILS FWHM {fwhm:.4f} nm, files tau_{name}.json {os.path.getsize(f'{out}/tau_{name}.json')/1e3:.0f} kB, solar_{name}.json {os.path.getsize(f'{out}/solar_{name}.json')/1e3:.0f} kB")
print("\n".join(checks))
