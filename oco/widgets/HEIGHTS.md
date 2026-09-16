# Widget heights for fixed-height iframes

Measured 2026-09-16 with headless Chromium (Playwright 1.55, viewport height 1400) as the
rendered height of the `.widget` card, at the two Caltech CMS column widths. "no caption" =
`?caption=0` (the CMS writes the caption next to the iframe). Collapsible `<details>` sections
were closed; opening them adds their content height (fraunhofer, resolution, canopy), so either
keep them closed on the Caltech page or add ~150 px. No widget reported a console error.

| widget | 890 px | 890 px, no caption | 650 px | 650 px, no caption | suggested iframe height (no caption) |
|---|---|---|---|---|---|
| oco/widgets/spectra-explorer.html (three stacked bands, 2026-09-16 rev.) | 865 | 795 | 987 | 929 | 810 (890) / 945 (650) |
| oco/widgets/footprint-scale.html (2026-09-16 rev., longer readouts) | ~740 | 621 | ~745 | 621 | 635 / 635 |
| oco/widgets/photon-path.html | 672 | 535 | 750 | 613 | 550 / 630 |
| sif/widgets/fraunhofer-explorer.html (`?data=/sif/data/solar_757_771nm.json`) | 691 | 603 | 719 | 631 | 620 / 650 |
| sif/widgets/sif-map.html | 717 | 558 | 629 | 470 | 570 / 480 |
| sif/widgets/resolution-explorer.html | 951 | 734 | 1030 | 794 | 750 / 810 |
| sif/widgets/spectral-explorer.html | 677 | 596 | 709 | 628 | 610 / 640 |
| sif/widgets/albedo-explorer.html | 489 | 414 | 489 | 414 | 430 / 430 |
| sif/widgets/canopy-builder.html | 1035 | 896 | 1095 | 956 | 910 / 970 |
| sif/widgets/fluorescence-spectrum.html | 576 | 476 | 636 | 536 | 490 / 550 |

Add ~12 px of slack to the suggested values for font rendering differences on the Caltech
template. All widgets accept `?theme=light|dark` (light is the default: they no longer follow the
visitor's OS dark-mode preference when embedded cross-origin) and `?caption=0`, and every widget
has a `PNG ↓` button that exports the plot at 2× resolution (the SIF widgets composite all their
canvases; the OCO widgets re-render the chart offscreen).

Reproduce: `python3 -m http.server 8765` in the site root, then
`node test_widgets.js <screenshot dir>` (see `oco/scripts/measure_heights.js`).
