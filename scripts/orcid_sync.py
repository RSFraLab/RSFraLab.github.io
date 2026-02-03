import argparse
import html
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

import requests

try:
    import bibtexparser
    from bibtexparser.bibdatabase import BibDatabase
    from bibtexparser.bwriter import BibTexWriter
except Exception:  # pragma: no cover
    bibtexparser = None
    BibDatabase = None
    BibTexWriter = None

ORCID_API = "https://pub.orcid.org/v3.0"
CROSSREF_API = "https://api.crossref.org/works"
UNPAYWALL_API = "https://api.unpaywall.org/v2"


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def strip_jats(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def load_existing_dois(publications_dir: Path) -> set:
    dois = set()
    for qmd in publications_dir.rglob("*.qmd"):
        try:
            content = qmd.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in content.splitlines():
            if line.lower().startswith("doi:"):
                doi = line.split(":", 1)[1].strip().strip('"')
                if doi:
                    dois.add(doi.lower())
                break
    return dois


def load_bib_dois(bib_path: Optional[Path]) -> set:
    if not bib_path or not bib_path.exists() or bibtexparser is None:
        return set()
    with bib_path.open("r", encoding="utf-8") as f:
        bib_database = bibtexparser.load(f)
    dois = set()
    for entry in bib_database.entries:
        doi = entry.get("doi", "")
        if doi:
            dois.add(doi.lower())
    return dois


def get_orcid_works(orcid: str) -> dict:
    headers = {"Accept": "application/vnd.orcid+json"}
    response = requests.get(f"{ORCID_API}/{orcid}/works", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def extract_dois(works: dict) -> dict:
    dois = {}
    for group in works.get("group", []):
        summaries = group.get("work-summary", [])
        for summary in summaries:
            external_ids_block = summary.get("external-ids") or {}
            external_ids = external_ids_block.get("external-id", []) if isinstance(external_ids_block, dict) else []
            for ext in external_ids:
                if ext.get("external-id-type", "").lower() == "doi":
                    doi = (ext.get("external-id-value") or "").strip()
                    if doi:
                        dois[doi.lower()] = (summary.get("type") or "").strip()
    return dois


def fetch_crossref(doi: str) -> dict:
    response = requests.get(f"{CROSSREF_API}/{doi}", timeout=30)
    response.raise_for_status()
    return response.json().get("message", {})


def fetch_unpaywall(doi: str, email: str) -> dict:
    response = requests.get(f"{UNPAYWALL_API}/{doi}", params={"email": email}, timeout=30)
    response.raise_for_status()
    return response.json()


def build_record(message: dict, doi: str, orcid_type: str = "") -> dict:
    title = (message.get("title") or [""])[0]
    container = (message.get("container-title") or [""])[0]
    issued = message.get("issued", {}).get("date-parts", [[""]])[0]
    year = issued[0] if issued else ""

    authors = []
    authors_bib = []
    for author in message.get("author", []):
        given = author.get("given", "").strip()
        family = author.get("family", "").strip()
        full = " ".join([part for part in [family, given] if part])
        full_bib = ", ".join([part for part in [family, given] if part])
        if full:
            authors.append(full)
        if full_bib:
            authors_bib.append(full_bib)
    author_str = " and ".join(authors)
    author_bib = " and ".join(authors_bib)

    abstract = strip_jats(message.get("abstract", ""))

    return {
        "title": title,
        "author": author_str,
        "author_bib": author_bib,
        "type": "article",
        "year": year,
        "publication": container,
        "doi": doi,
        "materials": "",
        "abstract": abstract,
        "orcid_type": orcid_type,
    }


def choose_filename(record: dict) -> str:
    first_author = record.get("author", "").split(" and ")[0]
    surname = first_author.split(" ")[0] if first_author else "work"
    year = record.get("year") or "0000"
    first_word = (record.get("title") or "").split(" ")[0]
    base = slugify(f"{surname}{year}{first_word}") or slugify(record.get("doi", ""))
    return f"{base}.qmd"


def resolve_materials(
    record: dict,
    materials_template: Optional[str],
    unpaywall_email: Optional[str],
) -> str:
    if materials_template:
        doi = record.get("doi", "")
        slug = Path(record.get("_filename", "")).stem
        return materials_template.format(doi=doi, slug=slug)

    if unpaywall_email:
        try:
            up = fetch_unpaywall(record.get("doi", ""), unpaywall_email)
        except Exception:
            return ""
        best = up.get("best_oa_location") or {}
        pdf_url = best.get("url_for_pdf") or ""
        return pdf_url

    return ""


def write_qmd(path: Path, record: dict) -> None:
    props = ["title", "author", "type", "year", "publication", "doi", "materials", "toc"]
    with path.open("w", encoding="utf-8") as f:
        f.write("---\n")
        record["toc"] = "false"
        for prop in props:
            value = record.get(prop, "")
            if prop in {"toc", "year"}:
                f.write(f"{prop}: {value}\n")
            else:
                f.write(f"{prop}: \"{value}\"\n")
        f.write("---\n\n## Abstract\n\n")
        f.write(record.get("abstract", ""))


def build_bib_entry(record: dict) -> dict:
    entry_id = Path(record.get("_filename", "")).stem
    return {
        "ENTRYTYPE": "article",
        "ID": entry_id,
        "title": record.get("title", ""),
        "author": record.get("author_bib", record.get("author", "")),
        "year": str(record.get("year", "")),
        "journal": record.get("publication", ""),
        "doi": record.get("doi", ""),
        "abstract": record.get("abstract", ""),
        "orcid_type": record.get("orcid_type", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync publications from ORCID into QMD files.")
    parser.add_argument("--orcid", default=os.getenv("ORCID_ID"), help="ORCID iD (or set ORCID_ID env var)")
    parser.add_argument("--publications-dir", default="publications", help="Directory for publication QMDs")
    parser.add_argument("--bib-file", default="publications/publications.bib", help="BibTeX file to update")
    parser.add_argument("--no-bib", action="store_true", help="Skip writing the BibTeX file")
    parser.add_argument("--no-qmd", action="store_true", help="Skip writing QMD files")
    parser.add_argument("--full", action="store_true", help="Rebuild BibTeX from ORCID (ignore existing DOIs)")
    parser.add_argument("--pdf-dir", default="publications/pdfs", help="Directory containing local PDFs")
    parser.add_argument(
        "--materials-template",
        default=os.getenv("MATERIALS_TEMPLATE"),
        help="Template for external PDF links, e.g. https://server/papers/{slug}.pdf or {doi}.pdf",
    )
    parser.add_argument(
        "--unpaywall-email",
        default=os.getenv("UNPAYWALL_EMAIL"),
        help="Email for Unpaywall API (used to find OA PDFs).",
    )
    parser.add_argument(
        "--download-pdfs",
        action="store_true",
        help="Download OA PDFs found via Unpaywall into --pdf-dir.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be added without writing files")
    args = parser.parse_args()

    if not args.orcid:
        raise SystemExit("Missing ORCID iD. Pass --orcid or set ORCID_ID.")

    if not args.no_bib and bibtexparser is None:
        raise SystemExit("Missing dependency: bibtexparser. Install with 'pip install bibtexparser'.")

    publications_dir = Path(args.publications_dir)
    pdf_dir = Path(args.pdf_dir)
    bib_path = None if args.no_bib else Path(args.bib_file)
    publications_dir.mkdir(parents=True, exist_ok=True)

    existing_dois = set()
    if not args.full:
        existing_dois = load_existing_dois(publications_dir)
        existing_dois |= load_bib_dois(bib_path)
    works = get_orcid_works(args.orcid)
    doi_map = extract_dois(works)

    new_records = []
    for doi, orcid_type in doi_map.items():
        if doi.lower() in existing_dois:
            continue
        try:
            message = fetch_crossref(doi)
        except Exception:
            continue
        record = build_record(message, doi, orcid_type)
        filename = choose_filename(record)
        record["_filename"] = filename

        materials = resolve_materials(record, args.materials_template, args.unpaywall_email)
        record["materials"] = materials

        if args.download_pdfs and args.unpaywall_email:
            try:
                up = fetch_unpaywall(doi, args.unpaywall_email)
                best = up.get("best_oa_location") or {}
                pdf_url = best.get("url_for_pdf") or ""
                if pdf_url:
                    pdf_dir.mkdir(parents=True, exist_ok=True)
                    pdf_path = pdf_dir / Path(filename).with_suffix(".pdf")
                    response = requests.get(pdf_url, timeout=60)
                    response.raise_for_status()
                    pdf_path.write_bytes(response.content)
                    record["materials"] = str(pdf_path.as_posix())
            except Exception:
                pass

        new_records.append(record)

    if args.dry_run:
        for record in new_records:
            print(f"NEW: {record['_filename']} ({record['doi']})")
        print(f"Total new records: {len(new_records)}")
        return

    if not args.no_bib and bib_path is not None:
        bib_path.parent.mkdir(parents=True, exist_ok=True)
        if not args.full and bib_path.exists():
            with bib_path.open("r", encoding="utf-8") as f:
                bib_database = bibtexparser.load(f)
        else:
            bib_database = BibDatabase()
            bib_database.entries = []

        for record in new_records:
            bib_database.entries.append(build_bib_entry(record))

        writer = BibTexWriter()
        writer.order_entries_by = None
        with bib_path.open("w", encoding="utf-8") as f:
            f.write(writer.write(bib_database))

    if not args.no_qmd:
        for record in new_records:
            out_path = publications_dir / record["_filename"]
            write_qmd(out_path, record)

    print(f"Added {len(new_records)} new records.")


if __name__ == "__main__":
    main()
