import csv
import sys
import argparse

def quote(val, is_number=False):
    val = val.strip()
    if val == "":
        return "NULL"
    if is_number:
        return val
    return "'" + val.replace("'", "''") + "'"

def process_tsv(file_path):
    seen_betrnr = {}    # betrnr -> zeilennummer
    seen_company = {}   # company.lower() -> zeilennummer

    print("INSERT INTO vnbd_operators (betrnr, loc, company) VALUES ")

    with open(file_path, encoding='utf-8', newline='') as f:
        reader = list(csv.reader(f, delimiter='\t'))

        for line_num, row in enumerate(reader, start=1):
            if len(row) != 3:
                print(f"⚠️  Zeile {line_num}: erwartet 3 Spalten, gefunden {len(row)} – übersprungen", file=sys.stderr)
                continue

            betrnr, loc, company = row[0].strip(), row[1].strip(), row[2].strip()

            if not betrnr.isdigit():
                print(f"⚠️  Zeile {line_num}: ungültiger betrnr '{betrnr}' – übersprungen", file=sys.stderr)
                continue

            if betrnr in seen_betrnr:
                first_line = seen_betrnr[betrnr]
                print(f"⚠️  Zeile {line_num}: doppelter betrnr '{betrnr}' (bereits in Zeile {first_line}) – übersprungen", file=sys.stderr)
                continue

            company_key = company.lower()
            if company_key in seen_company:
                first_line = seen_company[company_key]
                print(f"⚠️  Zeile {line_num}: doppelte company '{company}' (bereits in Zeile {first_line}) – wird trotzdem übernommen", file=sys.stderr)

            seen_betrnr[betrnr] = line_num
            seen_company[company_key] = line_num

            values = [quote(betrnr, is_number=True), quote(loc), quote(company)]
            print(f"({', '.join(values)}),")

    print("ON CONFLICT (betrnr) DO UPDATE SET")
    print("  loc = EXCLUDED.loc,")
    print("company = EXCLUDED.company")
    print(";")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert TSV to PostgreSQL VALUES list with duplicate checks.")
    parser.add_argument("tsv_file", help="Pfad zur TSV-Datei")
    args = parser.parse_args()

    process_tsv(args.tsv_file)
