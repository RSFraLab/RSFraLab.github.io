# oco/data — static inputs for the CO₂ measurement page widgets

All files are plain JSON, numbers rounded to 6 significant digits, each with a `meta` block
(`source`, `created`, `description`, …). Produced 2026-09-16 on curry with the scripts in
`oco/scripts/` (Python: conda env `ee`, Python 3.12; Julia: the Google-RT project environment,
AtmosphericAbsorption.jl with ABSCO v5.2). Re-run order and exact commands are at the bottom.

## 1. Spectra explorer

| file | contents | check |
|---|---|---|
| `tau_aband.json` (134 kB) | 758–772 nm, 4000 pts; `tau_o2` (`tau_co2` = 0) `tau_h2o` | tau_o2 n=4000 min=1.643e-4 max=52.92 nan=0; tau_h2o max=9.76e-4; ILS FWHM 0.0418 nm |
| `tau_wco2.json` (137 kB) | 1590–1621 nm; `tau_co2` at 420 ppm, `tau_h2o` (`tau_o2` = 0) | tau_co2 min=5.705e-5 max=0.4712; tau_h2o min=1.264e-4 max=0.03999; nan=0; ILS FWHM 0.0775 nm |
| `tau_sco2.json` (173 kB) | 2042–2082 nm; `tau_co2`, `tau_h2o`, `tau_ch4` | tau_co2 min=0.01017 max=8.833; tau_h2o max=0.8333; tau_ch4 max=3.0e-5; nan=0; ILS FWHM 0.1011 nm |
| `solar_{aband,wco2,sco2}.json` (64 kB each) | `e0` W m⁻² µm⁻¹ at 1 AU on the same `wl` | aband 738.4–1252; wco2 133.0–208.1; sco2 73.47–95.3; nan=0 |
| `sounding_oco2.json` (65 kB) | one OCO-2 L1b sounding, 3 bands × 1016 samples, L2 values | aband 757.66–772.57 nm, max 62.31 W m⁻² sr⁻¹ µm⁻¹, good 858/1016; wco2 1590.58–1621.74, max 14.32, good 878; sco2 2043.06–2083.20, max 5.518, good 855 |

Optical depths: vertical (airmass 1), US Standard Atmosphere 1976 (T, p) on 60 layers from
1013.25 to 0.05 hPa, H₂O = 50 % relative humidity in the troposphere (column 15.7 kg m⁻²),
XCO₂ 420 ppm (dry), O₂ 0.20946, CH₄ 1.9 ppm. CO₂, O₂, H₂O cross sections from **ABSCO v5.2**
(`~/data/ABSCO/v5.2_final/*_v52.hdf`, pressure/temperature/H₂O-broadener interpolation via
`AtmosphericAbsorption.compute_cross_section`); CH₄ line-by-line from the HITRAN2020 `.par`
artifact (Voigt, 40 cm⁻¹ cutoff) because no ABSCO CH₄ table is on disk. Computed at 0.01 cm⁻¹,
**convolved at that resolution** with the OCO-2 L1b instrument line shape (per-spectral-sample
`ils_delta_lambda` / `ils_relative_response`, footprint 4, of granule
`oco2_L1bScND_53642a_240801_B11205r_240906004756.h5`), then linearly interpolated to 4000
points per band. Note the client's `exp(-m·tau_conv)` is an approximation of the ILS-convolved
transmittance (requested form); CH₄ in this band is negligible (τ ≤ 3e-5) and can be dropped.

Solar irradiance: Geoff Toon's disk-integrated solar transmittance
(`solar_merged_20240731_600_33300_100`, 0.01 cm⁻¹) × Planck continuum at 5772 K scaled by
(R☉/AU)². The Planck continuum is within ~1 % of measured irradiance at 0.76 µm but ~10 % low at
1.6 µm; stated in `meta`.

Sounding: OCO-2 `2024080120532372`, 2024-08-01 20:53:34 UTC, nadir, footprint 2, Railroad
Valley playa (38.382 N, 115.857 W), SZA 24.9°, VZA 0.52°, L2 Lite v11.2 XCO₂ 422.89 ppm,
albedo 0.353 / 0.409 / 0.394, surface pressure 857 hPa, AOD 0.071, quality flag 0. Radiance
converted from photon units with hc/λ; wavelengths from the footprint's L1b dispersion polynomial
(1-based sample index); `good` = `bad_sample_list == 0`. **OCO-2 measures one linear
polarization**, so the L1b radiance is ≈ ½ of the total intensity of an unpolarized scene
(`meta.polarization_factor = 0.5`; the explorer scales the forward model accordingly).

## 2. Footprint scale explorer

| file | contents | check |
|---|---|---|
| `track_oco2_orbit.json` (6 kB) | orbit 53380, 2024-07-14, nadir; sub-satellite point every 10 s | 280 points, 20:39:55–21:26:25 UTC, lon −176.6…176.4 (crosses the dateline), lat −58.3…81.8 |
| `footprints_oco2_la.json` (71 kB) | 100 consecutive nadir frames over the LA basin (centre 34.125 N, 117.898 W), 8 footprints × 4 O₂-band vertices | 755 of 800 footprints have vertices (45 are fill values in the L1b file → `null`); **medians: cross-track 1.085 km, along-track 2.276 km, swath 8.67 km** |
| `footprints_oco3_sam_la.json` (209 kB) | OCO-3 SAM `fossil0005` "fossil_Los_Angeles_USA", 2022-02-18, all Lite soundings grouped by frame and swath | 305 frames, 2199 footprints, 8 swaths, 1641 good-quality, median XCO₂ 419.4 ppm; medians 2.25 × 2.34 km |
| `basemaps.json` + `img/basemap_{orbit,200km,12km,12km_oco3}.jpg` | stitched OpenStreetMap standard raster tiles (Web Mercator), bounds in the JSON | orbit z2 1024×800 (lon −300…60), 200 km z9 1100×760 (253 m/px), 12 km z13 1100×760 (15.8 m/px); © OpenStreetMap contributors (ODbL) |

