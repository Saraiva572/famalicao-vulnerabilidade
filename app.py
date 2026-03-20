import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
 
st.set_page_config(page_title="Famalicão — Análise", layout="wide")
 
# --- Credenciais ---
USER = st.secrets["STATSBOMB_USER"]
PASS = st.secrets["STATSBOMB_PASS"]
 
COMPETITION_ID    = 13
SEASON_ID         = 318
TEAM_NAME         = "Famalicão"
TRANSITION_WINDOW = 10
DEEP_ENTRY_X      = 80
team_key          = "Famalic"
auth              = (USER, PASS)
 
# ── Helpers ────────────────────────────────────────────────────────────────────
 
def get_json(url):
    r = requests.get(url, auth=auth)
    r.raise_for_status()
    return r.json()
 
def ts_to_seconds(ts):
    try:
        h, m, rest = str(ts).split(":")
        s, ms = rest.split(".")
        return int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
    except:
        return 0.0
 
def safe_xy(loc):
    if isinstance(loc, list) and len(loc) >= 2:
        return loc[0], loc[1]
    return None, None
 
def classificar_risco(vap):
    if vap < 10:   return "🟢 Baixo"
    elif vap <= 20: return "🟡 Médio"
    return "🔴 Alto"
 
def corredor(y):
    if y is None: return "Desconhecido"
    if y < 26.7:  return "Esquerdo"
    if y < 53.3:  return "Central"
    return "Direito"
 
# ── Carregar matches ────────────────────────────────────────────────────────────
 
@st.cache_data(ttl=3600, show_spinner="A carregar lista de jogos...")
def carregar_matches():
    url = (f"https://data.statsbombservices.com/api/v6/competitions/"
           f"{COMPETITION_ID}/seasons/{SEASON_ID}/matches")
    matches = pd.json_normalize(get_json(url), sep=".")
    HOME_COL = "home_team.home_team_name"
    AWAY_COL = "away_team.away_team_name"
    mask = (
        (matches["match_status"] == "available") &
        (
            matches[HOME_COL].str.contains(team_key, case=False, na=False) |
            matches[AWAY_COL].str.contains(team_key, case=False, na=False)
        )
    )
    tm = matches[mask].copy()
    def get_opp(row):
        if team_key.lower() in row[HOME_COL].lower(): return row[AWAY_COL]
        return row[HOME_COL]
    tm["opponent"]   = tm.apply(get_opp, axis=1)
    tm["match_date"] = pd.to_datetime(tm["match_date"])
    tm["label"]      = tm["match_date"].dt.strftime("%Y-%m-%d") + " vs " + tm["opponent"]
    return tm.sort_values("match_date").reset_index(drop=True)
 
# ── Carregar eventos de um jogo ─────────────────────────────────────────────────
 
@st.cache_data(ttl=3600, show_spinner="A carregar eventos...")
def carregar_eventos(match_id):
    ev = pd.json_normalize(
        get_json(f"https://data.statsbombservices.com/api/v8/events/{match_id}"),
        sep="."
    )
    ev["time_s"] = ev["timestamp"].apply(ts_to_seconds) + (ev["period"] - 1) * 45 * 60
    ev["loc_x"], ev["loc_y"] = zip(*ev["location"].apply(safe_xy))
    ev["corredor"] = ev["loc_y"].apply(corredor)
    return ev
 
# ── Calcular métricas de vulnerabilidade (todos os jogos) ───────────────────────
 
