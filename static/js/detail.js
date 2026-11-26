const root = document.getElementById("detail-root");
const id = Number(root.dataset.animeId);
const auth = window.AnimeXAuth;
const baseTitle = document.title;
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ------------------------------------------------------------------ */
/* Injected styles (skeleton, reveal, small extras)                    */
/* ------------------------------------------------------------------ */
(() => {
  const style = document.createElement("style");
  style.textContent = `
  @keyframes dxShimmer { 0% { background-position: -600px 0; } 100% { background-position: 600px 0; } }
  @keyframes dxRise { from { opacity: 0; transform: translateY(24px) scale(.96); } to { opacity: 1; transform: none; } }
  @keyframes dxPop { 0% { transform: scale(.6); opacity: 0; } 70% { transform: scale(1.12); } 100% { transform: scale(1); opacity: 1; } }

  .dx-skel { background: linear-gradient(90deg, #1b1630 25%, #2a2148 50%, #1b1630 75%); background-size: 1200px 100%; animation: dxShimmer 1.4s linear infinite; border-radius: 12px; }
  .dx-skel-hero { min-height: 520px; display: grid; grid-template-columns: 230px 1fr; gap: 42px; align-items: center; max-width: 1180px; margin: auto; padding: 115px 30px 65px; }
  .dx-skel-poster { aspect-ratio: 3 / 4.2; }
  .dx-skel-lines { display: grid; gap: 16px; }
  .dx-skel-lines .dx-skel { height: 18px; }
  .dx-skel-lines .dx-skel:nth-child(1) { width: 30%; height: 12px; }
  .dx-skel-lines .dx-skel:nth-child(2) { width: 70%; height: 44px; }
  .dx-skel-lines .dx-skel:nth-child(3) { width: 45%; }
  .dx-skel-lines .dx-skel:nth-child(4) { width: 90%; }
  .dx-skel-lines .dx-skel:nth-child(5) { width: 80%; }
  @media (max-width: 700px) { .dx-skel-hero { grid-template-columns: 112px 1fr; padding: 65px 20px 40px; gap: 18px; } }

  .dx-hide { opacity: 0; transform: translateY(28px); }
  .dx-show { opacity: 1; transform: none; transition: opacity .7s cubic-bezier(.2,.9,.2,1), transform .7s cubic-bezier(.2,.9,.2,1); }

  .dx-card { animation: dxRise .6s cubic-bezier(.2,.9,.2,1) backwards; animation-delay: calc(var(--i, 0) * 60ms); }

  .detail-synopsis { white-space: pre-line; }
  .detail-synopsis.dx-clamp { display: -webkit-box; -webkit-line-clamp: 5; -webkit-box-orient: vertical; overflow: hidden; }
  .dx-more { background: none; border: 0; color: #c9b4ff; font: 600 11px "DM Sans", sans-serif; cursor: pointer; padding: 0; margin: -8px 0 18px; }
  .dx-more:hover { color: #fff; }

  .schedule-item.dx-next { border-color: #b69aff88; background: linear-gradient(110deg, #231a38, #14101e); }
  .dx-badge { display: inline-block; margin-left: 10px; padding: 3px 8px; border-radius: 999px; background: linear-gradient(105deg, #b69aff, #ee8bdd); color: #100b1b; font-size: 8px; font-weight: 700; letter-spacing: 1.2px; animation: dxPop .5s ease backwards .3s; }
  .dx-when { text-align: right; display: grid; gap: 3px; }
  .dx-when em { font-style: normal; color: #d8caff; font-weight: 600; }
  @media (max-width: 650px) { .dx-when { text-align: left; } }

  .dx-actions-row { display: flex; flex-wrap: wrap; gap: 12px; align-items: center; }
  .library-form .outline-btn[hidden] { display: none; }
  .dx-retry { margin-top: 25px; }

  @media (prefers-reduced-motion: reduce) {
    .dx-hide { opacity: 1; transform: none; }
    .dx-skel, .dx-card, .dx-badge { animation: none !important; }
  }`;
  document.head.appendChild(style);
})();

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

// Only allow http(s) links so a bad value can never become a javascript: URL.
function safeUrl(url, fallback = "") {
  try {
    const parsed = new URL(url, location.origin);
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : fallback;
  } catch { return fallback; }
}

const trailerUrl = t => t?.id && t.site === "youtube" ? `https://www.youtube.com/watch?v=${encodeURIComponent(t.id)}` : "";

// AniList synopses contain HTML (<br>, <i>...). Turn them into clean plain text.
function cleanText(html) {
  const doc = new DOMParser().parseFromString(String(html || "").replace(/<br\s*\/?>/gi, "\n"), "text/html");
  return (doc.body.textContent || "").trim();
}

