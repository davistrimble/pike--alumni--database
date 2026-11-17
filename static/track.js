// Counts clicks and copies of alumni emails / LinkedIns for the admin page.
// Only (alum id, email|linkedin, click|copy) is sent; nothing about the search.
(function () {
  const csrf = document.querySelector('meta[name="csrf-token"]').content;

  function track(el, action) {
    const row = el.closest("tr[data-alumni-id]");
    fetch("/track", {
      method: "POST",
      keepalive: true, // still sends if the click navigates away
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
      body: JSON.stringify({
        alumni_id: row ? Number(row.dataset.alumniId) : null,
        channel: el.dataset.track,
        action: action,
      }),
    }).catch(() => {});
  }

  async function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      try {
        return await navigator.clipboard.writeText(text);
      } catch {
        // Permission denied or unfocused page: fall through to the old way.
      }
    }
    // Fallback for plain-http hosts or browsers that block the Clipboard API.
    const box = document.createElement("textarea");
    box.value = text;
    box.setAttribute("readonly", "");
    box.style.position = "fixed";
    box.style.opacity = "0";
    document.body.appendChild(box);
    box.select();
    const ok = document.execCommand("copy");
    box.remove();
    if (!ok) throw new Error("copy failed");
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("button.copy");
    if (button) {
      try {
        await copyText(button.dataset.copy);
        button.textContent = "Copied!";
        button.classList.add("copied");
        track(button, "copy");
      } catch {
        button.textContent = "Failed";
      }
      setTimeout(() => {
        button.textContent = "Copy";
        button.classList.remove("copied");
      }, 1500);
      return;
    }
    const link = event.target.closest("a[data-track]");
    if (link) track(link, "click");
  });
})();
