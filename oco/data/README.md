# oco/data — static inputs for the CO₂ measurement page widgets

All files are plain JSON, numbers rounded to 6 significant digits, each with a `meta` block
(`source`, `created`, `description`, …). Produced 2026-09-16 on curry with the scripts in
`oco/scripts/` (Python: conda env `ee`, Python 3.12; Julia: the Google-RT project environment,
AtmosphericAbsorption.jl with ABSCO v5.2). Re-run order and exact commands are at the bottom.

## 1. Spectra explorer (round 2, 2026-09-16: unconvolved high-resolution inputs)

| file | contents | check |
|---|---|---|
| `tau_aband.json` (360 kB) | 758–772 nm, 0.001 nm, 14 001 pts, **unconvolved**; `tau_o2`, `tau_h2o` (`tau_co2` = 0) | tau_o2 min=1.466e-4 max=528.9; tau_h2o max=3.667e-3; nan=0 |
| `tau_wco2.json` (204 kB) | 1590–1621 nm, 0.004 nm, 7 751 pts; `tau_co2` at 420 ppm, `tau_h2o` | tau_co2 min=4.917e-5 max=2.131; tau_h2o max=0.1373; nan=0 |
| `tau_sco2.json` (189 kB) | 2042–2082 nm, 0.005 nm, 8 001 pts; `tau_co2`, `tau_h2o` (CH₄ dropped, τ < 3e-5) | tau_co2 min=7.264e-3 max=38.14; tau_h2o max=2.791; nan=0 |
| `solar_{aband,wco2,sco2}.json` (112 / 62 / 65 kB) | `e0` W m⁻² µm⁻¹ at 1 AU, unconvolved, same grids | 141.9–1265; 124.3–254.5; 71.47–107.9; nan=0; TSIS continuum at band centre 1245.5 / 250.7 / 103.7 |
| `ils_{aband,wco2,sco2}.json` (13 / 8 / 11 kB) | OCO-2 L1b ILS kernel, footprint 4, band-centre sample, on the tau spacing, unit sum | FWHM 0.0415 / 0.0774 / 0.1012 nm; 583 / 351 / 547 pts (±0.28 / ±0.70 / ±1.37 nm); wings < 2e-4 of peak dropped (0.06 / 0.13 / 0.00 % of the sum) |
| `sounding_oco2.json` (65 kB) | one OCO-2 L1b sounding, 3 bands × 1016 samples, L2 values | aband 757.66–772.57 nm, max 62.31 W m⁻² sr⁻¹ µm⁻¹, good 858/1016; wco2 1590.58–1621.74, max 14.32, good 878; sco2 2043.06–2083.20, max 5.518, good 855 |

Grids are uniform and stored compactly: `wl[i] = meta.wl_start_nm + i·meta.wl_step_nm`, `i = 0 … meta.n_points−1`
(no `wl` array; this keeps the A-band file under 400 kB). Optical depths are vertical (airmass 1) at 1013.25 hPa
for the US Standard Atmosphere 1976 (60 layers, H₂O 50 % RH in the troposphere, 15.7 kg m⁻²), XCO₂ 420 ppm dry,
O₂ 0.20946, from **ABSCO v5.2** (`~/data/ABSCO/v5.2_final`) at 0.01 cm⁻¹, linearly interpolated to the grids (the
0.01 cm⁻¹ computation is finer than every grid: 0.0006 / 0.0025 / 0.0042 nm). **The client does the physics in
the right order**: `T = exp(−m·[psurf/1013.25·(XCO₂/420·tau_co2 + tau_o2) + tau_h2o])`, `L = E₀·cos(SZA)·a/π·T`
at full resolution, then convolution with the ILS kernel, then sampling every 4th point for drawing; a
surface-pressure slider (700–1030 hPa) is set to the L2 value when the sounding overlay is on.

Solar irradiance: **TSIS-1 Hybrid Solar Reference Spectrum** (Coddington et al. 2021; v2 0.005 nm file,
`hybrid_reference_spectrum_p005nm_resolution_c2022-11-30_with_unc.nc`) provides the continuum — its lines are
divided out with Toon's transmittance at 0.2 nm and the ratio smoothed to 1 nm — and Geoff Toon's disk-integrated
transmittance (`solar_merged_20240731_600_33300_100`, 0.01 cm⁻¹) provides the Fraunhofer structure.

