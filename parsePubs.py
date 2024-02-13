from collections import defaultdict
with open("publications/cfranken2024_doi.bib") as f:
    file = f.read()

def parse_entry(entry,write=True):
    # breakdown into lines
    lines = [x.strip(",").strip("}") for x in entry.split("\n")]
    
    # remove empty lines
    lines = [x.replace("\t","") for x in lines if x != ""]
    
    # get file name
    file_name = lines[0].split("{")[1].replace("/", "")
    
    # itialize dictionary
    article_dict = defaultdict(lambda: "", key="some_value")
    
    for x in lines[1:]:
        
        # split into key and value
        y = x.split(" = ")
        if len(y) == 1:
            y = x.split("=")
        article_dict[y[0].strip(" ").lower()] = y[1].strip('"').strip("{").strip("}").replace("{","").replace("}","").replace("\\n","").replace("\\'","").replace("\\`","").replace("\\o","o").replace("\\e","e").replace("\\","").replace("---","-").replace("--","-").replace('"',"")
        # if article_dict['author'].startswith("Butz,"):
        #     print(article_dict['author'])
    article_dict['type'] = 'article'
    article_dict['toc'] = 'false'
    article_dict['publication'] = article_dict['journal']
    article_dict['year'] = article_dict['year']
    
    # write to file
    if write:
        with open(f"publications/{file_name}.qmd", "w") as f:
            f.write("---\n")
            props = ['title', 'author', 'type','year','publication', 'doi', 'materials', 'toc']
            for prop in props:
                if (prop == 'toc') | (prop == 'year'):
                    f.write(f'{prop}: {article_dict[prop]}\n')
                else:
                    f.write(f'{prop}: "{article_dict[prop]}"\n')
            f.write("---\n\n## Abstract\n\n")
            f.write(article_dict["abstract"])
        

for row in file.split("@")[1:]:
    if row != "":
        parse_entry(row)



import bibtexparser
import requests

def find_doi(title, author):
    # Format a query to the CrossRef API
    query = f"{title} {author}"
    url = f"https://api.crossref.org/works?query={query}"

    response = requests.get(url)
    if response.status_code == 200:
        results = response.json()['message']['items']
        if results:
            return results[0].get('DOI', None)
    return None

# Load your BibTeX file
with open('publications/cfranken2024.bib') as bibtex_file:
    bib_database = bibtexparser.load(bibtex_file)

# Iterate over entries
for entry in bib_database.entries:
    if 'doi' not in entry:
        title = entry.get('title', '')
        author = entry.get('author', '').split(' and ')[0]  # First author
        doi = find_doi(title, author)
        if doi:
            entry['doi'] = doi

# Save the updated BibTeX file
with open('publications/cfranken2024_doi.bib', 'w') as bibtex_file:
    bibtexparser.dump(bib_database, bibtex_file)