const scoreText = s => s ? `${(s / 10).toFixed(1)} ★` : "";

function whenText(unixSeconds) {
  const ms = unixSeconds * 1000 - Date.now();
  const abs = Math.abs(ms);
  const d = Math.floor(abs / 86400000);
  const h = Math.floor((abs % 86400000) / 3600000);
  const m = Math.floor((abs % 3600000) / 60000);
  const span = d ? `${d}d ${h}h` : h ? `${h}h ${m}m` : `${Math.max(m, 1)}m`;
  return ms > 0 ? `in ${span}` : `${span} ago`;
}

async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function recCard(a, i) {
  const image = safeUrl(a.image, "https://placehold.co/420x590/171322/a78bfa?text=AnimeX");
  return `<a class="anime-card dx-card" style="--i:${Math.min(i, 12)}" href="/anime/${encodeURIComponent(a.id)}"><div class="poster-wrap"><img loading="lazy" src="${esc(image)}" alt="${esc(a.title)}"><span class="score">${esc(scoreText(a.score) || "ANIME")}</span></div><div class="card-title" title="${esc(a.title)}">${esc(a.title)}</div><div class="card-sub">${esc(a.season_year || a.format || "Anime")}</div></a>`;
}

function showSkeleton() {
  root.innerHTML = `
    <section class="detail-hero"><div class="dx-skel-hero">
      <div class="dx-skel dx-skel-poster"></div>
      <div class="dx-skel-lines"><div class="dx-skel"></div><div class="dx-skel"></div><div class="dx-skel"></div><div class="dx-skel"></div><div class="dx-skel"></div></div>
    </div></section>`;
}

// Sections fade up as they scroll into view.
function revealSections() {
  const sections = root.querySelectorAll(".section");
  if (reduceMotion || !("IntersectionObserver" in window)) return;
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.remove("dx-hide");
      entry.target.classList.add("dx-show");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.08 });
  sections.forEach(section => { section.classList.add("dx-hide"); observer.observe(section); });
}

