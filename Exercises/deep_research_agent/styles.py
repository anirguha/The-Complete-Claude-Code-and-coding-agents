EXAMPLES = [
    "Most popular AI Agent frameworks in 2026",
    "Most commercially successful Agentic AI implementations in 2026",
    "Celebrities who don't like cheese",
]

HEADER_HTML = """
<div class="dr-brand">
    <div class="dr-mark" aria-hidden="true">
        <span class="dr-bar dr-bar-1"></span>
        <span class="dr-bar dr-bar-2"></span>
        <span class="dr-bar dr-bar-3"></span>
    </div>
    <div class="dr-titles">
        <h1>Deep<span class="dr-sep">/</span>Research</h1>
        <p>Explore a question. Connect the evidence. Get a clearer picture.</p>
    </div>
</div>
"""

CSS = """
/* ==========================================================================
   Deep/Research — Gradio theme (v2, editorial)
   --------------------------------------------------------------------------
   Direction
     A research tool should feel like a well-set document, not a dashboard.
     UI chrome is quiet and sans-serif; the report — the actual product — is
     set in a serif with a measured line length and generous leading.
     One accent colour, used for actions and links only. No decorative
     shadows, gradients, or hover lifts.

   Sections
     1. Design tokens (light + dark)
     2. Page shell
     3. Header
     4. Query row
     5. Examples
     6. Report
     7. Accessibility & responsive
   ========================================================================== */


/* --------------------------------------------------------------------------
   1. Design tokens
   -------------------------------------------------------------------------- */

.gradio-container {
    /* Surfaces */
    --dr-bg:       #fafbfb;
    --dr-surface:  #ffffff;
    --dr-tint:     #f1f4f6;

    /* Lines */
    --dr-line:        #d9dfe5;
    --dr-line-strong: #b9c3cc;

    /* Text */
    --dr-text:   #1b2530;
    --dr-muted:  #5c6873;

    /* Accent — a single deep blue, reserved for actions and links */
    --dr-accent:        #24577a;
    --dr-accent-strong: #193f59;
    --dr-accent-fg:     #ffffff;
    --dr-accent-ring:   color-mix(in srgb, var(--dr-accent) 22%, transparent);

    /* Shape */
    --dr-radius-sm: 4px;
    --dr-radius-md: 6px;
    --dr-ease:      0.12s ease;

    /* Type */
    --dr-font-ui:    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    --dr-font-serif: "Charter", "Iowan Old Style", "Source Serif Pro", "Georgia", "Times New Roman", serif;
    --dr-font-mono:  ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;

    /* Report measure (characters per line) */
    --dr-measure: 70ch;
}

.gradio-container.dark,
.dark .gradio-container,
body.dark .gradio-container,
html.dark .gradio-container {
    --dr-bg:       #121a21;
    --dr-surface:  #18222b;
    --dr-tint:     #1f2b35;

    --dr-line:        #2d3a46;
    --dr-line-strong: #45545f;

    --dr-text:   #e4e9ee;
    --dr-muted:  #9aa7b3;

    --dr-accent:        #7fb3d9;
    --dr-accent-strong: #a9cde8;
    --dr-accent-fg:     #0e1a24;
}


/* --------------------------------------------------------------------------
   2. Page shell
   -------------------------------------------------------------------------- */

body { background: #fafbfb; }

body.dark,
html.dark body,
body:has(.gradio-container.dark),
body:has(.dark .gradio-container) {
    background: #121a21;
}

.gradio-container {
    max-width: 960px !important;
    margin: 0 auto !important;
    padding: 4rem 2.5rem 6rem !important;
    background: var(--dr-bg) !important;
    color: var(--dr-text) !important;
    font-family: var(--dr-font-ui) !important;
    -webkit-font-smoothing: antialiased;
}

.gradio-container footer { display: none !important; }


/* --------------------------------------------------------------------------
   3. Header
   -------------------------------------------------------------------------- */

.dr-brand {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: start;
    gap: 1.25rem;
    margin-bottom: 2.75rem;
    padding-bottom: 1.75rem;
    border-bottom: 1px solid var(--dr-line);
}

/* Mark: three ink rules, reads as a document — no tint box, no accent */
.dr-mark {
    display: flex;
    flex-direction: column;
    justify-content: center;
    gap: 5px;
    box-sizing: border-box;
    width: 40px;
    height: 40px;
    margin-top: 0.35rem;
    padding: 8px 6px;
    border: 1px solid var(--dr-line-strong);
    border-radius: var(--dr-radius-sm);
}

.dr-bar {
    display: block;
    height: 3px;
    background: var(--dr-text);
}

.dr-bar-1 { width: 100%; }
.dr-bar-2 { width: 80%; }
.dr-bar-3 { width: 55%; }

/* Eyebrow removed from the hierarchy: the title and subtitle carry it */
.dr-eyebrow { display: none; }

.dr-titles h1 {
    margin: 0;
    color: var(--dr-text);
    font-family: var(--dr-font-serif);
    font-size: clamp(1.9rem, 3.6vw, 2.5rem);
    font-weight: 500;
    line-height: 1.15;
    letter-spacing: -0.01em;
}

.dr-sep {
    margin: 0 0.06em;
    color: var(--dr-muted);
    font-weight: 300;
}

.dr-titles p {
    max-width: 48ch;
    margin: 0.5rem 0 0;
    color: var(--dr-muted);
    font-size: 1rem;
    line-height: 1.55;
}


/* --------------------------------------------------------------------------
   4. Query row
   -------------------------------------------------------------------------- */

.dr-query-row {
    gap: 0.5rem !important;
    align-items: stretch !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Strip Gradio's wrapper chrome */
#dr-query,
#dr-query > div,
#dr-query .wrap,
#dr-query .form,
#dr-query .block {
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

#dr-query textarea,
#dr-query input {
    min-height: 52px !important;
    padding: 0.85rem 1rem !important;
    background: var(--dr-surface) !important;
    color: var(--dr-text) !important;
    border: 1px solid var(--dr-line-strong) !important;
    border-radius: var(--dr-radius-md) !important;
    box-shadow: none !important;
    font-family: inherit !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
    resize: none !important;
    transition: border-color var(--dr-ease), box-shadow var(--dr-ease) !important;
}

#dr-query textarea:hover,
#dr-query input:hover {
    border-color: var(--dr-muted) !important;
}

#dr-query textarea:focus,
#dr-query input:focus {
    outline: none !important;
    border-color: var(--dr-accent) !important;
    box-shadow: 0 0 0 3px var(--dr-accent-ring) !important;
}

#dr-query textarea::placeholder,
#dr-query input::placeholder {
    color: var(--dr-muted) !important;
    opacity: 1 !important;
}

/* Primary action */
#dr-run {
    min-width: 132px !important;
    min-height: 52px !important;
    padding: 0 1.25rem !important;
    background: var(--dr-accent) !important;
    color: var(--dr-accent-fg) !important;
    border: 1px solid var(--dr-accent) !important;
    border-radius: var(--dr-radius-md) !important;
    box-shadow: none !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    letter-spacing: 0 !important;
    transition: background var(--dr-ease), border-color var(--dr-ease) !important;
}

#dr-run:hover:not(:disabled) {
    background: var(--dr-accent-strong) !important;
    border-color: var(--dr-accent-strong) !important;
}

#dr-run:disabled {
    opacity: 0.55;
    cursor: not-allowed;
}


/* --------------------------------------------------------------------------
   5. Examples
   -------------------------------------------------------------------------- */

.dr-examples-label {
    margin: 1.5rem 0 0.6rem;
    color: var(--dr-muted);
    font-size: 0.875rem;
    font-weight: 500;
    letter-spacing: 0;
    text-transform: none;
}

.dr-examples-label::after { content: none; }

/* Strip Gradio's wrapper chrome */
#dr-examples,
#dr-examples > div,
#dr-examples .wrap,
#dr-examples .block {
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

#dr-examples label,
#dr-examples .label-wrap,
#dr-examples thead {
    display: none !important;
}

#dr-examples table {
    width: auto !important;
    background: transparent !important;
    border: none !important;
    border-collapse: separate !important;
    border-spacing: 0 !important;
}

/* Rows/cells become a wrapping list of quiet, text-first suggestions */
#dr-examples tbody,
#dr-examples tr {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 0.4rem 0.5rem !important;
    background: transparent !important;
    border: none !important;
}

#dr-examples td,
#dr-examples button {
    margin: 0 !important;
    padding: 0.45rem 0.8rem !important;
    background: transparent !important;
    color: var(--dr-text) !important;
    border: 1px solid var(--dr-line) !important;
    border-radius: var(--dr-radius-md) !important;
    box-shadow: none !important;
    font-size: 0.875rem !important;
    line-height: 1.45 !important;
    text-align: left !important;
    white-space: normal !important;
    cursor: pointer !important;
    transition: background var(--dr-ease), border-color var(--dr-ease) !important;
}

#dr-examples td:hover,
#dr-examples button:hover {
    background: var(--dr-tint) !important;
    border-color: var(--dr-line-strong) !important;
}


/* --------------------------------------------------------------------------
   6. Report — the product; set as a document
   -------------------------------------------------------------------------- */

#dr-report {
    min-height: 40px;
    margin-top: 3rem !important;
    padding: 0 !important;
    background: transparent !important;
    color: var(--dr-text) !important;
    border: none !important;
    box-shadow: none !important;
    overflow-wrap: anywhere;
}

#dr-report > div,
#dr-report .prose {
    background: transparent !important;
    color: var(--dr-text) !important;
}

/* Draw the page only once the Markdown wrapper has content */
#dr-report:has(.prose > :not(:empty)) {
    padding: 2.5rem 3rem 3rem !important;
    background: var(--dr-surface) !important;
    border: 1px solid var(--dr-line) !important;
    border-top: 3px solid var(--dr-text) !important;
    border-radius: var(--dr-radius-sm) !important;
    box-shadow: none !important;
}

#dr-report .prose {
    max-width: var(--dr-measure);
    font-family: var(--dr-font-serif);
    font-size: 1.0625rem;
    line-height: 1.7;
}

#dr-report .prose > :first-child { margin-top: 0; }
#dr-report .prose > :last-child  { margin-bottom: 0; }

/* Headings: same serif, differentiated by size and space, not colour */
#dr-report h1,
#dr-report h2,
#dr-report h3 {
    color: var(--dr-text);
    font-family: var(--dr-font-serif);
    font-weight: 600;
    line-height: 1.25;
}

#dr-report h1 {
    margin: 0 0 1.25rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--dr-line);
    font-size: 1.9rem;
    letter-spacing: -0.01em;
}

#dr-report h2 {
    margin: 2.25rem 0 0.75rem;
    font-size: 1.4rem;
}

#dr-report h3 {
    margin: 1.75rem 0 0.5rem;
    font-size: 1.125rem;
}

/* Body text */
#dr-report p { margin: 0 0 1rem; }

#dr-report ul,
#dr-report ol {
    margin: 0 0 1rem;
    padding-left: 1.4rem;
}

#dr-report li { margin: 0.35rem 0; }

#dr-report a {
    color: var(--dr-accent);
    text-decoration: underline;
    text-decoration-color: color-mix(in srgb, var(--dr-accent) 45%, transparent);
    text-decoration-thickness: 1px;
    text-underline-offset: 0.2em;
}

#dr-report a:hover {
    color: var(--dr-accent-strong);
    text-decoration-color: currentColor;
}

#dr-report hr {
    height: 1px;
    margin: 2rem 0;
    background: var(--dr-line);
    border: none;
}

/* Code: sans-serif UI chrome inside the serif document */
#dr-report code {
    padding: 0.1em 0.35em;
    background: var(--dr-tint);
    border-radius: var(--dr-radius-sm);
    font-family: var(--dr-font-mono);
    font-size: 0.86em;
}

#dr-report pre {
    margin: 1.25rem 0;
    padding: 1rem 1.25rem;
    background: var(--dr-tint);
    border: 1px solid var(--dr-line);
    border-radius: var(--dr-radius-sm);
    font-size: 0.875rem;
    line-height: 1.55;
    overflow-x: auto;
}

#dr-report pre code {
    padding: 0;
    background: transparent;
    font-size: inherit;
}

/* Quotes: a single rule, no fill */
#dr-report blockquote {
    margin: 1.25rem 0;
    padding: 0.25rem 0 0.25rem 1.25rem;
    color: var(--dr-muted);
    border-left: 2px solid var(--dr-line-strong);
    font-style: italic;
}

/* Tables: horizontal rules only */
#dr-report table {
    display: block;
    max-width: 100%;
    margin: 1.25rem 0;
    border-collapse: collapse;
    font-family: var(--dr-font-ui);
    font-size: 0.9rem;
    line-height: 1.45;
    overflow-x: auto;
}

#dr-report th,
#dr-report td {
    padding: 0.6rem 0.85rem;
    border: none;
    border-bottom: 1px solid var(--dr-line);
    text-align: left;
    vertical-align: top;
}

#dr-report th {
    color: var(--dr-text);
    border-bottom: 2px solid var(--dr-text);
    font-weight: 600;
}

#dr-report td:first-child,
#dr-report th:first-child { padding-left: 0; }

#dr-report td:last-child,
#dr-report th:last-child { padding-right: 0; }


/* --------------------------------------------------------------------------
   7. Accessibility & responsive
   -------------------------------------------------------------------------- */

#dr-run:focus-visible,
#dr-examples button:focus-visible,
#dr-examples td:focus-visible,
#dr-report a:focus-visible {
    outline: 2px solid var(--dr-accent) !important;
    outline-offset: 2px !important;
}

@media (prefers-reduced-motion: reduce) {
    .gradio-container *,
    .gradio-container *::before,
    .gradio-container *::after {
        transition: none !important;
    }
}

@media (max-width: 700px) {
    .gradio-container { padding: 2rem 1.25rem 4rem !important; }

    .dr-brand {
        gap: 0.9rem;
        margin-bottom: 2rem;
    }

    .dr-query-row { flex-direction: column !important; }

    #dr-query,
    #dr-run {
        flex-basis: auto !important;
        min-width: 0 !important;
    }

    #dr-run { width: 100% !important; }

    #dr-report:has(.prose > :not(:empty)) { padding: 1.5rem 1.25rem 2rem !important; }

    #dr-report .prose { font-size: 1rem; }
}
"""

JS = """
() => {
    const focus = () => {
        const el = document.querySelector("#dr-query textarea, #dr-query input");
        if (el) { el.focus(); return true; }
        return false;
    };
    if (!focus()) {
        let tries = 0;
        const i = setInterval(() => {
            if (focus() || ++tries > 20) clearInterval(i);
        }, 100);
    }
}
"""