**Line-depth check** (`oco/scripts/check_line_depths.py`: the shipped sounding forward-modelled exactly as the
widget does, at the L2 XCO₂ 422.89 ppm, albedos 0.353 / 0.409 / 0.394, psurf 857.9 hPa, SZA 24.9°, polarization
factor 0.5; depth = 1 − L/continuum envelope, averaged over good samples):

| band | mean line depth measured | mean line depth model | model − measured | continuum meas/model |
|---|---|---|---|---|
| A-band | 0.291 | 0.307 | +0.016 | 0.980 |
| weak CO₂ | 0.078 | 0.078 | +0.000 | 0.959 |
| strong CO₂ | 0.301 | 0.314 | +0.013 | 0.985 |

(Round 1, convolved-τ form with Planck continuum: 0.437 / 0.070 / 0.419 vs measured 0.317 / 0.060 / 0.321 and
continuum ratios 0.97 / 1.18 / 1.07.) All bands are now within the 0.02 target and no fudge factor is applied.

Sounding: OCO-2 `2024080120532372`, 2024-08-01 20:53:34 UTC, nadir, footprint 2, Railroad Valley playa
(38.382 N, 115.857 W), SZA 24.9°, VZA 0.52°, L2 Lite v11.2 XCO₂ 422.89 ppm, albedo 0.353 / 0.409 / 0.394,
surface pressure 857.9 hPa, AOD 0.071 (`meta.aod_l2`), quality flag 0 (`meta.quality_flag`). Radiance converted
from photon units with hc/λ; wavelengths from the footprint's L1b dispersion polynomial (1-based sample index);
`good` = `bad_sample_list == 0`. **OCO-2 measures one linear polarization**, so the L1b radiance is ≈ ½ of the total
intensity of an unpolarized scene (`meta.polarization_factor = 0.5`).

## 2. Footprint scale explorer

| file | contents | check |
|---|---|---|
| `track_oco2_orbit.json` (6 kB) | orbit 53380, 2024-07-14, nadir; sub-satellite point every 10 s | 280 points, 20:39:55–21:26:25 UTC, lon −176.6…176.4 (crosses the dateline), lat −58.3…81.8 |
| `footprints_oco2_la.json` (72 kB) | 100 consecutive nadir frames over the LA basin (centre 34.125 N, 117.898 W), 8 footprints × 4 O₂-band vertices | 755 of 800 footprints have vertices (45 are fill values in the L1b file → `null`); **medians: 1.085 km along the slit × 2.276 km along track, 8.67 km for the eight footprints end to end; slit 11.7° from the ground track** |
| `footprints_oco3_sam_la.json` (209 kB) | OCO-3 SAM `fossil0005` "fossil_Los_Angeles_USA", 2022-02-18, all Lite soundings grouped by frame and swath | 305 frames, 2199 footprints, 8 swaths, 1641 good-quality, median XCO₂ 419.4 ppm; medians 2.25 × 2.34 km |
| `basemaps.json` + `img/basemap_{orbit,200km,12km,12km_oco3}.jpg` | stitched OpenStreetMap standard raster tiles (Web Mercator), bounds in the JSON | orbit z2 1024×800 (lon −300…60), 200 km z9 1100×760 (253 m/px), 12 km z13 1100×760 (15.8 m/px); © OpenStreetMap contributors (ODbL) |

**Geometry finding (2026-09-16).** OCO-2 does not keep its slit across the ground track: the
slit direction rotates along the orbit (measured on three granules: ~85° from the track near the
equator, ~70° at 28°S, only ~10° at 34°N, ~35° at 62°N), so over Los Angeles the eight footprints of
a frame are stacked nearly **along** the track and the 8.7 km "swath" lies along the slit. Footprint
dimensions are geodesic side lengths of the L1b vertex parallelograms: the short side is the pitch
along the slit (1.09 km, nominal 1.29 km), the long side the along-track smear per ⅓-s frame
(2.28 km, nominal 2.25 km); each footprint is only ~0.6 km wide across the slit. The along-slit
values are ~15 % below the often-quoted 1.29 / 10.3 km; reported as measured, not adjusted. The
widget draws one frame explicitly with its eight numbered footprints and states the slit angle. The
OCO-3 file carries only the soundings that passed L2 pre-screening (the Lite product), not every L1b
sounding of the SAM.

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