The footprint sizes are geodesic side lengths of the L1b vertex parallelograms (short pair =
across track, long pair = along track); swath = separation of footprint 1 and 8 centroids + one
footprint width. **They come out at 1.09 / 2.28 / 8.7 km, not the often-quoted 1.29 / 2.25 /
10.3 km** — the along-track size agrees, the across-track width from the vertices is ~15 %
smaller; reported as measured, not adjusted. The OCO-3 file carries only the soundings that
passed L2 pre-screening (the Lite product), not every L1b sounding of the SAM.

## 3. Surface albedo

| file | contents | check |
|---|---|---|
| `albedo_surfaces.json` (19 kB) | 400–2200 nm at 5 nm, five ECOSTRESS 1.0 spectra + `band_means` | ocean 0.017–0.031; desert 0.003–0.447; snow 0.035–0.993; conifer 0.053–0.701; dry_grass 0.157–0.676; nan=0 |

Entries (local copy of the ECOSTRESS library zips, `/kiwi-data/Data/groupMembers/sanghavi/ECOSTRESSlib`):
ocean → `water.tapwater.none.liquid.all.tapwater.jhu.becknic` (**stand-in**: no seawater entry
in the local copy; liquid water, near-zero SWIR, no glint), desert →
`soil.aridisol.calciorthid.none.all.84p3721.jhu.becknic` (light yellowish-brown arid loam), snow →
`water.snow.finegranular.fine.all.fine_snw_.jhu.becknic`, conifer →
`vegetation.tree.pinus.ponderosa.vswir.vh067.ucsb.asd`, dry_grass →
`nonphotosyntheticvegetation.leaves.unknown.unknown.all.drygrass.jhu.becknic`. Band means:
A-band / weak CO₂ / strong CO₂ = ocean 0.026/0.021/0.019, desert 0.372/0.434/0.417,
snow 0.955/0.156/0.052, conifer 0.652/0.261/0.112, dry grass 0.517/0.597/0.452.

## 4b. Hero image

`img/xco2_hero.jpg` (2400 × 1080, 148 kB): per-cell **median** XCO₂ of all good-quality OCO-2
Lite v11.2 soundings of 2023 on a 3° grid (29.0 M soundings, 5855 cells), nearest-neighbour
gap-filled, σ = 0.7 cell smoothing, drawn over land only (ocean left dark), Antarctica masked,
bold light coastlines, Robinson projection, colour range 413.4–420.8 ppm. There is no OCO L3
product on disk, so this is our own composite; annual medians at high latitudes are biased low by
summer-only sampling (the blue Siberia).

## Reproduce

```bash
PY=~/.conda/envs/ee/bin/python; S=~/code/gitHub/RSFraLab.github.io; W=/path/to/work
# 1. line-by-line optical depths (Julia, Google-RT environment) and solar irradiance
julia -t 8 $S/oco/scripts/tau_lbl.jl $W                       # tau_{aband,wco2,sco2}_lbl.txt
$PY $S/oco/scripts/make_solar_lbl.py /kiwi-data/Data/groupMembers/cfranken/solar/toon/solar_merged_20240731_600_33300_100.out.gz $W
L1B=~/data/OCO2_L1b_full/oco2_L1bScND_53642a_240801_B11205r_240906004756.h5   # GES DISC OCO2_L1B_Science.11.2r/2024/214
$PY $S/oco/scripts/make_tau_solar_json.py $W $S/oco/data $L1B 3
$PY $S/oco/scripts/make_sounding_json.py $L1B /kiwi-data/Data/satellite/OCO2/L2_Lite_FP/11.2r/raw/2024/oco2_LtCO2_240801_B11211Ar_240924224233s.nc4 2024080120532372 $S/oco/data/sounding_oco2.json "Railroad Valley playa, Nevada"
# 2. footprints and track (local O2-band L1bSc granule), OCO-3 SAM (Lite), basemaps
$PY $S/oco/scripts/make_footprints_json.py /kiwi-data/Data/satellite/OCO2/L1bSc/11.2r/raw/2024/196/oco2_L1bScND_53380a_240714_B11205r_240814182247.h5 $S/oco/data 34.05 -118.25
$PY $S/oco/scripts/make_oco3_sam_json.py /kiwi-data/Data/satellite/OCO3/L2_Lite_FP/11r/raw/2022/oco3_LtCO2_220218_B11072Ar_240915212336s.nc4 fossil0005 $S/oco/data/footprints_oco3_sam_la.json
$PY $S/oco/scripts/make_basemaps.py $S/oco/img $S/oco/data/basemaps.json
# 3. albedo
$PY $S/oco/scripts/make_albedo_surfaces.py <dir with the ECOSTRESS .spectrum.txt files> $S/oco/data/albedo_surfaces.json
# 4b. hero
$PY $S/oco/scripts/make_xco2_composite.py 2023 $W/xco2_2023_3deg.npz 3 && $PY $S/oco/scripts/make_xco2_hero.py $W/xco2_2023_3deg.npz $S/oco/img/xco2_hero.jpg
```
