// Click every button/chip/tab, move every slider, open every <details>, verify the PNG export downloads; report errors per widget.
const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8765/';
const widgets = ['oco/widgets/spectra-explorer.html','oco/widgets/footprint-scale.html','oco/widgets/photon-path.html',
  'sif/widgets/fraunhofer-explorer.html?data=/sif/data/solar_757_771nm.json','sif/widgets/sif-map.html','sif/widgets/resolution-explorer.html',
  'sif/widgets/spectral-explorer.html','sif/widgets/albedo-explorer.html','sif/widgets/canopy-builder.html','sif/widgets/fluorescence-spectrum.html'];
(async () => {
  const browser = await chromium.launch({ args: ['--no-sandbox'] });
  for (const w of widgets) {
    const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 890, height: 1400 } }); const page = await ctx.newPage(); const errs = [];
    page.on('pageerror', e => errs.push('pageerror: ' + String(e.message).slice(0, 140))); page.on('console', m => { if (m.type() === 'error') errs.push('console: ' + m.text().slice(0, 140)); });
    await page.goto(base + w, { waitUntil: 'networkidle' }); await page.waitForTimeout(800);
    const before = await page.evaluate(() => document.querySelector('canvas') ? document.querySelector('canvas').toDataURL().length : 0);
    // buttons (skip the PNG export, tested separately)
    const buttons = await page.$$('button, .chip, .tab, [role=button], select');
    let nb = 0, changed = 0;
    for (const b of buttons) {
      const txt = ((await b.textContent()) || '').trim(); if (/PNG/.test(txt)) continue;
      const tag = await b.evaluate(e => e.tagName);
      if (tag === 'SELECT') { const opts = await b.$$('option'); if (opts.length > 1) { await b.selectOption({ index: 1 }); nb++; } continue; }
      try { await b.click({ timeout: 2000 }); nb++; await page.waitForTimeout(120); } catch (e) { errs.push('click failed: ' + txt.slice(0, 30)); }
      const after = await page.evaluate(() => document.querySelector('canvas') ? document.querySelector('canvas').toDataURL().length : 0); if (after !== before) changed++;
    }
    // sliders
    const sliders = await page.$$('input[type=range]'); let ns = 0;
    for (const s of sliders) { const mx = await s.getAttribute('max'), mn = await s.getAttribute('min'); for (const v of [mx, mn]) { await s.evaluate((el, val) => { el.value = val; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }, v); await page.waitForTimeout(80); } ns++; }
    // details
    const det = await page.$$('details'); for (const d of det) await d.evaluate(e => e.open = true);
    // checkboxes / radios
    const cbs = await page.$$('input[type=checkbox], input[type=radio]'); for (const c of cbs) { try { await c.click({ timeout: 1000 }); } catch (e) { errs.push('checkbox click failed'); } }
    await page.waitForTimeout(300);
    // PNG export must trigger a download
    let dl = 'no PNG button';
    const png = await page.$('button:has-text("PNG")');
    if (png) { try { const [d] = await Promise.all([page.waitForEvent('download', { timeout: 6000 }), png.click()]); dl = `download ok (${d.suggestedFilename()})`; } catch (e) { dl = 'DOWNLOAD FAILED'; } }
    console.log(JSON.stringify({ widget: w.split('?')[0].split('/').pop(), buttons: nb, canvas_redraws: changed, sliders: ns, details: det.length, toggles: cbs.length, export: dl, errors: [...new Set(errs)].slice(0, 4) }));
    await ctx.close();
  }
  await browser.close();
})();
