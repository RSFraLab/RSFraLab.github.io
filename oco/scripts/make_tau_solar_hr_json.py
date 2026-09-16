#!/usr/bin/env python3
"""Round-2 data for the spectra explorer: UNCONVOLVED high-resolution optical depths and solar irradiance,
plus one ILS kernel per band. The client forms exp(-m*tau) at full resolution, multiplies by E0, convolves with
the ILS, and only then samples for drawing — so saturated lines are handled correctly.
  tau_{band}.json   : wl (nm), tau_co2 (420 ppm), tau_o2, tau_h2o at 1013.25 hPa, airmass 1 (no CH4: tau < 3e-5)
  solar_{band}.json : wl (nm), e0 (W m-2 um-1 at 1 AU) = TSIS-1 HSRS continuum x Toon line transmittance
  ils_{band}.json   : delta_lambda_nm (same spacing as tau), response (unit sum), fwhm_nm — OCO-2 L1b ILS, footprint 4, band-centre sample
Usage: make_tau_solar_hr_json.py <lbl dir> <out dir> <L1b granule> <footprint index 0-7> <TSIS HSRS .nc>"""
import sys, os, json, datetime, numpy as np, h5py, netCDF4 as nc
lbl, out, l1b, fp, tsis = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
BANDS = {"aband": (758.0, 772.0, 0.001, 0), "wco2": (1590.0, 1621.0, 0.004, 1), "sco2": (2042.0, 2082.0, 0.005, 2)}
H = h5py.File(l1b, "r")
T = nc.Dataset(tsis); twl = T["Vacuum Wavelength"][:] if "Vacuum Wavelength" in T.variables else T["wavelength"][:]
tsi = T["SSI"][:]                      # W m-2 nm-1 at 1 AU
tsis_name = os.path.basename(tsis)
def r6(a): return [float(f"{v:.6g}") for v in a]
checks = []
for name, (lo, hi, dl, bi) in BANDS.items():
    wl = np.round(np.arange(lo, hi + dl / 2, dl), 6)
    Tb = np.loadtxt(f"{lbl}/tau_{name}_lbl.txt"); hdr = open(f"{lbl}/tau_{name}_lbl.txt").readline().strip("# \n").split()
    Sn = np.loadtxt(f"{lbl}/solar_{name}_lbl.txt")
    nu = Tb[:, 0]; wl_lbl = 1e7 / nu; o = np.argsort(wl_lbl); wl_lbl = wl_lbl[o]
    tau = {k: np.interp(wl, wl_lbl, Tb[o, j]) for j, k in enumerate(hdr) if k in ("tau_co2", "tau_o2", "tau_h2o")}
    # solar: Toon line transmittance on the fine grid; continuum from TSIS-1 HSRS with the lines divided out
    Ttoon = np.interp(wl, wl_lbl, Sn[o, 2])
    sel = (twl >= lo - 3) & (twl <= hi + 3); hw, hs = twl[sel], tsi[sel] * 1e3           # -> W m-2 um-1
    # HSRS resolution is 0.005 nm here; smooth both HSRS and Toon to 0.2 nm, take the ratio as the continuum, smooth to 1 nm
    def box(y, x, width): n = max(1, int(round(width / np.median(np.diff(x))))); k = np.ones(n) / n; return np.convolve(np.pad(y, (n // 2, n - 1 - n // 2), mode="edge"), k, mode="valid")
    toon_on_h = np.interp(hw, wl, Ttoon)
    cont = box(hs, hw, 0.2) / np.maximum(box(toon_on_h, hw, 0.2), 1e-3); cont = box(cont, hw, 1.0)
    e0 = np.interp(wl, hw, cont) * Ttoon
    # ILS kernel: band-centre sample of footprint fp, resampled onto the tau spacing, unit sum
    c = H["InstrumentHeader/dispersion_coef_samp"][bi, fp, :]; i = np.arange(1, 1017); lam_pix = sum(c[k] * i**k for k in range(6)) * 1e3
    p = int(np.argmin(np.abs(lam_pix - (lo + hi) / 2)))
    dlam = H["InstrumentHeader/ils_delta_lambda"][bi, fp, p, :] * 1e3; resp = H["InstrumentHeader/ils_relative_response"][bi, fp, p, :]
    half = np.ceil(dlam.max() / dl) * dl; kgrid = np.round(np.arange(-half, half + dl / 2, dl), 6)
    kern = np.interp(kgrid, dlam, resp, left=0, right=0); wings = 1 - kern[kern >= 2e-4 * kern.max()].sum() / kern.sum()
    keep = np.where(kern >= 2e-4 * kern.max())[0]; kgrid = kgrid[keep[0]:keep[-1] + 1]; kern = kern[keep[0]:keep[-1] + 1]; kern = kern / kern.sum()
    fwhm = float(np.ptp(dlam[resp > resp.max() / 2]))
    meta = {"band": name, "band_range_nm": [lo, hi], "spacing_nm": dl, "n_points": int(len(wl)),
            "wl_start_nm": lo, "wl_step_nm": dl, "grid": "uniform: wl[i] = wl_start_nm + i*wl_step_nm, i = 0..n_points-1 (no explicit wl array, to keep the file small)",
            "resolution": "line-by-line, UNCONVOLVED (0.01 cm-1 computation, linearly interpolated to this grid); convolve with ils_{band}.json AFTER forming the radiance",
            "atmosphere": "US Standard Atmosphere 1976 (T, p), 60 layers 1013.25-0.05 hPa; H2O = 50 % RH in the troposphere (column 15.7 kg m-2); XCO2 reference 420 ppm dry; O2 0.20946; surface pressure 1013.25 hPa — scale tau_co2 and tau_o2 by psurf/1013.25",
            "line_list": "ABSCO v5.2 (CO2, O2, H2O; JPL/AER tables incl. line mixing and continua)",
            "code": "RSFraLab.github.io/oco/scripts/tau_lbl.jl (AtmosphericAbsorption.jl) + oco/scripts/make_tau_solar_hr_json.py",
            "created": datetime.date.today().isoformat(), "source": "oco/scripts/tau_lbl.jl output (tau_{band}_lbl.txt) and make_solar_lbl.py output"}
    json.dump({"meta": dict(meta, description="Vertical (airmass 1) optical depths per absorber at 1013.25 hPa; client scales tau_co2 by XCO2/420 and tau_co2, tau_o2 by psurf/1013.25"),
               "tau_co2": r6(tau["tau_co2"]), "tau_o2": r6(tau["tau_o2"]), "tau_h2o": r6(tau["tau_h2o"])}, open(f"{out}/tau_{name}.json", "w"), separators=(",", ":"))
    json.dump({"meta": dict(meta, description="Solar irradiance at 1 AU, W m-2 um-1, unconvolved: continuum from the TSIS-1 Hybrid Solar Reference Spectrum (Coddington et al. 2021; lines divided out at 0.2 nm, continuum smoothed to 1 nm) times G. Toon's disk-integrated line transmittance (solar_merged_20240731)",
                            source=f"{tsis_name}; /kiwi-data/Data/groupMembers/cfranken/solar/toon/solar_merged_20240731_600_33300_100.out.gz"),
               "e0": r6(e0)}, open(f"{out}/solar_{name}.json", "w"), separators=(",", ":"))
    json.dump({"meta": {"band": name, "ils": f"OCO-2 L1b ILS, {os.path.basename(l1b)}, footprint {fp+1}, spectral sample {p+1} at {lam_pix[p]:.3f} nm", "fwhm_nm": float(f"{fwhm:.5g}"),
                        "spacing_nm": dl, "normalization": "unit sum on this grid", "truncation": f"wings below 2e-4 of the peak dropped ({100*wings:.2f} % of the L1b kernel sum), then renormalized", "created": datetime.date.today().isoformat()},
               "delta_lambda_nm": r6(kgrid), "response": r6(kern), "fwhm_nm": float(f"{fwhm:.5g}")}, open(f"{out}/ils_{name}.json", "w"), separators=(",", ":"))
    for k, a in list(tau.items()) + [("e0", e0)]: checks.append(f"{name} {k}: n={len(a)} min={a.min():.4g} max={a.max():.4g} nan={int(np.isnan(a).sum())}")
    checks.append(f"{name}: {lo}-{hi} nm at {dl} nm ({len(wl)} pts); ILS FWHM {fwhm:.4f} nm, kernel {len(kgrid)} pts (±{kgrid.max():.3f} nm, wings dropped {100*wings:.2f} %); tau {os.path.getsize(f'{out}/tau_{name}.json')/1e3:.0f} kB, solar {os.path.getsize(f'{out}/solar_{name}.json')/1e3:.0f} kB, ils {os.path.getsize(f'{out}/ils_{name}.json')/1e3:.0f} kB; TSIS continuum at band centre {np.median(np.interp(wl, hw, cont)):.1f} W m-2 um-1")
print("\n".join(checks))
