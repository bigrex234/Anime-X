const grid = document.getElementById("anime-grid");
const statusBox = document.getElementById("status");
const title = document.getElementById("results-title");
const loadMore = document.getElementById("load-more");
let currentCollection = "trending", currentGenre = "", currentPage = 1, searchMode = false;
let activeRequest = 0;

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ------------------------------------------------------------------ */
/* Injected animation styles                                           */
/* ------------------------------------------------------------------ */
(() => {
  const css = `
  @keyframes axCardIn {
    0%   { opacity: 0; transform: perspective(900px) translateY(60px) rotateX(-25deg) scale(.85); filter: blur(10px); }
    60%  { opacity: 1; filter: blur(0); }
    100% { opacity: 1; transform: perspective(900px) translateY(0) rotateX(0) scale(1); }
  }
  @keyframes axShimmer { 0% { background-position: -400px 0; } 100% { background-position: 400px 0; } }
  @keyframes axTitleIn { 0% { opacity: 0; transform: translateX(-30px) skewX(-10deg); filter: blur(6px); } 100% { opacity: 1; transform: none; filter: blur(0); } }
  @keyframes axPop { 0% { transform: scale(.4) rotate(-20deg); opacity: 0; } 70% { transform: scale(1.25) rotate(6deg); } 100% { transform: scale(1) rotate(0); opacity: 1; } }
  @keyframes axRipple { to { transform: scale(4); opacity: 0; } }
  @keyframes axFloat { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
  @keyframes axPulse { 0%,100% { box-shadow: 0 0 0 0 rgba(167,139,250,.55); } 50% { box-shadow: 0 0 0 14px rgba(167,139,250,0); } }
  @keyframes axStatus { 0% { opacity: 0; transform: translateY(8px); } 100% { opacity: 1; transform: none; } }

  .ax-pre { opacity: 0; }
  .ax-in  { animation: axCardIn .8s cubic-bezier(.2,.9,.2,1) backwards; animation-delay: calc(var(--i, 0) * 70ms); }

  .anime-card {
    transform-style: preserve-3d;
    transition: transform .25s ease-out, box-shadow .3s ease;
    transform: perspective(900px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg));
    will-change: transform;
  }
  .anime-card:hover { box-shadow: 0 20px 50px -15px rgba(167,139,250,.55); z-index: 2; }
  .anime-card .poster-wrap { position: relative; overflow: hidden; }
  .anime-card .poster-wrap img { transition: transform .6s cubic-bezier(.2,.9,.2,1); }
  .anime-card:hover .poster-wrap img { transform: scale(1.12) rotate(1deg); }
  .anime-card .score { animation: axPop .6s cubic-bezier(.2,.9,.2,1) .4s backwards; }
  .ax-glare {
    position: absolute; inset: 0; pointer-events: none; opacity: 0; transition: opacity .3s;
    background: radial-gradient(circle at var(--mx, 50%) var(--my, 50%), rgba(255,255,255,.35), transparent 55%);
    mix-blend-mode: overlay;
  }
  .anime-card:hover .ax-glare { opacity: 1; }

  .ax-skeleton { border-radius: 14px; aspect-ratio: 420 / 590; background: linear-gradient(90deg, #1b1630 25%, #2a2148 50%, #1b1630 75%); background-size: 800px 100%; animation: axShimmer 1.3s infinite linear; }

  #results-title.ax-title-anim { animation: axTitleIn .6s cubic-bezier(.2,.9,.2,1); }
  #status:not(:empty) { animation: axStatus .4s ease; }
  .empty { animation: axFloat 3s ease-in-out infinite; }

  .tab, .genre-chip, #load-more { position: relative; overflow: hidden; transition: transform .2s ease, box-shadow .3s ease, background .3s ease; }
  .tab:hover, .genre-chip:hover, #load-more:hover { transform: translateY(-3px) scale(1.05); }
  .tab:active, .genre-chip:active, #load-more:active { transform: scale(.94); }
  .tab.active, .genre-chip.selected { animation: axPulse 1.8s ease-out 1; }
  #load-more:not([hidden]) { animation: axFloat 2.4s ease-in-out infinite; }
  .ax-ripple { position: absolute; width: 40px; height: 40px; margin: -20px 0 0 -20px; border-radius: 50%; background: rgba(255,255,255,.45); pointer-events: none; animation: axRipple .6s ease-out forwards; }

  #ax-progress { position: fixed; top: 0; left: 0; height: 3px; width: 100%; transform-origin: 0 50%; transform: scaleX(0); background: linear-gradient(90deg, #a78bfa, #f472b6, #38bdf8); z-index: 9999; pointer-events: none; }
  #ax-glow { position: fixed; top: 0; left: 0; width: 420px; height: 420px; margin: -210px 0 0 -210px; border-radius: 50%; pointer-events: none; z-index: 0; opacity: .5;
    background: radial-gradient(circle, rgba(167,139,250,.22), transparent 65%); transition: opacity .3s; will-change: transform; }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
    .ax-pre { opacity: 1; }
  }`;
  const style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);
})();

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
function esc(value="") {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}

