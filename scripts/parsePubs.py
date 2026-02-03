import argparse
import re
from pathlib import Path

import bibtexparser


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def sanitize_id(entry_id: str) -> str:
    return slugify(entry_id) or "publication"


def get_publication(entry: dict) -> str:
    return (
        entry.get("journal")
        or entry.get("journaltitle")
        or entry.get("journal_title")
        or entry.get("journal-title")
        or entry.get("container-title")
        or entry.get("container_title")
        or entry.get("booktitle")
        or entry.get("series")
        or entry.get("organization")
        or entry.get("publisher")
        or ""
    )


def is_conference_abstract(entry: dict) -> bool:
    entry_type = (entry.get("ENTRYTYPE") or "").lower()
    title = (entry.get("title") or "").lower()
    venue = (entry.get("journal") or entry.get("booktitle") or "").lower()

    if entry_type in {"inproceedings", "proceedings", "conference"}:
        return True

    keywords = ["abstract", "conference", "meeting", "symposium", "workshop", "proceedings"]
    if any(keyword in venue for keyword in keywords):
        return True

    if "abstract" in title and any(keyword in title for keyword in ["meeting", "conference", "symposium", "workshop"]):
        return True

    return False


def is_supplement(entry: dict) -> bool:
    title = (entry.get("title") or "").lower()
    doi = (entry.get("doi") or "").lower()
    journal = (entry.get("journal") or "").lower()

    if "supplement" in title:
        return True
    if doi.endswith("-supplement") or doi.endswith("-supplementary"):
        return True
    if "/supplement" in doi or "/supplementary" in doi:
        return True
    if "supplement" in journal:
        return True
    return False


def is_preprint(entry: dict) -> bool:
    orcid_type = (entry.get("orcid_type") or entry.get("orcid-type") or entry.get("orcidtype") or "").lower()
    if orcid_type == "preprint":
        return True

    entry_type = (entry.get("ENTRYTYPE") or "").lower()
    title = (entry.get("title") or "").lower()
    journal = (entry.get("journal") or "").lower()
    publisher = (entry.get("publisher") or "").lower()
    note = (entry.get("note") or "").lower()
    doi = (entry.get("doi") or "").lower()

    if entry_type in {"preprint", "posted-content"}:
        return True

    markers = [
        "preprint",
        "arxiv",
        "biorxiv",
        "medrxiv",
        "eartharxiv",
        "essoar",
        "egusphere",
    ]

    if any(marker in journal for marker in markers):
        return True
    if any(marker in publisher for marker in markers):
        return True
    if any(marker in note for marker in markers):
        return True
    if any(marker in doi for marker in markers):
        return True
    if "preprint" in title:
        return True

    return False


def base_doi_from_supplement(doi: str) -> str:
    base = re.sub(r"(-supplement(ary)?)$", "", doi, flags=re.IGNORECASE)
    base = re.sub(r"(/supplement(ary)?)$", "", base, flags=re.IGNORECASE)
    return base


def normalize_chemistry(text: str) -> str:
    if not text:
        return text

    text = re.sub(
        r"\b([A-Z][a-z]?\d+)\s+\$\{\s*\\mathbf\{([A-Za-z]+)\}\s*\}_\{\s*\\mathbf\{(\d+)\}\s*\}\$([A-Za-z]+)",
        lambda m: f"{m.group(2)}{m.group(3)}{m.group(4)}" if m.group(1).lower() == f"{m.group(2)}{m.group(3)}".lower() else m.group(0),
        text,
    )
    text = re.sub(
        r"\b([A-Z][a-z]?\d+)\s+\$\\mathbf\{([A-Za-z]+)\}_\\mathbf\{(\d+)\}\$([A-Za-z]+)",
        lambda m: f"{m.group(2)}{m.group(3)}{m.group(4)}" if m.group(1).lower() == f"{m.group(2)}{m.group(3)}".lower() else m.group(0),
        text,
    )

    text = re.sub(
        r"\$\{\s*\\mathbf\{([A-Za-z]+)\}\s*\}_\{\s*\\mathbf\{(\d+)\}\s*\}\$",
        r"$\\mathrm{\1_\2}$",
        text,
    )
    text = re.sub(
        r"\$\\mathbf\{([A-Za-z]+)\}_\\mathbf\{(\d+)\}\$",
        r"$\\mathrm{\1_\2}$",
        text,
    )

    parts = re.split(r"(\$[^$]*\$)", text)

    def formula_to_html(formula: str) -> str:
        formula = re.sub(r"_\{?(\d+)\}?", r"\1", formula)
        pieces = re.findall(r"([A-Z][a-z]?)(\d*)", formula)
        if not pieces:
            return formula
        if not any(num for _, num in pieces):
            return formula
        return "".join(f"{el}<sub>{num}</sub>" if num else el for el, num in pieces)

    def convert_formula_token(token: str) -> str:
        return formula_to_html(token)

    for idx, part in enumerate(parts):
        if part.startswith("$") and part.endswith("$"):
            inner = part[1:-1]
            inner = re.sub(r"\\mathbf\{([A-Za-z]+)\}", r"\1", inner)
            inner = re.sub(r"\\mathbf\{(\d+)\}", r"\1", inner)
            inner = re.sub(r"\\mathrm\{([^}]+)\}", r"\1", inner)
            inner = inner.replace(" ", "")
            parts[idx] = formula_to_html(inner)
        else:
            parts[idx] = re.sub(r"\b[A-Z][A-Za-z0-9]*\d+[A-Za-z0-9]*\b", lambda m: convert_formula_token(m.group(0)), part)

    merged = "".join(parts)
    merged = re.sub(
        r"\$\\mathrm\{([^}]+)\}\$",
        lambda m: formula_to_html(m.group(1)),
        merged,
    )
    return merged