/* ------------------------------------------------------------------ */
/* Main                                                                */
/* ------------------------------------------------------------------ */
async function load() {
  showSkeleton();
  try {
    // Start everything at once; only the main details are required.
    const detailsPromise = fetchJson(`/api/anime/details/${id}`);
    const airingPromise = fetchJson(`/api/anime/${id}/airing`).catch(() => ({ episodes: [] }));
    const downloadsPromise = fetchJson(`/api/anime/${id}/downloads`).catch(() => ({ downloads: [] }));
    const sessionPromise = auth?.ready ? auth.session().catch(() => null) : Promise.resolve(null);

    const anime = await detailsPromise;
    const [airing, downloads, session] = await Promise.all([airingPromise, downloadsPromise, sessionPromise]);

    document.title = `${anime.title} | ${baseTitle}`;
    if (session) auth.apiFetch("/api/me/recent", { method: "POST", body: JSON.stringify({ anime_id: id, title: anime.title, image: anime.image }) }).catch(() => {});

    const banner = safeUrl(anime.banner || anime.image || "");
    const trailer = trailerUrl(anime.trailer);
    const synopsis = cleanText(anime.synopsis) || "No synopsis is available yet.";
    const longSynopsis = synopsis.length > 420;
    const genres = (anime.genres || []).map(g => `<span class="detail-chip">${esc(g)}</span>`).join("");

    const links = (downloads.downloads || []).map(d => {
      const href = safeUrl(d.source_url);
      return href ? `<a class="download-item" href="${esc(href)}" target="_blank" rel="noopener noreferrer"><strong>${esc(d.title)}</strong><small>${esc(d.rights_note)}</small><span>Download ↗</span></a>` : "";
    }).join("");

    const nowSec = Date.now() / 1000;
    const episodes = airing.episodes || [];
    const nextIndex = episodes.findIndex(ep => ep.airingAt > nowSec);
    const scheduleHtml = episodes.length
      ? episodes.map((ep, i) => `<div class="schedule-item${i === nextIndex ? " dx-next" : ""}"><strong>Episode ${esc(ep.episode)}${i === nextIndex ? '<span class="dx-badge">NEXT</span>' : ""}</strong><span class="dx-when"><em>${esc(whenText(ep.airingAt))}</em><span>${esc(new Date(ep.airingAt * 1000).toLocaleString())}</span></span></div>`).join("")
      : '<p class="status">No airing schedule is currently available. Past episode catalogue data is not supplied by AniList.</p>';

    const sourceUrl = safeUrl(anime.source_url, "https://anilist.co");
    const recs = anime.recommendations || [];

    root.innerHTML = `
      <section class="detail-hero"><div class="detail-overlay"></div><div class="detail-content">
        <img class="detail-poster" src="${esc(safeUrl(anime.image))}" alt="${esc(anime.title)} poster">
        <div class="detail-copy"><div class="eyebrow">ANIMEX / ANIME PROFILE</div><h1>${esc(anime.title)}</h1>
          ${anime.title_romaji && anime.title_romaji !== anime.title ? `<p class="native-title">${esc(anime.title_romaji)}</p>` : ""}
          <div class="detail-facts"><span>★ ${anime.score ? `${(anime.score / 10).toFixed(1)} / 10` : "Not rated"}</span><span>${esc(anime.format || "Anime")}</span><span>${esc(anime.episodes ?? "?")} episodes</span><span>${esc(anime.season_year || anime.status || "")}</span></div>
          <div class="detail-genres">${genres}</div>
          <p id="synopsis" class="detail-synopsis${longSynopsis ? " dx-clamp" : ""}">${esc(synopsis)}</p>
          ${longSynopsis ? '<button id="synopsis-toggle" class="dx-more" type="button">Read more ↓</button>' : ""}
          <div class="hero-actions dx-actions-row">
            ${trailer ? `<a class="primary-btn" href="${trailer}" target="_blank" rel="noopener noreferrer">Watch trailer ↗</a>` : ""}
            <a class="text-btn" href="${esc(sourceUrl)}" target="_blank" rel="noopener noreferrer">View on AniList ↗</a>
            <button id="share-btn" class="outline-btn" type="button">Share ↗</button>
          </div>
        </div></div></section>

      <section class="section detail-actions-section"><div class="section-heading"><div><div class="eyebrow">KEEP YOUR PROGRESS</div><h2>Your <span>anime library</span></h2></div></div>
        ${session ? `<form id="library-form" class="library-form">
          <label>Status<select id="watch-status"><option value="plan_to_watch">Plan to watch</option><option value="watching">Watching</option><option value="completed">Completed</option><option value="on_hold">On hold</option><option value="dropped">Dropped</option></select></label>
          <label>Episode progress<input id="episode-progress" type="number" min="0" max="${esc(anime.episodes || 10000)}" value="0"></label>
          <label class="favorite-label"><input id="is-favorite" type="checkbox"> Favourite</label>
          <button id="save-btn" class="primary-btn" type="submit">Save to my library →</button>
          <button id="remove-btn" class="outline-btn" type="button" hidden>Remove</button>
        </form>` : `<p class="library-prompt"><a href="/login">Sign in</a> to save this anime, track episode progress and build your watchlist.</p>`}
        <p id="library-message" class="auth-message" role="status" aria-live="polite"></p>
      </section>

      <section class="section detail-info"><div class="section-heading"><div><div class="eyebrow">MORE INFORMATION</div><h2>Anime <span>overview</span></h2></div></div>
        <div class="info-grid"><div><small>STATUS</small><strong>${esc(anime.status || "Unknown")}</strong></div><div><small>STUDIO</small><strong>${esc((anime.studios || []).join(", ") || "Not listed")}</strong></div><div><small>EPISODE LENGTH</small><strong>${anime.duration ? `${esc(anime.duration)} min` : "Not listed"}</strong></div><div><small>RELEASE YEAR</small><strong>${esc(anime.season_year || "Not listed")}</strong></div></div>
      </section>

      <section class="section"><div class="section-heading"><div><div class="eyebrow">AIRING INFORMATION</div><h2>Episode <span>schedule</span></h2></div></div>
        <div class="schedule-list">${scheduleHtml}</div>
      </section>

      <section class="section"><div class="section-heading"><div><div class="eyebrow">WATCH LEGALLY</div><h2>Official <span>streaming platforms</span></h2></div></div>
        <p class="status">Browse these licensed services and check whether this title is available in your region. Availability varies by country and subscription.</p>
        <div class="provider-links">
          <a href="https://www.crunchyroll.com/" target="_blank" rel="noopener noreferrer">Crunchyroll ↗</a>
          <a href="https://www.netflix.com/" target="_blank" rel="noopener noreferrer">Netflix ↗</a>
          <a href="https://www.hidive.com/" target="_blank" rel="noopener noreferrer">HIDIVE ↗</a>
          <a href="https://www.primevideo.com/" target="_blank" rel="noopener noreferrer">Prime Video ↗</a>
        </div>
      </section>

      <section class="section"><div class="section-heading"><div><div class="eyebrow">PERMITTED OFFLINE CONTENT</div><h2>Legal <span>downloads</span></h2></div></div>
        <div class="download-list">${links || '<p class="status">No rights-cleared downloadable files have been added for this title yet.</p>'}</div>
      </section>

      ${recs.length ? `<section class="section"><div class="section-heading"><div><div class="eyebrow">KEEP EXPLORING</div><h2>You may also <span>like</span></h2></div></div><div class="anime-grid">${recs.map(recCard).join("")}</div></section>` : ""}
    `;

    // Set the banner through the DOM (safer than putting a URL inside a style attribute).
    if (banner) root.querySelector(".detail-hero").style.setProperty("--detail-bg", `url("${banner.replace(/["\\\n]/g, encodeURIComponent)}")`);

    setupSynopsis();
    setupShare(anime);
    setupLibrary(anime, session);
    revealSections();
  } catch (error) {
    root.innerHTML = `<div class="status detail-error">${esc(error.message)}<p class="dx-retry"><button id="retry-btn" class="primary-btn" type="button">Try again</button> <a class="text-btn" href="/">Return home</a></p></div>`;
    document.getElementById("retry-btn")?.addEventListener("click", load);
  }
}

