// Know Your Officials: shows who represents each state and what each office does.
// Pages are chosen by the part of the address after "#":
//   #              home page
//   #state/NY      officials for one state
//   #office/senator  what an office does

let officials = null;
let offices = null;
const app = document.getElementById("app");

// Turn text into safe HTML, so names and data can never break the page.
function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

function formatDate(iso) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });
}

function year(iso) {
  return iso.slice(0, 4);
}

function link(url, label) {
  return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label)}</a>` : "";
}

function roleLabel(person, stateName) {
  const title = offices[person.office].title;
  if (person.office === "senator" && person.rank) {
    return `${title} · ${person.rank === "senior" ? "Senior" : "Junior"} senator`;
  }
  if (person.office === "representative") {
    return person.district ? `${title} · District ${person.district}` : `${title} · Whole state (at large)`;
  }
  if (person.office === "governor") return `Governor of ${stateName}`;
  return title;
}

function card(person, stateName) {
  const facts = [];
  if (person.party) facts.push(`Party: ${person.party}`);
  if (person.office === "president" || person.office === "vice_president") {
    facts.push(`Current term began ${formatDate(person.since)}`);
  } else if (person.office === "governor") {
    facts.push(`In office since ${year(person.since)}`);
  } else {
    // Some members left Congress and came back, so "first" is the accurate word.
    facts.push(`First took this office in ${year(person.since)}`);
  }
  if (person.term_ends) {
    facts.push(`Current term ends ${formatDate(person.term_ends)}`);
  }
  const links = [
    link(person.website, "Official website"),
    link(person.contact_form, "Contact form"),
    person.phone ? `<a href="tel:${esc(person.phone.replace(/[^0-9+]/g, ""))}">${esc(person.phone)}</a>` : "",
    link(person.record, "Bills and votes"),
    link(person.wikipedia, "Wikipedia"),
    `<a href="#office/${esc(person.office)}">What does this office do?</a>`,
  ].filter(Boolean);
  const photo = person.photo
    ? `<img src="${esc(person.photo)}" alt="" loading="lazy" onerror="this.remove()">`
    : "";
  return `
    <article class="card">
      ${photo}
      <div>
        <h3>${esc(person.name)}</h3>
        <div class="role">${esc(roleLabel(person, stateName))}</div>
        <ul class="facts">${facts.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
        <div class="links">${links.join("")}</div>
      </div>
    </article>`;
}

function statePicker(selected) {
  const options = Object.entries(officials.states)
    .map(([code, s]) => `<option value="${code}" ${code === selected ? "selected" : ""}>${esc(s.name)}</option>`)
    .join("");
  return `
    <div class="picker">
      <label for="state">Choose your state</label>
      <select id="state" onchange="if (this.value) location.hash = 'state/' + this.value">
        <option value="">Select a state or territory…</option>
        ${options}
      </select>
    </div>`;
}

function officeLinks() {
  return `<div class="offices">${Object.entries(offices)
    .map(([id, o]) => `
      <a class="office-link" href="#office/${id}">
        <strong>${esc(o.title)}</strong>
        <span>${esc(o.summary)}</span>
      </a>`)
    .join("")}</div>`;
}

function promisesNote() {
  return `
    <div class="callout">
      <p><strong>Coming soon: campaign promises.</strong> We plan to track what officials promised
      and whether they followed through, with a source for every claim. We'll start with a small
      number of officials so we can get it right.</p>
    </div>`;
}

function homePage() {
  return `
    <h1>Who represents you?</h1>
    <p class="lead">See your governor and members of Congress, learn what each office does, and find out how to reach them.</p>
    ${statePicker()}
    <h2>Leading the whole country</h2>
    <div class="cards">${officials.national.map((p) => card(p)).join("")}</div>
    <h2>What does each office do?</h2>
    <p class="section-note">Plain-language guides to each office's job, powers and limits.</p>
    ${officeLinks()}
    ${promisesNote()}`;
}

function statePage(code) {
  const state = officials.states[code];
  if (!state) return notFound();
  const isState = Object.keys(officials.states).indexOf(code) < 50;

  let governor;
  if (state.governor) {
    governor = `<div class="cards">${card(state.governor, state.name)}</div>`;
  } else if (code === "DC") {
    governor = `<p class="empty">Washington, D.C., has a mayor instead of a governor. Mayors aren't covered yet.</p>`;
  } else if (!isState) {
    governor = `<p class="empty">Territorial governors aren't covered yet.</p>`;
  } else {
    governor = `<p class="empty">We couldn't find this state's governor in our data source. We're working on it.</p>`;
  }

  const senators = isState
    ? `<div class="cards">${state.senators.map((p) => card(p, state.name)).join("") || '<p class="empty">No senators listed.</p>'}</div>`
    : `<p class="empty">${esc(state.name)} has no U.S. senators.</p>`;

  const houseCount = state.representatives.length;
  const houseIntro = !isState
    ? `${esc(state.name)} sends one delegate to the House, who can't vote on final passage of laws.`
    : houseCount === 1
      ? `${esc(state.name)} has one representative, elected by the whole state.`
      : `${esc(state.name)} has ${houseCount} representatives, one for each congressional district. Yours depends on where you live:
         <a href="https://www.house.gov/representatives/find-your-representative" target="_blank" rel="noopener">find your district on House.gov</a>.`;
  const houseSearch = houseCount > 4
    ? `<p><label for="house-search" class="visually-hidden">Search representatives</label>
       <input type="search" id="house-search" placeholder="Search by name or district number" oninput="filterHouse(this.value)"></p>`
    : "";

  return `
    <a class="back" href="#">← All states</a>
    <h1>${esc(state.name)}</h1>
    <p class="lead">${isState ? "Your governor and members of Congress." : "Your member of Congress."}</p>
    ${statePicker(code)}
    <h2>${isState ? "Governor" : "Local leader"}</h2>
    ${governor}
    <h2>U.S. Senators</h2>
    ${senators}
    <h2>${isState ? "U.S. Representatives" : "Delegate to the U.S. House"}</h2>
    <p class="section-note">${houseIntro}</p>
    ${houseSearch}
    <div class="cards" id="house">${state.representatives.map((p) => card(p, state.name)).join("")}</div>
    ${promisesNote()}`;
}