`img/xco2_hero.jpg` (2400 × 1080, dark background, < 400 kB): **JJA 2019 mean XCO₂ from the AtmosTransport CATRINE
C90 run** (`co2_natural`, dry-air-mass-weighted column, 8 snapshots/day × 92 days, nearest-cell regridded to 0.25°,
σ = 1 cell smoothing, dark-blue → gold ramp, subtle coastlines, no axes/labels). `img/xco2_hero_jja2019.gif` is the
same field day by day at 12 UTC (92 frames). An observation-based alternative is produced by
`make_xco2_composite.py` + `make_xco2_hero.py` (OCO-2 Lite v11.2, JJA 2021–2024, 1° medians incl. ocean glint,
σ = 2 cells, Antarctica removed) — smoother than round 1 but still streaky from the glint sampling, which is why the
model field is used.

## Reproduce

```bash
PY=~/.conda/envs/ee/bin/python; S=~/code/gitHub/RSFraLab.github.io; W=/path/to/work
# 1. line-by-line optical depths (Julia, Google-RT environment) and solar irradiance
julia -t 8 $S/oco/scripts/tau_lbl.jl $W                       # tau_{aband,wco2,sco2}_lbl.txt
$PY $S/oco/scripts/make_solar_lbl.py /kiwi-data/Data/groupMembers/cfranken/solar/toon/solar_merged_20240731_600_33300_100.out.gz $W
L1B=~/data/OCO2_L1b_full/oco2_L1bScND_53642a_240801_B11205r_240906004756.h5   # GES DISC OCO2_L1B_Science.11.2r/2024/214
$PY $S/oco/scripts/make_tau_solar_hr_json.py $W $S/oco/data $L1B 3 ~/data/solar/hybrid_reference_spectrum_p005nm_resolution_c2022-11-30_with_unc.nc   # TSIS-1 HSRS v2 from LASP LISIRD
$PY $S/oco/scripts/check_line_depths.py $S/oco/data
$PY $S/oco/scripts/make_sounding_json.py $L1B /kiwi-data/Data/satellite/OCO2/L2_Lite_FP/11.2r/raw/2024/oco2_LtCO2_240801_B11211Ar_240924224233s.nc4 2024080120532372 $S/oco/data/sounding_oco2.json "Railroad Valley playa, Nevada"
# 2. footprints and track (local O2-band L1bSc granule), OCO-3 SAM (Lite), basemaps
$PY $S/oco/scripts/make_footprints_json.py /kiwi-data/Data/satellite/OCO2/L1bSc/11.2r/raw/2024/196/oco2_L1bScND_53380a_240714_B11205r_240814182247.h5 $S/oco/data 34.05 -118.25
$PY $S/oco/scripts/make_oco3_sam_json.py /kiwi-data/Data/satellite/OCO3/L2_Lite_FP/11r/raw/2022/oco3_LtCO2_220218_B11072Ar_240915212336s.nc4 fossil0005 $S/oco/data/footprints_oco3_sam_la.json
$PY $S/oco/scripts/make_basemaps.py $S/oco/img $S/oco/data/basemaps.json
# 3. albedo
$PY $S/oco/scripts/make_albedo_surfaces.py <dir with the ECOSTRESS .spectrum.txt files> $S/oco/data/albedo_surfaces.json
# 4b. hero (model field) and the observation-based alternative
$PY $S/oco/scripts/make_model_xco2_hero.py ~/data/AtmosTransport/output/catrine_c90_2019_rt_co2 $S/oco/img/xco2_hero.jpg $S/oco/img/xco2_hero_jja2019.gif
$PY $S/oco/scripts/make_xco2_composite.py $W/xco2_jja_2021_2024_1deg.npz 1 2021-2024 6,7,8 && $PY $S/oco/scripts/make_xco2_hero.py $W/xco2_jja_2021_2024_1deg.npz $W/xco2_hero_obs.jpg
```