def write_qmd(path: Path, entry: dict) -> None:
    props = ["title", "author", "type", "year", "publication", "doi", "materials", "supplement", "orcid_type", "toc"]

    def yaml_quote(value: str) -> str:
        value = value or ""
        return "'" + value.replace("'", "''") + "'"

    with path.open("w", encoding="utf-8") as f:
        f.write("---\n")
        for prop in props:
            value = entry.get(prop, "")
            if prop in {"title", "abstract"}:
                value = normalize_chemistry(str(value))
            if prop in {"toc", "year"}:
                f.write(f"{prop}: {value}\n")
            else:
                f.write(f"{prop}: {yaml_quote(str(value))}\n")
        f.write("---\n\n## Abstract\n\n")
        f.write(entry.get("abstract", ""))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate QMD files from a BibTeX file.")
    parser.add_argument("--bib", default="publications/publications.bib", help="Path to BibTeX file")
    parser.add_argument("--out-dir", default="publications", help="Output directory for QMDs")
    parser.add_argument("--preprints-dir", default="publications/preprints", help="Output directory for preprints")
    parser.add_argument(
        "--include-preprints",
        action="store_true",
        help="Include preprints in the publications list (default is to skip).",
    )
    args = parser.parse_args()

    bib_path = Path(args.bib)
    out_dir = Path(args.out_dir)
    preprints_dir = Path(args.preprints_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.include_preprints:
        preprints_dir.mkdir(parents=True, exist_ok=True)

    with bib_path.open("r", encoding="utf-8") as bibtex_file:
        bib_database = bibtexparser.load(bibtex_file)

    all_ids = []
    generated_ids = []
    generated_preprint_ids = []

    supplements_by_base = {}
    for entry in bib_database.entries:
        doi = (entry.get("doi") or "").lower()
        if is_supplement(entry) and doi:
            base = base_doi_from_supplement(doi)
            supplements_by_base[base] = doi

    def type_rank(entry: dict) -> int:
        orcid_type = (entry.get("orcid_type") or entry.get("orcid-type") or "").lower()
        entry_type = (entry.get("ENTRYTYPE") or "").lower()
        t = orcid_type or entry_type
        order = {
            "journal-article": 1,
            "article": 2,
            "book-chapter": 3,
            "book": 4,
            "report": 5,
            "conference-paper": 6,
            "inproceedings": 6,
            "other": 7,
            "preprint": 10,
            "posted-content": 10,
        }
        return order.get(t, 8)

    best_by_doi = {}
    non_doi_entries = []

    for entry in bib_database.entries:
        doi = (entry.get("doi") or "").lower()
        if doi:
            current = best_by_doi.get(doi)
            if current is None or type_rank(entry) < type_rank(current):
                best_by_doi[doi] = entry
        else:
            non_doi_entries.append(entry)

    selected_entries = list(best_by_doi.values()) + non_doi_entries

    for entry in selected_entries:
        entry_id = sanitize_id(entry.get("ID", ""))
        all_ids.append(entry_id)

        if is_conference_abstract(entry):
            continue

        if is_supplement(entry):
            continue

        if is_preprint(entry):
            if not args.include_preprints:
                continue
            generated_preprint_ids.append(entry_id)
            out_path = preprints_dir / f"{entry_id}.qmd"
        else:
            generated_ids.append(entry_id)
            out_path = out_dir / f"{entry_id}.qmd"

        doi = (entry.get("doi") or "").lower()

        # out_path assigned above based on preprint status

        supplement_link = ""
        if doi:
            supplement_doi = supplements_by_base.get(doi, "")
            if supplement_doi:
                supplement_link = f"https://doi.org/{supplement_doi}"

        orcid_type = entry.get("orcid_type") or entry.get("orcid-type") or ""
        display_type = orcid_type or entry.get("ENTRYTYPE", "article")

        qmd_entry = {
            "title": normalize_chemistry(entry.get("title", "")),
            "author": entry.get("author", ""),
            "type": "preprint" if is_preprint(entry) else display_type,
            "year": entry.get("year", ""),
            "publication": get_publication(entry),
            "doi": entry.get("doi", ""),
            "materials": entry.get("materials", ""),
            "supplement": supplement_link,
            "orcid_type": orcid_type,
            "toc": "false",
            "abstract": normalize_chemistry(entry.get("abstract", "")),
        }

        write_qmd(out_path, qmd_entry)

    for qmd in out_dir.glob("*.qmd"):
        if qmd.stem not in set(generated_ids):
            qmd.unlink()

    if args.include_preprints:
        for qmd in preprints_dir.glob("*.qmd"):
            if qmd.stem not in set(generated_preprint_ids):
                qmd.unlink()
    elif preprints_dir.exists():
        for qmd in preprints_dir.glob("*.qmd"):
            qmd.unlink()

    print(f"Wrote {len(generated_ids)} QMD files to {out_dir}.")
    if args.include_preprints:
        print(f"Wrote {len(generated_preprint_ids)} preprints to {preprints_dir}.")


if __name__ == "__main__":
    main()
