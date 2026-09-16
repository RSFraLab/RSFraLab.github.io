const { chromium } = require('playwright');
const base = 'http://127.0.0.1:8765/';
const widgets = ['oco/widgets/spectra-explorer.html','oco/widgets/footprint-scale.html','oco/widgets/photon-path.html',
  'sif/widgets/fraunhofer-explorer.html?data=/sif/data/solar_757_771nm.json','sif/widgets/sif-map.html','sif/widgets/resolution-explorer.html','sif/widgets/spectral-explorer.html','sif/widgets/albedo-explorer.html','sif/widgets/canopy-builder.html','sif/widgets/fluorescence-spectrum.html'];
(async () => {
  const browser = await chromium.launch(); const rows = [];
  for (const w of widgets) {
    const errs = []; const row = { widget: w.split('?')[0].split('/').pop() };
    for (const cap of ['1','0']) for (const width of [890, 650]) {
      const page = await browser.newPage({ viewport: { width, height: 1400 } });
      page.on('pageerror', e => errs.push(String(e.message).slice(0,160))); page.on('console', m => { if (m.type()==='error') errs.push(m.text().slice(0,160)); });
      const url = base + w + (w.includes('?') ? '&' : '?') + (cap==='0' ? 'caption=0' : 'x=1');
      await page.goto(url, { waitUntil: 'networkidle' }); await page.waitForTimeout(900);
      row[`${width}${cap==='0'?'_nocap':''}`] = await page.evaluate(() => Math.ceil(document.querySelector('.widget').getBoundingClientRect().height));
      if (cap==='1' && width===890 && w.startsWith('oco')) await page.screenshot({ path: process.argv[2] + '/' + row.widget.replace('.html','') + '.png', fullPage: true });
      await page.close();
    }
    row.errors = [...new Set(errs)].slice(0,3); rows.push(row); console.log(JSON.stringify(row));
  }
  await browser.close();
})();
