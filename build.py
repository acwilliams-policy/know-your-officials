"""Gathers current officials from free public data and saves them for the website.

Run it with:  python3 build.py
It writes site/data/officials.json, which the website reads. Run it again
whenever you want fresh data (for example after an election or a resignation).

Sources:
- President, Vice President and Congress: the public-domain
  "congress-legislators" dataset (https://github.com/unitedstates/congress-legislators)
- Governors: Wikidata (https://www.wikidata.org), which is free (CC0) but
  edited by volunteers, so the script reports anything that looks wrong.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
OUTPUT = HERE / "site" / "data" / "officials.json"
USER_AGENT = "KnowYourOfficials/0.1 (free civic education website)"

CONGRESS_URL = "https://unitedstates.github.io/congress-legislators/legislators-current.json"
EXECUTIVE_URL = "https://unitedstates.github.io/congress-legislators/executive.json"
PHOTO_URL = "https://unitedstates.github.io/images/congress/225x275/{bioguide}.jpg"
WIKIDATA_URL = "https://query.wikidata.org/sparql"

# Every place with a member of Congress. The last six send a non-voting
# delegate (Puerto Rico's is called a Resident Commissioner).
PLACES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
    "DC": "Washington, D.C.", "PR": "Puerto Rico", "GU": "Guam",
    "VI": "U.S. Virgin Islands", "AS": "American Samoa", "MP": "Northern Mariana Islands",
}

GOVERNORS_QUERY = """
SELECT ?code ?personLabel ?start ?partyLabel ?article WHERE {
  ?state wdt:P31 wd:Q35657; wdt:P1313 ?position; wdt:P300 ?code.  # P300 = ISO code like "US-AZ"
  ?person p:P39 ?held. ?held ps:P39 ?position; pq:P580 ?start.
  # Still current if there is no end date, or the end date hasn't arrived yet.
  FILTER NOT EXISTS { ?held pq:P582 ?end. FILTER(?end <= NOW()) }
  OPTIONAL {
    ?person p:P102 ?membership. ?membership ps:P102 ?party.
    FILTER NOT EXISTS { ?membership pq:P582 ?left }
  }
  OPTIONAL { ?article schema:about ?person; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""

warnings = []


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def clean_url(url):
    """Fix small typos in source data (like "hhttps://") and drop anything that isn't a web address."""
    if not url:
        return None
    url = re.sub(r"^h+ttp", "http", url.strip())
    if not url.startswith(("http://", "https://")):
        warnings.append(f"Dropped a link that isn't a web address: {url}")
        return None
    return url


def normalize_party(party):
    """Use one spelling per party: Congress data says "Democrat", Wikidata says "Democratic Party"."""
    if not party:
        return None
    party = party.replace(" Party", "")
    return {"Democrat": "Democratic"}.get(party, party)


def full_name(name):
    return name.get("official_full") or " ".join(
        part for part in (name.get("first"), name.get("middle"), name.get("last")) if part
    )


def congress_members():
    """Return {state code: {"senators": [...], "representatives": [...]}}."""
    members = {code: {"senators": [], "representatives": []} for code in PLACES}
    for person in fetch_json(CONGRESS_URL):
        term = person["terms"][-1]
        if term["state"] not in members:
            warnings.append(f"Unknown state code {term['state']} for {full_name(person['name'])}")
            continue
        name = full_name(person["name"])
        slug = re.sub(r"[^a-z]+", "-", name.lower()).strip("-")
        member = {
            "name": name,
            "party": normalize_party(term.get("party")),
            # First time they started this same office (a senator may have served in the House before).
            "since": min(t["start"] for t in person["terms"] if t["type"] == term["type"]),
            "record": f"https://www.congress.gov/member/{slug}/{person['id']['bioguide']}",
            "term_ends": term["end"],
            "website": clean_url(term.get("url")),
            "contact_form": clean_url(term.get("contact_form")),
            "phone": term.get("phone"),
            "office_address": term.get("address"),
            "photo": PHOTO_URL.format(bioguide=person["id"]["bioguide"]),
        }
        if term["type"] == "sen":
            member["office"] = "senator"
            member["rank"] = term.get("state_rank")
            members[term["state"]]["senators"].append(member)
        else:
            member["office"] = "representative" if term["state"] in list(PLACES)[:50] else "delegate"
            member["district"] = term.get("district")  # 0 means the whole state ("at large")
            members[term["state"]]["representatives"].append(member)

    for code, group in members.items():
        group["senators"].sort(key=lambda m: m.get("rank") != "senior")
        group["representatives"].sort(key=lambda m: m.get("district") or 0)
        if code in list(PLACES)[:50] and len(group["senators"]) != 2:
            warnings.append(f"{PLACES[code]} has {len(group['senators'])} senators listed (expected 2; maybe a vacancy).")
    return members


def national_officials():
    today = date.today().isoformat()
    officials = []
    for person in fetch_json(EXECUTIVE_URL):
        term = person["terms"][-1]
        if term["start"] <= today < term["end"]:
            officials.append({
                "name": full_name(person["name"]),
                "office": "president" if term["type"] == "prez" else "vice_president",
                "party": normalize_party(term.get("party")),
                "since": term["start"],
                "term_ends": term["end"],
            })
    officials.sort(key=lambda o: o["office"] != "president")
    if [o["office"] for o in officials] != ["president", "vice_president"]:
        warnings.append(f"Expected one President and one Vice President, found: {officials}")
    return officials


def governors():
    """Return {state code: current governor}.

    Wikidata also lists some governors-elect (with future start dates), but
    not reliably for every state, so they are left out.
    """
    url = WIKIDATA_URL + "?" + urllib.parse.urlencode({"query": GOVERNORS_QUERY, "format": "json"})
    rows = fetch_json(url)["results"]["bindings"]
    today = date.today().isoformat()
    by_state = {}
    for row in rows:
        if row["start"]["value"][:10] > today:
            continue
        name = row["personLabel"]["value"]
        article = row.get("article", {}).get("value")
        if re.fullmatch(r"Q\d+", name) and article:  # no English label: use the Wikipedia title
            name = urllib.parse.unquote(article.rsplit("/", 1)[1]).replace("_", " ")
        person = {
            "name": name,
            "office": "governor",
            "party": normalize_party(row.get("partyLabel", {}).get("value")),
            "since": row["start"]["value"][:10],
            "wikipedia": article,
        }
        # One row per party; keep the first party listed for each person.
        by_state.setdefault(row["code"]["value"].replace("US-", ""), {}).setdefault(name, person)

    result = {}
    for state, people in by_state.items():
        current = sorted(people.values(), key=lambda p: p["since"])
        if len(current) != 1:
            warnings.append(f"Governor of {PLACES.get(state, state)}: Wikidata lists {len(current)} current governors {[p['name'] for p in current]}; using the most recent.")
        result[state] = current[-1]
    missing = [PLACES[code] for code in list(PLACES)[:50] if code not in result]
    if missing:
        warnings.append(f"No governor found on Wikidata for: {', '.join(missing)}")
    return result


def main():
    print("Downloading Congress, President and Vice President…")
    congress = congress_members()
    national = national_officials()
    print("Downloading governors from Wikidata…")
    governor_data = governors()
    # If Wikidata is missing a governor (it is edited by volunteers), keep the
    # one from the last successful update instead of dropping them.
    if OUTPUT.exists():
        previous = json.loads(OUTPUT.read_text())["states"]
        for code, name in list(PLACES.items())[:50]:
            if code not in governor_data and previous.get(code, {}).get("governor"):
                governor_data[code] = previous[code]["governor"]
                warnings.append(f"Kept the previous governor of {name} ({governor_data[code]['name']}); please confirm it is still correct.")

    states = {}
    for code, name in PLACES.items():
        states[code] = {"name": name, "governor": governor_data.get(code), **congress[code]}

    OUTPUT.write_text(json.dumps({
        "generated": date.today().isoformat(),
        "national": national,
        "states": states,
    }, indent=1))

    total = sum(len(s["senators"]) + len(s["representatives"]) for s in states.values())
    governors_found = sum(1 for s in states.values() if s["governor"])
    print(f"Saved {total} members of Congress, {governors_found} governors, and the President and Vice President.")
    if warnings:
        print("\nPlease check these by hand:")
        for warning in warnings:
            print(" -", warning)
    return 0


if __name__ == "__main__":
    sys.exit(main())
