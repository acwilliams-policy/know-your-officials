# Know Your Officials

A free, nonpartisan website that shows who represents you, what each office
does, and how to reach your officials. It's a static site (plain HTML, CSS and
JavaScript), so it can be hosted for free on GitHub Pages or Cloudflare Pages.

## What's covered so far

- President and Vice President
- All 100 U.S. senators and every member of the House, including the six
  non-voting delegates
- All 50 governors
- Plain-language guides to each of those offices

Planned next: campaign promises and follow-through (with a source for every
claim), then mayors and other state and local officials.

## Updating the officials data

```
python3 build.py
```

This downloads the latest data and saves it to `site/data/officials.json`.
It lists anything that looks wrong for you to check by hand. Run it after
elections (officials elected in November take office in January) and
whenever an official resigns or is replaced.

## Previewing the site on your computer

```
cd site
python3 -m http.server 8642
```

Then open http://127.0.0.1:8642 in your browser.

## Files

- `build.py` gathers the officials data from free public sources.
- `site/index.html` is the page itself.
- `site/app.js` decides what each page shows.
- `site/style.css` is how it looks.
- `site/data/offices.json` holds the plain-language explanations of each office.
  Edit this file to change or add explanations.
- `site/data/officials.json` is created by `build.py`. Don't edit it by hand.

## Sources

- President, Vice President and Congress: the public-domain
  [congress-legislators](https://github.com/unitedstates/congress-legislators) project.
- Photos: the public-domain [unitedstates/images](https://github.com/unitedstates/images) project.
- Governors: [Wikidata](https://www.wikidata.org) (CC0), which is edited by volunteers.
