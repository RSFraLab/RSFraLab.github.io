import argparse
from pathlib import Path

import bibtexparser
from bibtexparser.bibdatabase import BibDatabase
from bibtexparser.bwriter import BibTexWriter


def entry_key(entry: dict) -> str:
    doi = (entry.get("doi") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    title = (entry.get("title") or "").strip().lower()
    year = (entry.get("year") or "").strip()
    return f"title:{title}|year:{year}"


def load_bib(path: Path) -> list:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return bibtexparser.load(f).entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge BibTeX files into a single output.")
    parser.add_argument("--out", default="publications/publications.bib", help="Output BibTeX file")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input BibTeX files")
    args = parser.parse_args()

    merged = {}
    for bib_path in args.inputs:
        for entry in load_bib(Path(bib_path)):
            key = entry_key(entry)
            if key not in merged:
                merged[key] = entry

    db = BibDatabase()
    db.entries = list(merged.values())

    writer = BibTexWriter()
    writer.order_entries_by = None
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        f.write(writer.write(db))

    print(f"Wrote {len(db.entries)} entries to {out_path}.")


if __name__ == "__main__":
    main()