function filterHouse(query) {
  const q = query.trim().toLowerCase();
  for (const el of document.querySelectorAll("#house .card")) {
    const text = el.textContent.toLowerCase();
    const district = el.querySelector(".role").textContent.match(/District (\d+)/);
    const match = !q || text.includes(q) || (district && district[1] === q);
    el.style.display = match ? "" : "none";
  }
}

function officePage(id) {
  const o = offices[id];
  if (!o) return notFound();
  return `
    <a class="back" href="#">← Home</a>
    <article class="explainer">
      <h1>What does a ${esc(o.title)} do?</h1>
      <p class="lead">${esc(o.summary)}</p>
      <dl class="quick-facts">
        <dt>Level</dt><dd>${esc(o.level)} government</dd>
        <dt>How many</dt><dd>${esc(o.how_many)}</dd>
        <dt>Term</dt><dd>${esc(o.term)}</dd>
        <dt>How chosen</dt><dd>${esc(o.how_chosen)}</dd>
      </dl>
      <h2>Main responsibilities</h2>
      <ul>${o.what_they_do.map((item) => `<li>${esc(item)}</li>`).join("")}</ul>
      <h2>Limits on their power</h2>
      <p>${esc(o.limits)}</p>
      <h2>Why it matters to you</h2>
      <p>${esc(o.why_it_matters)}</p>
      <h2>Learn more</h2>
      <ul>${o.learn_more.map((l) => `<li>${link(l.url, l.label)}</li>`).join("")}</ul>
    </article>`;
}

function notFound() {
  return `<h1>Page not found</h1><p><a href="#">Go to the home page</a></p>`;
}

function render() {
  const [page, id] = location.hash.replace(/^#/, "").split("/");
  if (page === "state") app.innerHTML = statePage(id);
  else if (page === "office") app.innerHTML = officePage(id);
  else app.innerHTML = homePage();
  window.scrollTo(0, 0);
}

async function start() {
  try {
    [officials, offices] = await Promise.all([
      fetch("data/officials.json").then((r) => r.json()),
      fetch("data/offices.json").then((r) => r.json()),
    ]);
  } catch (error) {
    app.innerHTML = "<p>Sorry, the officials data couldn't be loaded. Please try again later.</p>";
    return;
  }
  document.getElementById("updated").textContent = formatDate(officials.generated);
  window.addEventListener("hashchange", render);
  render();
}

start();