@st.cache_data(ttl=3600, show_spinner="A calcular métricas de vulnerabilidade...")
def carregar_vap(team_matches):
    results = []
    for _, row in team_matches.iterrows():
        match_id   = int(row["match_id"])
        match_date = row["match_date"].strftime("%Y-%m-%d")
        opponent   = row["opponent"]
 
        ev = carregar_eventos(match_id)
        TYPE_COL    = "type.name"
        POSS_COL    = "possession_team.name"
        PATTERN_COL = "play_pattern.name"
        PASS_OUT    = "pass.outcome.name"
        SHOT_XG     = "shot.statsbomb_xg"
 
        fama_ev = ev[ev[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower())].copy()
 
        loss_mask = (
            (fama_ev[TYPE_COL].isin({"Miscontrol", "Dispossessed"})) |
            (
                (fama_ev[TYPE_COL] == "Pass") &
                (fama_ev.get(PASS_OUT, pd.Series(dtype=str)) == "Incomplete") &
                (fama_ev["loc_x"].apply(lambda x: x <= 40 if x is not None else False))
            )
        )
        losses = fama_ev[loss_mask].copy()
 
        hp = ca = cl = dp = 0
        xg = 0.0
 
        for _, le in losses.iterrows():
            opp_after = ev[
                (ev["possession"] > le["possession"]) &
                (ev["time_s"] >= le["time_s"]) &
                (ev["time_s"] <= le["time_s"] + TRANSITION_WINDOW) &
                (~ev[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower()))
            ]
            if opp_after.empty: continue
            for _, shot in opp_after[opp_after[TYPE_COL] == "Shot"].iterrows():
                pp = str(shot.get(PATTERN_COL, ""))
                if "Counter" in pp: ca += 1
                elif shot["time_s"] - le["time_s"] <= 5: hp += 1
                xg_val = shot.get(SHOT_XG, 0) or 0
                if xg_val >= 0.15: cl += 1
                xg += xg_val
            dp += len(opp_after[opp_after["loc_x"].apply(lambda x: x >= DEEP_ENTRY_X if x is not None else False)])
 
        results.append({
            "match_id": match_id, "match_date": match_date, "opponent": opponent,
            "team_match_high_press_shots_conceded": hp,
            "team_match_counter_attacking_shots_conceded": ca,
            "team_match_shots_in_clear_conceded": cl,
            "team_match_deep_progressions_conceded": dp,
            "team_match_xg_conceded_after_loss": round(xg, 3),
        })
 
    df = pd.DataFrame(results)
    df["VAP"]          = 4*df["team_match_high_press_shots_conceded"] + 3*df["team_match_counter_attacking_shots_conceded"] + 2*df["team_match_shots_in_clear_conceded"] + 0.1*df["team_match_deep_progressions_conceded"]
    df["Risco"]        = df["VAP"].apply(classificar_risco)
    df["Media_Movel_3"] = df["VAP"].rolling(3, min_periods=1).mean()
    return df
 
# ── Desenhar campo ──────────────────────────────────────────────────────────────
 
def draw_pitch(ax, half=True):
    ax.set_facecolor("#f5f5f0")
    fig_color = "#4a4a4a"
    # Campo completo StatsBomb: 120x80. Mostramos só metade defensiva (0-60)
    xlim = (0, 60) if half else (0, 120)
    ylim = (0, 80)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
 
    # Linhas do campo
    for rect_args in [
        (0, 0, xlim[1], 80),       # campo
        (0, 18, 18, 44),            # grande área defensiva
        (0, 30, 6, 20),             # pequena área defensiva
    ]:
        ax.add_patch(patches.Rectangle(
            (rect_args[0], rect_args[1]), rect_args[2], rect_args[3],
            fill=False, edgecolor=fig_color, linewidth=1.5
        ))
    # Linha de meio campo
    if not half:
        ax.axvline(60, color=fig_color, linewidth=1.5)
        ax.add_patch(patches.Circle((60, 40), 10, fill=False, edgecolor=fig_color, linewidth=1.5))
    # Corredores
    for y in [26.7, 53.3]:
        ax.axhline(y, color=fig_color, linewidth=0.8, linestyle="--", alpha=0.4)
    ax.text(2, 13, "Esq", fontsize=7, color=fig_color, alpha=0.5)
    ax.text(2, 40, "Cen", fontsize=7, color=fig_color, alpha=0.5)
    ax.text(2, 67, "Dir", fontsize=7, color=fig_color, alpha=0.5)
 