function cardMarkup(anime) {
  const image = anime.image || "https://placehold.co/420x590/171322/a78bfa?text=AnimeX";
  const scoreValue = anime.score ? anime.score / 10 : 0;
  const score = anime.score ? `${scoreValue.toFixed(1)} ★` : "NEW";
  const year = anime.season_year || anime.season || anime.format || "Anime";
  return `<a class="anime-card ax-pre" href="/anime/${encodeURIComponent(anime.id)}">
    <div class="poster-wrap"><img loading="lazy" src="${esc(image)}" alt="${esc(anime.title)} poster"><span class="score" data-score="${scoreValue}">${esc(score)}</span><span class="ax-glare"></span></div>
    <div class="card-title" title="${esc(anime.title)}">${esc(anime.title)}</div>
    <div class="card-sub">${esc(year)}${anime.episodes ? ` · ${anime.episodes} eps` : ""}</div></a>`;
}

/* Scroll-reveal: cards animate in (staggered) when they enter the viewport */
const revealObserver = new IntersectionObserver(entries => {
  let batch = 0;
  entries.forEach(entry => {
    if (!entry.isIntersecting) return;
    const card = entry.target;
    revealObserver.unobserve(card);
    card.style.setProperty("--i", Math.min(batch++, 12));
    card.classList.remove("ax-pre");
    card.classList.add("ax-in");
    countUpScore(card.querySelector(".score"));
    card.addEventListener("animationend", () => card.classList.remove("ax-in"), { once: true });
  });
}, { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });

function countUpScore(el) {
  if (!el || reduceMotion) return;
  const target = parseFloat(el.dataset.score);
  if (!target) return;
  const start = performance.now(), duration = 900;
  const tick = now => {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = `${(target * eased).toFixed(1)} ★`;
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function showSkeletons(count = 12) {
  grid.innerHTML = Array.from({ length: count }, () => '<div class="ax-skeleton"></div>').join("");
}
function clearSkeletons() {
  grid.querySelectorAll(".ax-skeleton").forEach(x => x.remove());
}

function render(items, append=false) {
  clearSkeletons();
  if (!append) grid.innerHTML = "";
  if (!items?.length && !append) { grid.innerHTML = '<div class="empty">No anime found. Try another category.</div>'; return; }
  const before = new Set(grid.children);
  grid.insertAdjacentHTML("beforeend", items.map(cardMarkup).join(""));
  [...grid.children].filter(el => !before.has(el)).forEach(card => revealObserver.observe(card));
}

async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}

function animateTitle() {
  title.classList.remove("ax-title-anim");
  void title.offsetWidth; // restart the animation
  title.classList.add("ax-title-anim");
}

/* ------------------------------------------------------------------ */
/* Data loading                                                        */
/* ------------------------------------------------------------------ */
async function loadCollection(append=false) {
  const requestId = ++activeRequest;
  if (!append) {
    currentPage = 1;
    statusBox.textContent = "Loading your anime universe...";
    loadMore.hidden = true;
    showSkeletons();
  } else {
    grid.insertAdjacentHTML("beforeend", '<div class="ax-skeleton"></div>'.repeat(6));
  }
  try {
    const url = `/api/anime/${currentCollection}?page=${currentPage}${currentGenre ? `&genre=${encodeURIComponent(currentGenre)}` : ""}`;
    const data = await fetchJson(url);
    if (requestId !== activeRequest) return;
    render(data.results, append);
    statusBox.textContent = data.results.length ? "" : "No anime found in this collection.";
    loadMore.hidden = data.results.length < 18;
  } catch (error) {
    if (requestId === activeRequest) {
      clearSkeletons();
      statusBox.textContent = `${error.message} Please try again.`;
    }
  }
}

function setTitle() {
  const names = {"trending":"Trending","popular":"Popular","top-rated":"Top rated","upcoming":"Upcoming"};
  title.innerHTML = `${esc(names[currentCollection])} <span>${currentGenre ? `· ${esc(currentGenre)}` : "now"}</span>`;
  animateTitle();
}

/* ------------------------------------------------------------------ */
/* Events                                                              */
/* ------------------------------------------------------------------ */
document.getElementById("collection-tabs").addEventListener("click", event => {
  const button = event.target.closest("[data-collection]");
  if (!button) return;
  searchMode = false; currentCollection = button.dataset.collection;
  document.querySelectorAll(".tab").forEach(x => x.classList.toggle("active", x === button));
  setTitle(); loadCollection();
});

document.getElementById("genre-list").addEventListener("click", event => {
  const button = event.target.closest("[data-genre]");
  if (!button) return;
  currentGenre = button.dataset.genre; searchMode = false;
  document.querySelectorAll(".genre-chip").forEach(x => x.classList.toggle("selected", x === button));
  setTitle(); loadCollection();
});

document.getElementById("search-form").addEventListener("submit", async event => {
  event.preventDefault();
  const query = document.getElementById("search-input").value.trim();
  if (!query) return;
  searchMode = true; currentPage = 1; currentGenre = "";
  const requestId = ++activeRequest;
  title.innerHTML = `Search <span>results</span>`; animateTitle();
  statusBox.textContent = `Searching for "${query}"...`; // textContent is already safe, no esc() needed
  loadMore.hidden = true;
  showSkeletons();
  try {
    const data = await fetchJson(`/api/anime/search?q=${encodeURIComponent(query)}&page=1`);
    if (requestId !== activeRequest) return;
    render(data.results);
    statusBox.textContent = `${data.results.length} results from ${data.provider}.`;
  } catch (error) {
    if (requestId === activeRequest) { clearSkeletons(); statusBox.textContent = error.message; }
  }
});

loadMore.addEventListener("click", () => { if (searchMode) return; currentPage += 1; loadCollection(true); });

/* ------------------------------------------------------------------ */
/* Extra motion: 3D tilt, ripple, cursor glow, scroll progress         */
/* ------------------------------------------------------------------ */
if (!reduceMotion) {
  // 3D tilt + moving glare on cards (mouse only)
  grid.addEventListener("pointermove", event => {
    if (event.pointerType !== "mouse") return;
    const card = event.target.closest(".anime-card");
    if (!card) return;
    const rect = card.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    card.style.setProperty("--ry", `${(x - 0.5) * 18}deg`);
    card.style.setProperty("--rx", `${(0.5 - y) * 18}deg`);
    card.style.setProperty("--mx", `${x * 100}%`);
    card.style.setProperty("--my", `${y * 100}%`);
  });
  grid.addEventListener("pointerout", event => {
    const card = event.target.closest(".anime-card");
    if (!card || card.contains(event.relatedTarget)) return;
    card.style.setProperty("--rx", "0deg");
    card.style.setProperty("--ry", "0deg");
  });

  // Ripple on tabs, genre chips and the load-more button
  document.addEventListener("click", event => {
    const target = event.target.closest(".tab, .genre-chip, #load-more");
    if (!target) return;
    const rect = target.getBoundingClientRect();
    const ripple = document.createElement("span");
    ripple.className = "ax-ripple";
    ripple.style.left = `${event.clientX - rect.left}px`;
    ripple.style.top = `${event.clientY - rect.top}px`;
    target.appendChild(ripple);
    ripple.addEventListener("animationend", () => ripple.remove());
  });

  // Cursor-following glow (desktop only)
  if (window.matchMedia("(pointer: fine)").matches) {
    const glow = document.createElement("div");
    glow.id = "ax-glow";
    document.body.appendChild(glow);
    let gx = 0, gy = 0, tx = 0, ty = 0;
    window.addEventListener("pointermove", e => { tx = e.clientX; ty = e.clientY; });
    (function follow() {
      gx += (tx - gx) * 0.12; gy += (ty - gy) * 0.12;
      glow.style.transform = `translate(${gx}px, ${gy}px)`;
      requestAnimationFrame(follow);
    })();
  }

  // Scroll progress bar
  const bar = document.createElement("div");
  bar.id = "ax-progress";
  document.body.appendChild(bar);
  const updateProgress = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.transform = `scaleX(${max > 0 ? window.scrollY / max : 0})`;
  };
  window.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();
}

/* ------------------------------------------------------------------ */
/* Init                                                                */
/* ------------------------------------------------------------------ */
loadCollection();

// Auth-aware navigation
(async () => {
  const auth = window.AnimeXAuth;
  const nav = document.getElementById("auth-nav");
  if (auth?.ready && nav) {
    const session = await auth.session();
    if (session) { nav.href = "/library"; nav.textContent = "My library"; }
  }
})();

// Compact mobile navigation with accessible open/close state.
(() => {
  const toggle = document.getElementById("mobile-menu");
  const menu = document.getElementById("mobile-nav");
  if (!toggle || !menu) return;
  const close = () => { menu.hidden = true; toggle.setAttribute("aria-expanded", "false"); toggle.textContent = "☰"; };
  toggle.addEventListener("click", () => {
    const opening = menu.hidden; menu.hidden = !opening;
    toggle.setAttribute("aria-expanded", String(opening)); toggle.textContent = opening ? "×" : "☰";
  });
  menu.addEventListener("click", event => { if (event.target.closest("a")) close(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
})();
