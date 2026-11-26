const auth = window.AnimeXAuth;
const form = document.getElementById("auth-form");
const message = document.getElementById("auth-message");
let mode = "signin";
function showMessage(text, error=false) { message.textContent = text; message.className = `auth-message ${error ? "error" : "success"}`; }
function setMode(next) {
  mode = next;
  document.querySelectorAll(".auth-tab").forEach(b => b.classList.toggle("active", b.dataset.mode === mode));
  document.getElementById("auth-title").textContent = mode === "signup" ? "Join AnimeX." : "Welcome back.";
  document.getElementById("auth-subtitle").textContent = mode === "signup" ? "Create an account to save your anime journey." : "Sign in to continue your anime journey.";
  document.getElementById("auth-submit").innerHTML = mode === "signup" ? "Create account <span>→</span>" : "Sign in <span>→</span>";
  document.getElementById("password").autocomplete = mode === "signup" ? "new-password" : "current-password";
  showMessage("");
}
document.querySelectorAll(".auth-tab").forEach(b => b.addEventListener("click", () => setMode(b.dataset.mode)));
form.addEventListener("submit", async e => {
  e.preventDefault();
  if (!auth?.ready) return showMessage("Supabase is not configured. Add the project URL and publishable/anon key, then restart.", true);
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const button = document.getElementById("auth-submit");
  button.disabled = true; showMessage("Please wait...");
  try {
    const result = mode === "signup"
      ? await auth.client.auth.signUp({ email, password })
      : await auth.client.auth.signInWithPassword({ email, password });
    if (result.error) throw result.error;
    if (mode === "signup" && !result.data.session) {
      showMessage("Account created. Check your email to confirm your address, then sign in.");
    } else {
      window.location.href = "/library";
    }
  } catch (err) { showMessage(err.message || "Authentication failed.", true); }
  finally { button.disabled = false; }
});
if (!auth?.ready) showMessage("Add your Supabase URL and public key to .env to enable registration and login.", true);
else auth.session().then(s => { if (s) window.location.href = "/library"; });
