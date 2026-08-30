"""Custom look for the digital-twin chat UI.

Gradio's ``css=`` argument accepts a raw CSS string, so ``CUSTOM_CSS`` is
imported and passed straight into ``gr.ChatInterface(..., css=CUSTOM_CSS)``.

Selectors below target Gradio 6.x's actual rendered DOM for
``ChatInterface`` (verified against a live instance), not a hypothetical
custom layout — e.g. ``.message-row.user-row`` / ``.bot-row`` for the two
message sides, ``.submit-button`` for the send button. The theme is set
mostly through Gradio's own CSS custom properties on ``.gradio-container``
so it stays consistent with parts of the UI (focus rings, disabled states,
etc.) that this stylesheet doesn't touch directly.
"""

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ---------- Theme tokens (Gradio's own CSS variables) ---------- */

.gradio-container {
  --body-background-fill: #fafbfa;
  --background-fill-primary: #fafbfa;
  --background-fill-secondary: #ffffff;
  --block-background-fill: #ffffff;
  --block-border-color: #e2e4e4;
  --border-color-primary: #e2e4e4;
  --border-color-accent: #2f3ee0;
  --body-text-color: #14161a;
  --body-text-color-subdued: #5b6069;
  --color-accent: #2f3ee0;
  --color-accent-soft: #edeffc;
  --link-text-color: #2f3ee0;
  --button-primary-background-fill: #14161a;
  --button-primary-background-fill-hover: #2f3ee0;
  --button-primary-text-color: #fafbfa;
  --button-primary-border-color: #14161a;
  --input-background-fill: #fafbfa;
  --input-border-color: #e2e4e4;
  --input-border-color-focus: #2f3ee0;
  --radius-lg: 14px;
  --radius-md: 10px;
  --radius-sm: 6px;
  --font: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', ui-monospace, SFMono-Regular, monospace;

  max-width: 760px !important;
  margin: 0 auto !important;
}

/* ---------- Title ---------- */

.gradio-container .prose:not(.chatbot) h1 {
  font-family: 'Space Grotesk', 'Inter', system-ui, sans-serif;
  font-weight: 600;
  letter-spacing: 0.01em;
  font-size: 1.25rem;
}

/* ---------- Message list ---------- */

.bubble-wrap {
  background: var(--body-background-fill);
  padding: 24px 16px !important;
}

.message-row {
  animation: twin-rise 0.2s ease-out both;
}

/* User bubble: solid, right-aligned.
   NOTE: the visible bubble chrome (border/background/shadow) lives on the
   outer `.message.user` / `.message.bot` wrapper, not on the `.panel-full-width`
   div nested inside it - confirmed against Gradio 6.26's rendered DOM. */
.message-row.user-row .message.user {
  background: var(--body-text-color) !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 10px 10px 2px 10px !important;
}

.message-row.user-row .prose.chatbot,
.message-row.user-row .prose.chatbot p {
  color: var(--body-background-fill) !important;
}

/* Assistant: no bubble, thin left rule instead */
.message-row.bot-row .message.bot {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  border-radius: 0 !important;
  border-left: 2px solid var(--color-accent-soft) !important;
  padding-left: 12px !important;
}

.message-row.bot-row .prose.chatbot,
.message-row.bot-row .prose.chatbot p {
  color: var(--body-text-color);
}

.prose.chatbot,
.prose.chatbot p {
  font-family: var(--font);
  font-size: 0.9375rem;
  line-height: 1.55;
}

/* Copy / retry icons: understated until hovered */
.message-buttons-left,
.message-buttons-right {
  opacity: 0.45;
  transition: opacity 0.15s ease;
}

.message-row:hover .message-buttons-left,
.message-row:hover .message-buttons-right {
  opacity: 1;
}

/* ---------- Input bar ---------- */

.input-container textarea {
  font-family: var(--font);
  font-size: 0.9375rem;
  border-radius: var(--radius-md) !important;
}

.submit-button {
  border-radius: var(--radius-md) !important;
}

/* ---------- Accessibility ---------- */

@media (prefers-reduced-motion: reduce) {
  .message-row {
    animation: none !important;
  }
}

/* ---------- Keyframes ---------- */

@keyframes twin-rise {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
"""
