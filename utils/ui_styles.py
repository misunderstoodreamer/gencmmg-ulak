"""Temiz light mode UI stilleri."""

import streamlit as st


def apply_apple_style():
    """Global light mode stillerini uygula."""
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #0f172a;
        }

        .stApp {
            background-color: #ffffff;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }

        /* Sayfa başlığı */
        .page-header {
            margin-bottom: 1.75rem;
            padding-bottom: 1.25rem;
            border-bottom: 1px solid #e2e8f0;
        }

        .page-header h1 {
            font-size: 1.75rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0 0 0.35rem 0;
            letter-spacing: -0.03em;
        }

        .page-header .subtitle {
            color: #64748b;
            font-size: 0.95rem;
            margin: 0;
        }

        /* Kart */
        .ui-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }

        .ui-card h3 {
            font-size: 1.05rem;
            font-weight: 600;
            margin: 0 0 0.75rem 0;
            color: #0f172a;
        }

        .ui-card p {
            margin: 0.35rem 0;
            font-size: 0.9rem;
            color: #334155;
            line-height: 1.5;
        }

        .ui-card-muted {
            background: #f8fafc;
            border-color: #e2e8f0;
        }

        /* Form kutusu */
        .form-panel {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-top: 1rem;
        }

        /* Butonlar */
        .stButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            padding: 0.5rem 1rem !important;
            box-shadow: none !important;
            transition: background 0.15s ease !important;
        }

        .stButton > button:hover {
            background: #1d4ed8 !important;
            transform: none !important;
        }

        .stFormSubmitButton > button {
            background: #2563eb !important;
            color: #ffffff !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
        }

        /* Inputlar */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea,
        .stSelectbox > div > div > div,
        .stDateInput > div > div > input {
            border-radius: 8px !important;
            border: 1px solid #cbd5e1 !important;
            background: #ffffff !important;
            color: #0f172a !important;
        }

        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12) !important;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 8px;
            color: #334155 !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: #eff6ff !important;
            color: #1d4ed8 !important;
        }

        /* Metrikler */
        [data-testid="stMetric"] {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.75rem 1rem;
        }

        [data-testid="stMetricLabel"] {
            color: #64748b !important;
            font-size: 0.8rem !important;
        }

        [data-testid="stMetricValue"] {
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        /* Durum renkleri */
        .status-onaylandi { color: #16a34a; font-weight: 600; }
        .status-reddedildi { color: #dc2626; font-weight: 600; }
        .status-bekliyor { color: #d97706; font-weight: 600; }

        .badge {
            display: inline-block;
            padding: 2px 10px;
            border-radius: 999px;
            font-size: 0.72rem;
            font-weight: 600;
        }

        .badge-acil { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
        .badge-admin { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

        .sla-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: #fef2f2;
            color: #b91c1c;
            border: 1px solid #fecaca;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .nav-tile {
            display: block;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 1rem 1.25rem;
            text-decoration: none;
            color: #0f172a;
            margin-bottom: 0.5rem;
            transition: border-color 0.15s, box-shadow 0.15s;
        }

        .nav-tile:hover {
            border-color: #93c5fd;
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.08);
        }

        #MainMenu, footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def set_sidebar_visible(visible: bool):
    """Giriş öncesi sidebar'ı tamamen gizle veya göster."""
    if visible:
        css = """
        <style>
        [data-testid="stSidebar"] { display: block !important; }
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] { display: flex !important; }
        section[data-testid="stMain"] { margin-left: auto !important; }
        </style>
        """
    else:
        css = """
        <style>
        [data-testid="stSidebar"] { display: none !important; }
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="collapsedControl"] { display: none !important; }
        section[data-testid="stMain"] {
            margin-left: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stAppViewContainer"] > section.main > div {
            max-width: 1100px;
            margin: 0 auto;
        }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


def glass_header(title: str, subtitle: str = ""):
    """Sayfa başlığı."""
    sub_html = f'<p class="subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-header"><h1>{title}</h1>{sub_html}</div>',
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str = ""):
    """glass_header alias."""
    glass_header(title, subtitle)


def sla_warning_badge(hours_waiting: float) -> str:
    """48+ saat bekleyen talepler için rozet."""
    if hours_waiting >= 48:
        return f'<span class="sla-badge">⚠ {int(hours_waiting)}s bekleme</span>'
    return ""


def hide_sidebar_pages_for_role(rol: str):
    """Rol bazlı sidebar sayfa gizleme. Admin tüm sayfaları görür."""
    if rol == "Admin":
        return

    if rol == "Il_Temsilcisi":
        css = """
        <style>
        [data-testid="stSidebarNav"] li:has(a[href*="Merkez_Onay"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Admin_Panel"]) { display: none !important; }
        </style>
        """
    elif rol == "Merkez_Onayci":
        css = """
        <style>
        [data-testid="stSidebarNav"] li:has(a[href*="Yeni_Talep"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Talep_Takip"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Admin_Panel"]) { display: none !important; }
        </style>
        """
    else:
        css = """
        <style>
        [data-testid="stSidebarNav"] li:has(a[href*="Yeni_Talep"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Talep_Takip"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Merkez_Onay"]) { display: none !important; }
        [data-testid="stSidebarNav"] li:has(a[href*="Admin_Panel"]) { display: none !important; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)
