// Show / hide toggle for every password box that has a .show-password button.
document.querySelectorAll(".password-field").forEach((field) => {
  const input = field.querySelector("input[data-password]");
  const button = field.querySelector(".show-password");
  button.addEventListener("click", () => {
    const showing = input.type === "text";
    input.type = showing ? "password" : "text";
    button.textContent = showing ? "Show" : "Hide";
    button.setAttribute("aria-pressed", String(!showing));
    button.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    input.focus();
  });
});
