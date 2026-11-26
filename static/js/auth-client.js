(() => {
  const config = window.ANIMEX_CONFIG || {};
  const ready = Boolean(config.supabaseUrl && config.supabaseAnonKey && window.supabase);
  const client = ready ? window.supabase.createClient(config.supabaseUrl, config.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
  }) : null;
  async function session() {
    if (!client) return null;
    const { data } = await client.auth.getSession();
    return data.session || null;
  }
  async function apiFetch(url, options = {}) {
    const current = await session();
    const headers = new Headers(options.headers || {});
    if (current?.access_token) headers.set("Authorization", `Bearer ${current.access_token}`);
    if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    return fetch(url, { ...options, headers });
  }
  window.AnimeXAuth = { client, ready, session, apiFetch };
})();
