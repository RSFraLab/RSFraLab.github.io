# RSFraLab.github.io
The Lab Website built using Quarto:
https://rsfralab.github.io/

## Publications sync (ORCID)

This site can generate new publication entries directly from ORCID and Crossref.

### One-time setup

- Install Python dependencies: `pip install requests bibtexparser`

### Sync new publications

```
python scripts/orcid_sync.py --orcid YOUR-ORCID-ID --full
```

This will:

- Read your ORCID works
- Pull metadata from Crossref using DOIs
- Rebuild publications/publications.bib from ORCID
- Optionally create QMD files under publications/ (unless --no-qmd)

### ORCID-only workflow

Use ORCID as the single source of truth and regenerate the BibTeX each time:

```
python scripts/orcid_sync.py --orcid YOUR-ORCID-ID --full
```

To skip QMD creation:

```
python scripts/orcid_sync.py --orcid YOUR-ORCID-ID --full --no-qmd
```

### Preprints

By default, preprints are excluded when generating QMDs from the BibTeX file. To include them:

```
python scripts/parsePubs.py --bib publications/publications.bib --out-dir publications --include-preprints
```

Preprints are written to publications/preprints and shown on preprints.qmd.

### PDF links

If you want a PDF link to appear for a paper, place a PDF at:

```
publications/pdfs/<generated-filename>.pdf
```

The listing template will show a “PDF” link when `materials` is set. You can also manually set `materials` in any publication QMD front matter to an external URL.

### External PDF hosting (recommended for large files)

Use a URL template so new entries get a PDF link automatically:

```
python scripts/orcid_sync.py --orcid YOUR-ORCID-ID --materials-template "https://your-server.org/papers/{slug}.pdf"
```

Template variables:

- `{slug}` = generated filename without `.qmd`
- `{doi}` = DOI

### Auto-discover and download PDFs (OA only)

If you want to auto-find open-access PDFs, use Unpaywall (requires email):

```
python scripts/orcid_sync.py --orcid YOUR-ORCID-ID --unpaywall-email you@caltech.edu --download-pdfs
```

This downloads OA PDFs into publications/pdfs and sets `materials` to that local path.
