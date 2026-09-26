"""Global styles that complement the theme defined in .streamlit/config.toml."""

from __future__ import annotations

import streamlit as st

_CSS = """
<style>
.block-container { max-width: 1180px; padding-top: 2.25rem; padding-bottom: 4rem; }
[data-testid="stDecoration"] { display: none; }

/* Page header */
.page-header { margin: 0 0 1.75rem; padding-bottom: 1.25rem; border-bottom: 1px solid #e2e6ec; }
.page-header .eyebrow {
    margin: 0 0 .35rem; font-size: .75rem; font-weight: 600; letter-spacing: .08em;
    text-transform: uppercase; color: #1d4ed8;
}
.page-header h1 { margin: 0; padding: 0; font-size: 1.75rem; line-height: 1.25; }
.page-header .subtitle { margin: .4rem 0 0; color: #64748b; font-size: .95rem; }

/* Surfaces: keyed containers (st.container(key="card-..."/"panel-...")) */
[class*="st-key-card-"], [class*="st-key-panel-"] {
    background: #ffffff;
    border-radius: .75rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
[class*="st-key-card-"] { padding: 1.25rem 1.4rem !important; }
[class*="st-key-panel-"] { padding: 1.75rem !important; }
[data-testid="stMetric"] {
    background: #ffffff; border-radius: .75rem; box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
}
[data-testid="stMetricLabel"] p { color: #64748b; font-weight: 500; font-size: .85rem; }

/* Request card */
.card-title { margin: 0; font-size: 1.05rem; font-weight: 600; color: #0f172a; }
.card-meta { margin: .2rem 0 0; font-size: .82rem; color: #64748b; }
.card-meta code { font-size: .78rem; color: #334155; background: #f1f4f8; padding: .05rem .35rem; border-radius: .3rem; }
.field-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: .9rem 1.5rem; margin: .35rem 0 .15rem;
}
.field-label {
    margin: 0 0 .15rem; font-size: .7rem; font-weight: 600; letter-spacing: .06em;
    text-transform: uppercase; color: #94a3b8;
}
.field-value { margin: 0; font-size: .9rem; color: #0f172a; line-height: 1.45; white-space: pre-wrap; }
.field-value.muted { color: #64748b; }
.attachments { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .2rem; }
.attachment {
    display: inline-flex; align-items: center; padding: .25rem .65rem; border-radius: 999px;
    border: 1px solid #dbe3ee; background: #f8fafc; color: #1d4ed8 !important;
    font-size: .82rem; font-weight: 500; text-decoration: none !important;
}
.attachment::before { content: ""; width: .5rem; height: .6rem; margin-right: .45rem; border: 1.5px solid currentColor; border-radius: 1px; }
.attachment:hover { background: #eff6ff; border-color: #93c5fd; }
.decision-box {
    margin-top: .75rem; padding: .85rem 1rem; border-radius: .5rem;
    background: #f8fafc; border: 1px solid #e2e6ec;
}

/* Login */
.brand { display: flex; align-items: center; gap: .75rem; margin-bottom: 1.5rem; }
.brand-name { margin: 0; font-size: 1.05rem; font-weight: 700; color: #0f172a; line-height: 1.2; }
.brand-tagline { margin: 0; font-size: .8rem; color: #64748b; }
.login-title { margin: 0 0 .35rem; font-size: 1.4rem; font-weight: 700; color: #0f172a; }
.login-lead { margin: 0 0 1.25rem; font-size: .92rem; color: #64748b; }
.login-foot { margin-top: 1.25rem; font-size: .8rem; color: #94a3b8; text-align: center; }

/* Sidebar account block */
.account { padding: .85rem .9rem; border-radius: .6rem; background: #13284a; margin-bottom: .5rem; }
.account-email { margin: 0; font-size: .85rem; font-weight: 600; color: #f1f5f9; word-break: break-all; }
.account-meta { margin: .2rem 0 0; font-size: .75rem; color: #94a3b8; }

.figure { margin: .75rem 0 0; }
.figure-value { margin: 0; font-size: 1.5rem; font-weight: 600; color: #0f172a; }
.figure-label { margin: 0; font-size: .8rem; color: #64748b; }

.empty-state { padding: 2.5rem 1rem; text-align: center; color: #64748b; }
.empty-state strong { display: block; color: #0f172a; font-size: 1rem; margin-bottom: .25rem; }
</style>
"""


def apply_theme() -> None:
    st.html(_CSS)