/* ------------------------------------------------------------------ */
/* Interactions                                                        */
/* ------------------------------------------------------------------ */
function setupSynopsis() {
  const toggle = document.getElementById("synopsis-toggle");
  const text = document.getElementById("synopsis");
  if (!toggle || !text) return;
  toggle.addEventListener("click", () => {
    const collapsed = text.classList.toggle("dx-clamp");
    toggle.textContent = collapsed ? "Read more ↓" : "Show less ↑";
  });
}

function setupShare(anime) {
  const button = document.getElementById("share-btn");
  if (!button) return;
  button.addEventListener("click", async () => {
    const data = { title: anime.title, text: `Check out ${anime.title} on AnimeX`, url: location.href };
    try {
      if (navigator.share) { await navigator.share(data); return; }
      await navigator.clipboard.writeText(location.href);
      button.textContent = "Link copied ✓";
      setTimeout(() => { button.textContent = "Share ↗"; }, 2000);
    } catch { /* user cancelled sharing */ }
  });
}

function setupLibrary(anime, session) {
  const form = document.getElementById("library-form");
  if (!form || !session) return;

  const statusEl = document.getElementById("watch-status");
  const progressEl = document.getElementById("episode-progress");
  const favoriteEl = document.getElementById("is-favorite");
  const saveBtn = document.getElementById("save-btn");
  const removeBtn = document.getElementById("remove-btn");
  const msg = document.getElementById("library-message");

  const setMessage = (text, type = "") => { msg.textContent = text; msg.className = `auth-message ${type}`.trim(); };

  // If this anime is already saved, pre-fill the form with the saved values.
  auth.apiFetch("/api/me/library")
    .then(r => r.ok ? r.json() : null)
    .then(data => {
      const saved = (data?.items || []).find(item => Number(item.anime_id) === id);
      if (!saved) return;
      statusEl.value = saved.status || "plan_to_watch";
      progressEl.value = saved.progress ?? 0;
      favoriteEl.checked = Boolean(saved.is_favorite);
      saveBtn.textContent = "Update my library →";
      removeBtn.hidden = false;
    })
    .catch(() => {});

  form.addEventListener("submit", async event => {
    event.preventDefault();
    let progress = Math.max(0, Math.floor(Number(progressEl.value || 0)));
    if (anime.episodes) progress = Math.min(progress, anime.episodes);
    progressEl.value = progress;

    saveBtn.disabled = true;
    setMessage("Saving...");
    try {
      const response = await auth.apiFetch("/api/me/library", {
        method: "POST",
        body: JSON.stringify({
          anime_id: id, title: anime.title, image: anime.image,
          status: statusEl.value, progress, is_favorite: favoriteEl.checked,
        }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Could not save.");
      setMessage("Saved to your AnimeX library.", "success");
      saveBtn.textContent = "Update my library →";
      removeBtn.hidden = false;
    } catch (err) {
      setMessage(err.message, "error");
    } finally {
      saveBtn.disabled = false;
    }
  });

  removeBtn.addEventListener("click", async () => {
    removeBtn.disabled = true;
    setMessage("Removing...");
    try {
      const response = await auth.apiFetch(`/api/me/library/${id}`, { method: "DELETE" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || "Could not remove.");
      setMessage("Removed from your library.", "success");
      statusEl.value = "plan_to_watch"; progressEl.value = 0; favoriteEl.checked = false;
      saveBtn.textContent = "Save to my library →";
      removeBtn.hidden = true;
    } catch (err) {
      setMessage(err.message, "error");
    } finally {
      removeBtn.disabled = false;
    }
  });
}

load();
