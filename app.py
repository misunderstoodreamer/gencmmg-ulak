"""Genç MMG event approval platform — application entrypoint."""

import logging
from pathlib import Path

import streamlit as st

from core.auth import SessionUser, current_user, logout
from ui.components import sidebar_account
from ui.theme import apply_theme

ASSETS = Path(__file__).parent / "assets"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

st.set_page_config(
    page_title="Genç MMG Etkinlik Onay",
    page_icon=str(ASSETS / "mark.svg"),
    layout="wide",
)
apply_theme()


def _pages_for(user: SessionUser) -> dict[str, list[st.Page]]:
    sections: dict[str, list[st.Page]] = {
        "": [st.Page("views/home.py", title="Genel bakış", icon=":material/space_dashboard:", default=True)],
    }
    requests = []
    if user.can_submit:
        requests.append(st.Page("views/new_request.py", title="Yeni talep", icon=":material/add_circle:"))
    requests.append(
        st.Page(
            "views/request_tracking.py",
            title="Tüm talepler" if user.can_view_all else "Taleplerim",
            icon=":material/list_alt:",
        )
    )
    sections["Talepler"] = requests

    headquarters = []
    if user.can_review:
        headquarters.append(st.Page("views/approval_queue.py", title="Onay havuzu", icon=":material/fact_check:"))
    if user.can_view_all:
        headquarters.append(st.Page("views/reports.py", title="Raporlar", icon=":material/monitoring:"))
    if headquarters:
        sections["Genel Merkez"] = headquarters
    if user.is_admin:
        sections["Yönetim"] = [
            st.Page("views/admin_panel.py", title="Yönetim paneli", icon=":material/admin_panel_settings:"),
        ]
    return sections


user = current_user()

if user is None:
    navigation = st.navigation([st.Page("views/login.py", title="Giriş")], position="hidden")
else:
    st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "mark.svg"))
    navigation = st.navigation(_pages_for(user))
    sidebar_account(user, on_logout=logout)

navigation.run()
