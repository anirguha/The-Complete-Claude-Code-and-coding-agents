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
        <p>Multi-search web investigation</p>
    </div>
</div>
"""

CSS = """
.gradio-container {
    --dr-bg: #f8fafc;
    --dr-surface: #ffffff;
    --dr-line: #172033;
    --dr-line-soft: #dce3ed;
    --dr-text: #172033;
    --dr-muted: #64748b;
    --dr-amber: #2563eb;
    --dr-blue: #2563eb;
    --dr-purple: #1d4ed8;

    max-width: 1080px !important;
    margin: 0 auto !important;
    padding: 3.5rem 2rem 4rem !important;
    background: var(--dr-bg) !important;
    color: var(--dr-text) !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif !important;
}

.gradio-container.dark,
.dark .gradio-container,
body.dark .gradio-container,
html.dark .gradio-container {
    --dr-bg: #0f172a;
    --dr-surface: #182338;
    --dr-line: #94a3b8;
    --dr-line-soft: #334155;
    --dr-text: #e2e8f0;
    --dr-muted: #a5b4c8;
    --dr-blue: #93c5fd;
    --dr-purple: #bfdbfe;
}

body { background: #f8fafc; }
body:has(.gradio-container.dark), body:has(.dark .gradio-container),
body.dark, html.dark body { background: #0f172a; }

/* === HEADER === */
.dr-brand {
    display: grid;
    grid-template-columns: auto 1fr;
    align-items: center;
    gap: 1rem;
    padding-bottom: 1.75rem;
    border-bottom: 1px solid var(--dr-line-soft);
    margin-bottom: 2.5rem;
}

.dr-mark {
    display: flex;
    flex-direction: column;
    gap: 5px;
    width: 38px;
}

.dr-bar { height: 6px; display: block; border-radius: 4px; }
.dr-bar-1 { background: var(--dr-amber);  width: 100%; }
.dr-bar-2 { background: var(--dr-blue);   width: 70%;  }
.dr-bar-3 { background: var(--dr-purple); width: 45%;  }

.dr-titles h1 {
    font-size: clamp(1.8rem, 4vw, 2.6rem);
    font-weight: 700;
    letter-spacing: -0.045em;
    margin: 0;
    line-height: 1.15;
    color: var(--dr-text);
}

.dr-sep {
    color: var(--dr-amber);
    font-weight: 300;
    margin: 0 0.04em;
}

.dr-titles p {
    font-family: inherit;
    font-size: 0.95rem;
    letter-spacing: 0.01em;
    margin: 0.55rem 0 0;
    color: var(--dr-muted);
}

/* === QUERY ROW === */
.dr-query-row {
    gap: 0.75rem !important;
    align-items: stretch !important;
}

#dr-query, #dr-query > div, #dr-query .wrap, #dr-query .form, #dr-query .block {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    border-radius: 10px !important;
}

#dr-query textarea, #dr-query input {
    background: var(--dr-surface) !important;
    color: var(--dr-text) !important;
    border: 1px solid var(--dr-line-soft) !important;
    border-radius: 10px !important;
    padding: 1.05rem 1.2rem !important;
    font-size: 1.05rem !important;
    font-family: inherit !important;
    box-shadow: none !important;
    line-height: 1.45 !important;
    resize: none !important;
    min-height: 56px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}

#dr-query textarea:focus, #dr-query input:focus {
    outline: none !important;
    border-color: var(--dr-blue) !important;
    box-shadow: 0 0 0 3px color-mix(in srgb, var(--dr-blue) 20%, transparent) !important;
}

#dr-query textarea::placeholder, #dr-query input::placeholder {
    color: var(--dr-muted) !important;
    opacity: 1 !important;
}

#dr-run {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid var(--dr-line-soft) !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.01em !important;
    font-size: 0.95rem !important;
    box-shadow: none !important;
    transition: background 0.15s, color 0.15s, transform 0.08s !important;
    min-width: 150px !important;
    padding: 1rem 1.5rem !important;
}

#dr-run:hover:not(:disabled) {
    background: #1d4ed8 !important;
    color: #ffffff !important;
}

#dr-run:focus-visible, #dr-examples button:focus-visible,
#dr-examples td:focus-visible, #dr-report a:focus-visible {
    outline: 3px solid var(--dr-blue) !important;
    outline-offset: 3px !important;
}

#dr-run:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

#dr-run:active { transform: translateY(1px) !important; }

/* === EXAMPLES === */
.dr-examples-label {
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: var(--dr-muted);
    margin: 2rem 0 0.85rem 0;
    display: flex;
    align-items: center;
    gap: 0.85rem;
}

