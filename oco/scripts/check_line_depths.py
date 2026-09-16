#!/usr/bin/env python3
"""Forward-model the shipped sounding exactly as the widget does (high-res tau -> exp(-m*tau) -> x E0 mu0 a/pi -> ILS
convolution -> sample at the sounding wavelengths, polarization factor) at the L2 XCO2, albedo and surface pressure,
and compare mean line depth and continuum with the measurement. Prints a Markdown table."""
import sys, json, numpy as np
D = sys.argv[1]; S = json.load(open(f"{D}/sounding_oco2.json")); m = S["meta"]
def cont_env(wl, y, win_nm):  # running maximum then light smoothing -> continuum envelope
    n = max(3, int(win_nm / np.median(np.diff(wl)))); out = np.empty_like(y)
    for i in range(len(y)): out[i] = np.max(y[max(0, i - n // 2): i + n // 2 + 1])
    k = np.ones(n) // 1 / n; return np.convolve(np.pad(out, (n // 2, n - 1 - n // 2), mode="edge"), k, mode="valid")
rows = []
for band in ["aband", "wco2", "sco2"]:
    t = json.load(open(f"{D}/tau_{band}.json")); s = json.load(open(f"{D}/solar_{band}.json")); k = json.load(open(f"{D}/ils_{band}.json"))
    wl = t["meta"]["wl_start_nm"] + t["meta"]["wl_step_nm"] * np.arange(t["meta"]["n_points"]); mu0 = np.cos(np.radians(m["sza"])); am = 1 / mu0 + 1 / np.cos(np.radians(m["vza"])); ps = m["surface_pressure_hpa"] / 1013.25
    tau = ps * (m["xco2_l2_ppm"] / 420 * np.array(t["tau_co2"]) + np.array(t["tau_o2"])) + np.array(t["tau_h2o"])
    L_hr = np.array(s["e0"]) * mu0 * m["albedo_l2"][band] / np.pi * np.exp(-am * tau)
    L_c = np.convolve(L_hr, np.array(k["response"]), mode="same") * m["polarization_factor"]
    swl = np.array(S[band]["wl"]); rad = np.array(S[band]["radiance"]); good = np.array(S[band]["good"]) & (swl > wl[0] + 0.3) & (swl < wl[-1] - 0.3)
    mod = np.interp(swl, wl, L_c)
    win = {"aband": 1.0, "wco2": 1.5, "sco2": 1.5}[band]
    ce_meas = cont_env(swl[good], rad[good], win); ce_mod = cont_env(swl[good], mod[good], win)
    d_meas = np.mean(1 - rad[good] / ce_meas); d_mod = np.mean(1 - mod[good] / ce_mod); cr = np.mean(ce_meas) / np.mean(ce_mod)
    rows.append(f"| {band} | {d_meas:.3f} | {d_mod:.3f} | {d_mod - d_meas:+.3f} | {cr:.3f} |")
print("| band | mean line depth measured | mean line depth model | model − measured | continuum meas/model |")
print("|---|---|---|---|---|"); print("\n".join(rows))
print(f"(XCO2 {m['xco2_l2_ppm']:.2f} ppm, albedos {m['albedo_l2']}, psurf {m['surface_pressure_hpa']:.1f} hPa, SZA {m['sza']:.1f}, polarization factor {m['polarization_factor']})")
