#!/usr/bin/env python3
"""Solar irradiance at line-by-line resolution for the three OCO bands:
E0(nu) = T_solar(nu) * pi*B_lambda(T_eff) * (R_sun/1 AU)^2   [W m^-2 um^-1 at 1 AU]
T_solar: G. Toon's disk-integrated solar transmittance (solar_merged_20240731_600_33300_100), 0.01 cm^-1.
Continuum: Planck at T_eff = 5772 K (IAU nominal); |E0 - TSIS-1 HSRS| is a few percent in these bands,
adequate for the illustrative widget (stated in meta). Writes nu, E0 per band as text for the ILS step."""
import sys, gzip, numpy as np
toon, out = sys.argv[1], sys.argv[2]
h, c, k = 6.62607015e-34, 2.99792458e8, 1.380649e-23
Teff, Rsun, AU = 5772.0, 6.957e8, 1.495978707e11
bands = {"aband": (12950.0, 13200.0), "wco2": (6165.0, 6295.0), "sco2": (4800.0, 4900.0)}
nu_all, t_all = [], []
with gzip.open(toon, "rt") as f:
    for i, line in enumerate(f):
        if i < 3: continue
        p = line.split()
        if len(p) == 2:
            nu_all.append(float(p[0])); t_all.append(float(p[1]))
nu_all = np.array(nu_all); t_all = np.array(t_all)
print("toon rows", len(nu_all), nu_all[0], nu_all[-1])
for name, (a, b) in bands.items():
    nu = np.arange(a, b + 1e-9, 0.01)
    T = np.interp(nu, nu_all, t_all)
    lam = 1e-2 / nu                                   # m
    B = 2*h*c**2/lam**5 / (np.exp(h*c/(lam*k*Teff)) - 1)   # W m^-2 m^-1 sr^-1
    E0 = np.pi * B * (Rsun/AU)**2 * 1e-6              # W m^-2 um^-1
    np.savetxt(f"{out}/solar_{name}_lbl.txt", np.c_[nu, E0*T, T], header="nu_cm-1 E0_Wm-2um-1 T_solar", fmt="%.6g")
    print(name, "E0 continuum W m-2 um-1 at band centre:", f"{np.median(E0):.1f}", "min T", f"{T.min():.3f}")
