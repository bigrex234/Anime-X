const auth = window.AnimeXAuth;
const grid = document.getElementById("library-grid");
const statusBox = document.getElementById("library-status");
const recentGrid = document.getElementById("recent-grid");
const recentStatus = document.getElementById("recent-status");
let allItems = [], filter = "all";
const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function card(item, library=false) {
  const img = item.image || "https://placehold.co/420x590/171322/a78bfa?text=AnimeX";
  const id = item.anime_id || item.id;
  const title = item.title || "Anime";
  return `<article class="anime-card">
    <a href="/anime/${encodeURIComponent(id)}"><div class="poster-wrap"><img loading="lazy" src="${esc(img)}" alt="${esc(title)}"><span class="score">${library ? esc(item.status.replaceAll("_"," ")) : "RECENT"}</span></div><div class="card-title">${esc(title)}</div><div class="card-sub">${library ? `Episode progress: ${item.progress || 0}` : "Recently viewed"}</div></a>
    ${library ? `<button class="remove-library" data-remove="${id}">Remove from library</button>` : ""}
  </article>`;
}
function renderLibrary() {
  const shown = allItems.filter(x => filter === "all" ? true : filter === "favorites" ? x.is_favorite : x.status === filter);
  grid.innerHTML = shown.map(x => card(x, true)).join("");
  if (!shown.length) grid.innerHTML = `<div class="empty">Nothing here yet. Explore anime and add titles to your library.</div>`;
}
async function load() {
  if (!auth?.ready) { statusBox.textContent = "Supabase is not configured. Add the project URL and publishable/anon key."; return; }
  const session = await auth.session();
  if (!session) { window.location.href = "/login"; return; }
  document.getElementById("library-user").textContent = session.user.email || "";
  try {
    const [libraryRes, recentRes] = await Promise.all([
      auth.apiFetch("/api/me/library"), auth.apiFetch("/api/me/recent")
    ]);
    const lib = await libraryRes.json(), rec = await recentRes.json();
    if (!libraryRes.ok) throw new Error(lib.error || "Could not load library.");
    allItems = lib.items || []; renderLibrary(); statusBox.textContent = `${allItems.length} saved titles`;
    recentGrid.innerHTML = (rec.items || []).map(x => card(x)).join("");
    if (!(rec.items || []).length) recentStatus.textContent = "Your recently viewed anime will appear here.";
  } catch (e) { statusBox.textContent = e.message; }
}
document.querySelector(".library-tabs").addEventListener("click", e => {
  const b = e.target.closest("[data-filter]"); if (!b) return;
  filter = b.dataset.filter;
  document.querySelectorAll(".library-tabs .tab").forEach(x => x.classList.toggle("active", x === b));
  renderLibrary();
});
grid.addEventListener("click", async e => {
  const b = e.target.closest("[data-remove]"); if (!b) return;
  const response = await auth.apiFetch(`/api/me/library/${b.dataset.remove}`, { method: "DELETE" });
  if (response.ok) { allItems = allItems.filter(x => String(x.anime_id) !== b.dataset.remove); renderLibrary(); }
});
document.getElementById("signout-button").addEventListener("click", async () => {
  await auth.client.auth.signOut(); window.location.href = "/";
});
load();
