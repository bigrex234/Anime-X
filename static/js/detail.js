const root = document.getElementById("detail-root");
const id = Number(root.dataset.animeId);
const auth = window.AnimeXAuth;
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const trailerUrl = t => t?.id && t.site === "youtube" ? `https://www.youtube.com/watch?v=${encodeURIComponent(t.id)}` : "";
function recCard(a) {
  return `<a class="anime-card" href="/anime/${encodeURIComponent(a.id)}"><div class="poster-wrap"><img loading="lazy" src="${esc(a.image || "")}" alt="${esc(a.title)}"><span class="score">${a.score ? `${(a.score/10).toFixed(1)} ★` : "ANIME"}</span></div><div class="card-title">${esc(a.title)}</div><div class="card-sub">${esc(a.season_year || a.format || "Anime")}</div></a>`;
}
async function load() {
  try {
    const response = await fetch(`/api/anime/details/${id}`);
    const anime = await response.json();
    if (!response.ok) throw new Error(anime.error || "Could not load anime.");
    const [airingResponse, downloadResponse] = await Promise.all([
      fetch(`/api/anime/${id}/airing`), fetch(`/api/anime/${id}/downloads`)
    ]);
    const airing = airingResponse.ok ? await airingResponse.json() : {episodes:[]};
    const downloads = downloadResponse.ok ? await downloadResponse.json() : {downloads:[]};
    const session = auth?.ready ? await auth.session() : null;
    if (session) auth.apiFetch("/api/me/recent", {method:"POST", body:JSON.stringify({anime_id:id,title:anime.title,image:anime.image})}).catch(()=>{});
    const banner = anime.banner || anime.image || "";
    const trailer = trailerUrl(anime.trailer);
    const genres = (anime.genres || []).map(g => `<span class="detail-chip">${esc(g)}</span>`).join("");
    const links = (downloads.downloads || []).map(d => `<a class="download-item" href="${esc(d.source_url)}" target="_blank" rel="noopener"><strong>${esc(d.title)}</strong><small>${esc(d.rights_note)}</small><span>Download ↗</span></a>`).join("");
    root.innerHTML = `
      <section class="detail-hero" style="--detail-bg:url('${esc(banner)}')"><div class="detail-overlay"></div><div class="detail-content">
        <img class="detail-poster" src="${esc(anime.image || "")}" alt="${esc(anime.title)} poster">
        <div class="detail-copy"><div class="eyebrow">ANIMEX / ANIME PROFILE</div><h1>${esc(anime.title)}</h1>
          ${anime.title_romaji && anime.title_romaji !== anime.title ? `<p class="native-title">${esc(anime.title_romaji)}</p>` : ""}
          <div class="detail-facts"><span>★ ${anime.score ? `${(anime.score/10).toFixed(1)} / 10` : "Not rated"}</span><span>${esc(anime.format || "Anime")}</span><span>${esc(anime.episodes ?? "?")} episodes</span><span>${esc(anime.season_year || anime.status || "")}</span></div>
          <div class="detail-genres">${genres}</div><p class="detail-synopsis">${esc(anime.synopsis || "No synopsis is available yet.")}</p>
          <div class="hero-actions">${trailer ? `<a class="primary-btn" href="${trailer}" target="_blank" rel="noopener">Watch trailer ↗</a>` : ""}<a class="text-btn" href="${esc(anime.source_url || "https://anilist.co")}" target="_blank" rel="noopener">View on AniList ↗</a></div>
        </div></div></section>
      <section class="section detail-actions-section"><div class="section-heading"><div><div class="eyebrow">KEEP YOUR PROGRESS</div><h2>Your <span>anime library</span></h2></div></div>
        ${session ? `<form id="library-form" class="library-form">
          <label>Status<select id="watch-status"><option value="plan_to_watch">Plan to watch</option><option value="watching">Watching</option><option value="completed">Completed</option><option value="on_hold">On hold</option><option value="dropped">Dropped</option></select></label>
          <label>Episode progress<input id="episode-progress" type="number" min="0" max="10000" value="0"></label>
          <label class="favorite-label"><input id="is-favorite" type="checkbox"> Favourite</label>
          <button class="primary-btn" type="submit">Save to my library →</button>
        </form>` : `<p class="library-prompt"><a href="/login">Sign in</a> to save this anime, track episode progress and build your watchlist.</p>`}
        <p id="library-message" class="auth-message"></p>
      </section>
      <section class="section detail-info"><div class="section-heading"><div><div class="eyebrow">MORE INFORMATION</div><h2>Anime <span>overview</span></h2></div></div>
        <div class="info-grid"><div><small>STATUS</small><strong>${esc(anime.status || "Unknown")}</strong></div><div><small>STUDIO</small><strong>${esc((anime.studios || []).join(", ") || "Not listed")}</strong></div><div><small>EPISODE LENGTH</small><strong>${anime.duration ? `${esc(anime.duration)} min` : "Not listed"}</strong></div><div><small>RELEASE YEAR</small><strong>${esc(anime.season_year || "Not listed")}</strong></div></div>
      </section>
      <section class="section"><div class="section-heading"><div><div class="eyebrow">AIRING INFORMATION</div><h2>Episode <span>schedule</span></h2></div></div>
        <div class="schedule-list">${(airing.episodes || []).length ? airing.episodes.map(ep => `<div class="schedule-item"><strong>Episode ${ep.episode}</strong><span>${new Date(ep.airingAt*1000).toLocaleString()}</span></div>`).join("") : '<p class="status">No airing schedule is currently available. Past episode catalogue data is not supplied by AniList.</p>'}</div>
      </section>
      <section class="section"><div class="section-heading"><div><div class="eyebrow">WATCH LEGALLY</div><h2>Official <span>streaming platforms</span></h2></div></div>
        <p class="status">Browse these licensed services and check whether this title is available in your region. Availability varies by country and subscription.</p>
        <div class="provider-links">
          <a href="https://www.crunchyroll.com/" target="_blank" rel="noopener">Crunchyroll ↗</a>
          <a href="https://www.netflix.com/" target="_blank" rel="noopener">Netflix ↗</a>
          <a href="https://www.hidive.com/" target="_blank" rel="noopener">HIDIVE ↗</a>
          <a href="https://www.primevideo.com/" target="_blank" rel="noopener">Prime Video ↗</a>
        </div>
      </section>
      <section class="section"><div class="section-heading"><div><div class="eyebrow">PERMITTED OFFLINE CONTENT</div><h2>Legal <span>downloads</span></h2></div></div>
        <div class="download-list">${links || '<p class="status">No rights-cleared downloadable files have been added for this title yet.</p>'}</div>
      </section>
      ${(anime.recommendations || []).length ? `<section class="section"><div class="section-heading"><div><div class="eyebrow">KEEP EXPLORING</div><h2>You may also <span>like</span></h2></div></div><div class="anime-grid">${anime.recommendations.map(recCard).join("")}</div></section>` : ""}
    `;
    const form = document.getElementById("library-form");
    if (form) form.addEventListener("submit", async e => {
      e.preventDefault();
      const msg = document.getElementById("library-message"); msg.textContent = "Saving...";
      try {
        const r = await auth.apiFetch("/api/me/library", {method:"POST", body:JSON.stringify({
          anime_id:id, title:anime.title, image:anime.image,
          status:document.getElementById("watch-status").value,
          progress:Number(document.getElementById("episode-progress").value || 0),
          is_favorite:document.getElementById("is-favorite").checked
        })});
        const d = await r.json(); if (!r.ok) throw new Error(d.error || "Could not save.");
        msg.textContent = "Saved to your AnimeX library."; msg.className = "auth-message success";
      } catch(err) { msg.textContent = err.message; msg.className = "auth-message error"; }
    });
  } catch (error) {
    root.innerHTML = `<div class="status detail-error">${esc(error.message)}<p><a class="primary-btn" href="/">Return home</a></p></div>`;
  }
}
load();