def heatmap_fig(x_vals, y_vals, title, half=True):
    fig, ax = plt.subplots(figsize=(8, 5))
    draw_pitch(ax, half=half)
    if len(x_vals) > 0:
        ax.hexbin(x_vals, y_vals, gridsize=20, cmap="YlOrRd", alpha=0.7,
                  extent=(0, 60 if half else 120, 0, 80), mincnt=1)
    ax.set_title(title, fontsize=11, pad=8)
    fig.tight_layout()
    return fig
 
# ══════════════════════════════════════════════════════════════════════════════
# NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
 
pagina = st.sidebar.radio("📂 Página", ["📊 Vulnerabilidade", "🗺️ Heatmaps"])
 
team_matches = carregar_matches()
 
# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — VULNERABILIDADE
# ══════════════════════════════════════════════════════════════════════════════
 
if pagina == "📊 Vulnerabilidade":
    st.title("🔴 Famalicão — Vulnerabilidade após Perda")
    st.caption("Dados reais StatsBomb — Liga Portugal 25/26")
 
    df = carregar_vap(team_matches)
 
    # Filtros
    st.sidebar.header("Filtros")
    adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
    sel = st.sidebar.selectbox("Adversário", adversarios)
    df_f = df.copy() if sel == "Todos" else df[df["opponent"] == sel].copy()
 
    # Resumo
    st.subheader("Resumo Executivo")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("VAP média",        f"{df_f['VAP'].mean():.2f}")
    c2.metric("Maior VAP",        f"{df_f['VAP'].max():.2f}")
    c3.metric("Menor VAP",        f"{df_f['VAP'].min():.2f}")
    c4.metric("Jogo mais crítico", df_f.loc[df_f["VAP"].idxmax(), "opponent"])
    c5.metric("xG sofrido total", f"{df_f['team_match_xg_conceded_after_loss'].sum():.2f}")
 
    # Semáforo
    ultimo = df_f.iloc[-1]
    st.subheader("Semáforo de risco do último jogo")
    st.markdown(f"### {ultimo['Risco']}  |  vs {ultimo['opponent']}  |  VAP = {ultimo['VAP']:.2f}")
 
    # Tabela
    st.subheader("Tabela completa")
    cols = [c for c in [
        "match_id","match_date","opponent",
        "team_match_high_press_shots_conceded",
        "team_match_counter_attacking_shots_conceded",
        "team_match_shots_in_clear_conceded",
        "team_match_deep_progressions_conceded",
        "team_match_xg_conceded_after_loss",
        "VAP","Risco","Media_Movel_3"
    ] if c in df_f.columns]
    st.dataframe(df_f[cols], use_container_width=True)
 
    # Ranking
    st.subheader("Ranking dos jogos mais vulneráveis")
    ranking = df_f.sort_values("VAP", ascending=False)[
        ["match_date","opponent","VAP","team_match_xg_conceded_after_loss","Risco"]
    ].reset_index(drop=True)
    ranking.index += 1
    st.dataframe(ranking, use_container_width=True)
 
    # Gráficos
    st.subheader("Linha temporal da vulnerabilidade")
    st.line_chart(df_f.set_index("opponent")[["VAP","Media_Movel_3"]])
 
    st.subheader("Vulnerabilidade por jogo")
    st.bar_chart(df_f.set_index("opponent")["VAP"])
 
    st.subheader("xG sofrido após perda por jogo")
    st.bar_chart(df_f.set_index("opponent")["team_match_xg_conceded_after_loss"])
 
 
# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — HEATMAPS
# ══════════════════════════════════════════════════════════════════════════════
 