.dr-examples-label::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--dr-line-soft);
}

#dr-examples, #dr-examples > div, #dr-examples .wrap, #dr-examples .block {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

#dr-examples label, #dr-examples .label-wrap, #dr-examples > div > .label-wrap {
    display: none !important;
}

#dr-examples table {
    border-collapse: separate !important;
    border-spacing: 0 !important;
    width: auto !important;
    background: transparent !important;
    border: none !important;
}

#dr-examples thead { display: none !important; }

#dr-examples tbody { background: transparent !important; }

#dr-examples tr {
    background: transparent !important;
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 8px !important;
    border: none !important;
}

#dr-examples td, #dr-examples button {
    background: var(--dr-surface) !important;
    border: 1px solid var(--dr-line-soft) !important;
    padding: 0.7rem 1.05rem !important;
    cursor: pointer !important;
    transition: border-color 0.15s, color 0.15s, transform 0.1s !important;
    font-size: 0.9rem !important;
    color: var(--dr-text) !important;
    border-radius: 10px !important;
    margin: 0 !important;
    text-align: left !important;
    box-shadow: none !important;
}

#dr-examples td:hover, #dr-examples button:hover {
    border-color: var(--dr-purple) !important;
    color: var(--dr-purple) !important;
    transform: translateY(-1px);
}

/* === REPORT === */
#dr-report {
    margin-top: 2.5rem !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: var(--dr-text) !important;
    min-height: 40px;
}

#dr-report > div, #dr-report .prose {
    background: transparent !important;
    color: var(--dr-text) !important;
}

#dr-report:not(:empty) {
    border-top: 1px solid var(--dr-line-soft) !important;
    padding-top: 1.75rem !important;
}

#dr-report h1 {
    font-size: 1.85rem;
    font-weight: 700;
    color: var(--dr-blue);
    border-bottom: 1px solid var(--dr-line-soft);
    padding-bottom: 0.45rem;
    margin: 1.5rem 0 1rem;
    letter-spacing: -0.025em;
}

#dr-report h2 {
    font-size: 1.35rem;
    color: var(--dr-text);
    font-weight: 600;
    margin-top: 1.75rem;
    letter-spacing: -0.015em;
}

#dr-report h3 {
    font-size: 1.1rem;
    color: var(--dr-text);
    font-weight: 600;
    margin-top: 1.5rem;
}

#dr-report p { line-height: 1.8; }
#dr-report { overflow-wrap: anywhere; }
#dr-report pre { overflow-x: auto; }
#dr-report pre code { border: none; padding: 0; background: transparent; }
#dr-report table { display: block; max-width: 100%; overflow-x: auto; }
#dr-report blockquote { border-left: 3px solid var(--dr-blue); border-radius: 6px; }
#dr-examples tbody { display: flex; flex-wrap: wrap; gap: 0.6rem; }

#dr-report a {
    color: var(--dr-blue);
    text-decoration: underline;
    text-decoration-thickness: 2px;
    text-underline-offset: 3px;
}

#dr-report a:hover { color: var(--dr-amber); }

#dr-report code {
    background: var(--dr-surface);
    border: 1px solid var(--dr-line-soft);
    padding: 0.1rem 0.4rem;
    font-size: 0.92em;
    border-radius: 6px;
}

#dr-report pre {
    background: var(--dr-surface);
    border: 1px solid var(--dr-line-soft);
    border-radius: 6px;
    padding: 1rem 1.25rem;
}

#dr-report blockquote {
    background: var(--dr-surface);
    padding: 1rem 1.25rem;
    margin: 1rem 0;
    color: var(--dr-text);
}

#dr-report ul, #dr-report ol { padding-left: 1.5rem; }
#dr-report li { margin: 0.3rem 0; line-height: 1.6; }

#dr-report table {
    border-collapse: collapse;
    border: 1px solid var(--dr-line-soft);
}

#dr-report th, #dr-report td {
    border: 1px solid var(--dr-line-soft);
    padding: 0.5rem 0.85rem;
    text-align: left;
}

#dr-report th {
    background: var(--dr-surface);
    font-weight: 600;
    color: var(--dr-blue);
}

 .gradio-container footer { display: none !important; }

@media (prefers-reduced-motion: reduce) {
    .gradio-container *, .gradio-container *::before, .gradio-container *::after {
        transition: none !important;
    }
}

@media (max-width: 700px) {
    .gradio-container { padding: 1.5rem 1rem 3rem !important; }
    .dr-query-row { flex-direction: column !important; }
    #dr-run {
        width: 100% !important;
    }
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
