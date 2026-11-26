const grid = document.getElementById("anime-grid");
const statusBox = document.getElementById("status");
const title = document.getElementById("results-title");
const loadMore = document.getElementById("load-more");
let currentCollection = "trending", currentGenre = "", currentPage = 1, searchMode = false;

function esc(value="") {
  return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
}
function cardMarkup(anime) {
  const image = anime.image || "https://placehold.co/420x590/171322/a78bfa?text=AnimeX";
  const score = anime.score ? `${(anime.score / 10).toFixed(1)} ★` : "NEW";
  const year = anime.season_year || anime.season || anime.format || "Anime";
  return `<a class="anime-card" href="/anime/${encodeURIComponent(anime.id)}">
    <div class="poster-wrap"><img loading="lazy" src="${esc(image)}" alt="${esc(anime.title)} poster"><span class="score">${esc(score)}</span></div>
    <div class="card-title" title="${esc(anime.title)}">${esc(anime.title)}</div>
    <div class="card-sub">${esc(year)}${anime.episodes ? ` · ${anime.episodes} eps` : ""}</div></a>`;
}
function render(items, append=false) {
  if (!append) grid.innerHTML = "";
  if (!items?.length && !append) { grid.innerHTML = '<div class="empty">No anime found. Try another category.</div>'; return; }
  grid.insertAdjacentHTML("beforeend", items.map(cardMarkup).join(""));
}
async function fetchJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed.");
  return data;
}
async function loadCollection(append=false) {
  if (!append) { currentPage = 1; statusBox.textContent = "Loading your anime universe..."; loadMore.hidden = true; }
  try {
    const url = `/api/anime/${currentCollection}?page=${currentPage}${currentGenre ? `&genre=${encodeURIComponent(currentGenre)}` : ""}`;
    const data = await fetchJson(url);
    render(data.results, append);
    statusBox.textContent = data.results.length ? "" : "No anime found in this collection.";
    loadMore.hidden = data.results.length < 18;
  } catch (error) { statusBox.textContent = `${error.message} Please try again.`; }
}
function setTitle() {
  const names = {"trending":"Trending","popular":"Popular","top-rated":"Top rated","upcoming":"Upcoming"};
  title.innerHTML = `${esc(names[currentCollection])} <span>${currentGenre ? `· ${esc(currentGenre)}` : "now"}</span>`;
}
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
  title.innerHTML = `Search <span>results</span>`; statusBox.textContent = `Searching for "${esc(query)}"...`; grid.innerHTML = ""; loadMore.hidden = true;
  try {
    const data = await fetchJson(`/api/anime/search?q=${encodeURIComponent(query)}&page=1`);
    render(data.results); statusBox.textContent = `${data.results.length} results from ${data.provider}.`;
  } catch (error) { statusBox.textContent = error.message; }
});
loadMore.addEventListener("click", () => { if (searchMode) return; currentPage += 1; loadCollection(true); });
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