elif pagina == "🗺️ Heatmaps":
    st.title("🗺️ Heatmaps — Construção e Perdas")
    st.caption("1º terço defensivo do Famalicão | Campo StatsBomb 120×80")
 
    # Filtros
    st.sidebar.header("Filtros")
 
    # Filtro por jogo
    labels = ["Todos os jogos"] + team_matches["label"].tolist()
    sel_jogo = st.sidebar.selectbox("Jogo", labels)
 
    # Filtro por adversário
    adversarios = ["Todos"] + sorted(team_matches["opponent"].unique().tolist())
    sel_adv = st.sidebar.selectbox("Adversário", adversarios)
 
    # Filtro por corredor
    sel_corredor = st.sidebar.selectbox("Corredor", ["Todos", "Esquerdo", "Central", "Direito"])
 
    # Determinar jogos a incluir
    if sel_jogo != "Todos os jogos":
        jogos = team_matches[team_matches["label"] == sel_jogo]["match_id"].tolist()
    elif sel_adv != "Todos":
        jogos = team_matches[team_matches["opponent"] == sel_adv]["match_id"].tolist()
    else:
        jogos = team_matches["match_id"].tolist()
 
    # Carregar e juntar eventos
    all_events = []
    with st.spinner(f"A carregar eventos de {len(jogos)} jogo(s)..."):
        for mid in jogos:
            ev = carregar_eventos(int(mid))
            all_events.append(ev)
 
    if not all_events:
        st.warning("Nenhum jogo encontrado.")
        st.stop()
 
    ev_all = pd.concat(all_events, ignore_index=True)
 
    TYPE_COL = "type.name"
    POSS_COL = "possession_team.name"
    PASS_OUT = "pass.outcome.name"
 
    # Filtrar eventos do Famalicão no 1º terço
    fama = ev_all[ev_all[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower())].copy()
    fama_1t = fama[fama["loc_x"].apply(lambda x: x <= 60 if x is not None else False)].copy()
 
    # Filtro por corredor
    if sel_corredor != "Todos":
        fama_1t = fama_1t[fama_1t["corredor"] == sel_corredor]
 
    st.markdown(f"**{len(jogos)} jogo(s) selecionado(s)** | Corredor: {sel_corredor}")
 
    col1, col2 = st.columns(2)
 
    # ── Heatmap 1: Passes durante a construção ──────────────────────────────────
    with col1:
        passes = fama_1t[fama_1t[TYPE_COL] == "Pass"].copy()
        x_vals = passes["loc_x"].dropna().tolist()
        y_vals = passes["loc_y"].dropna().tolist()
        fig1 = heatmap_fig(x_vals, y_vals,
                           f"Passes na Construção (n={len(x_vals)})", half=True)
        st.pyplot(fig1)
        plt.close(fig1)
 
    # ── Heatmap 2: Perdas de bola ───────────────────────────────────────────────
    with col2:
        loss_mask = (
            (fama_1t[TYPE_COL].isin({"Miscontrol", "Dispossessed"})) |
            (
                (fama_1t[TYPE_COL] == "Pass") &
                (fama_1t.get(PASS_OUT, pd.Series(dtype=str)) == "Incomplete")
            )
        )
        perdas = fama_1t[loss_mask].copy()
        x_vals2 = perdas["loc_x"].dropna().tolist()
        y_vals2 = perdas["loc_y"].dropna().tolist()
        fig2 = heatmap_fig(x_vals2, y_vals2,
                           f"Perdas de Bola na Construção (n={len(x_vals2)})", half=True)
        st.pyplot(fig2)
        plt.close(fig2)
 
    # ── Estatísticas por corredor ───────────────────────────────────────────────
    st.subheader("Distribuição por corredor")
    c1, c2 = st.columns(2)
 
    with c1:
        st.markdown("**Passes por corredor**")
        passes_all = fama_1t[fama_1t[TYPE_COL] == "Pass"]
        dist_passes = passes_all["corredor"].value_counts().reset_index()
        dist_passes.columns = ["Corredor", "Passes"]
        st.dataframe(dist_passes, use_container_width=True)
 
    with c2:
        st.markdown("**Perdas por corredor**")
        perdas_all = fama_1t[loss_mask]
        dist_perdas = perdas_all["corredor"].value_counts().reset_index()
        dist_perdas.columns = ["Corredor", "Perdas"]
        st.dataframe(dist_perdas, use_container_width=True)

