import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
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

MESES_PT = {
    1:"Janeiro", 2:"Fevereiro", 3:"Março", 4:"Abril",
    5:"Maio", 6:"Junho", 7:"Julho", 8:"Agosto",
    9:"Setembro", 10:"Outubro", 11:"Novembro", 12:"Dezembro"
}

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
    if vap < 10:    return "🟢 Baixo"
    elif vap <= 20: return "🟡 Médio"
    return "🔴 Alto"

def corredor_h(y):
    """Corredor horizontal (largura do campo)"""
    if y is None: return "Desconhecido"
    if y < 26.7:  return "Esquerdo"
    if y < 53.3:  return "Central"
    return "Direito"

def corredor_v(x):
    """Corredor vertical (profundidade — só 1º terço 0-40)"""
    if x is None: return "Desconhecido"
    if x < 13.3:  return "Zona 1 (GR)"
    if x < 26.7:  return "Zona 2"
    return "Zona 3 (Saída)"

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
    tm["mes_ano"]    = tm["match_date"].apply(lambda d: f"{MESES_PT[d.month]} {d.year}")
    tm["label"]      = tm["match_date"].dt.strftime("%Y-%m-%d") + " vs " + tm["opponent"]
    # Jogo nº por adversário (para diferenciar rematches)
    tm["jogo_num"]   = tm.groupby("opponent").cumcount() + 1
    tm["label_full"] = tm.apply(
        lambda r: f"{r['match_date'].strftime('%Y-%m-%d')} vs {r['opponent']}" +
                  (f" (J{r['jogo_num']})" if tm[tm["opponent"]==r["opponent"]].shape[0]>1 else ""),
        axis=1
    )
    return tm.sort_values("match_date").reset_index(drop=True)

# ── Carregar eventos ────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="A carregar eventos...")
def carregar_eventos(match_id):
    ev = pd.json_normalize(
        get_json(f"https://data.statsbombservices.com/api/v8/events/{match_id}"),
        sep="."
    )
    ev["time_s"] = ev["timestamp"].apply(ts_to_seconds) + (ev["period"] - 1) * 45 * 60
    ev["loc_x"], ev["loc_y"] = zip(*ev["location"].apply(safe_xy))
    ev["corredor_h"] = ev["loc_y"].apply(corredor_h)
    ev["corredor_v"] = ev["loc_x"].apply(corredor_v)
    return ev

# ── Calcular VAP ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="A calcular métricas...")
def carregar_vap(team_matches):
    results = []
    for _, row in team_matches.iterrows():
        match_id   = int(row["match_id"])
        match_date = row["match_date"].strftime("%Y-%m-%d")
        opponent   = row["opponent"]
        jogo_num   = int(row["jogo_num"])
        mes_ano    = row["mes_ano"]
        label_full = row["label_full"]

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
            dp += len(opp_after[opp_after["loc_x"].apply(
                lambda x: x >= DEEP_ENTRY_X if x is not None else False)])

        results.append({
            "match_id":    match_id,
            "match_date":  match_date,
            "opponent":    opponent,
            "jogo_num":    jogo_num,
            "mes_ano":     mes_ano,
            "label_full":  label_full,
            "team_name":   TEAM_NAME,
            "team_match_high_press_shots_conceded":        hp,
            "team_match_counter_attacking_shots_conceded": ca,
            "team_match_shots_in_clear_conceded":          cl,
            "team_match_deep_progressions_conceded":       dp,
            "team_match_xg_conceded_after_loss":           round(xg, 3),
        })

    df = pd.DataFrame(results)
    df["VAP"]           = 4*df["team_match_high_press_shots_conceded"] + 3*df["team_match_counter_attacking_shots_conceded"] + 2*df["team_match_shots_in_clear_conceded"] + 0.1*df["team_match_deep_progressions_conceded"]
    df["Risco"]         = df["VAP"].apply(classificar_risco)
    df["Media_Movel_3"] = df["VAP"].rolling(3, min_periods=1).mean()
    return df

# ── Desenhar campo com grelha ───────────────────────────────────────────────────

def draw_pitch_grid(ax):
    """Campo StatsBomb metade defensiva (0-60x80) com grelha de corredores."""
    ax.set_facecolor("#f0f0e8")
    fc = "#333333"
    ax.set_xlim(0, 60)
    ax.set_ylim(0, 80)
    ax.set_aspect("equal")
    ax.axis("off")

    # Fundo dos corredores horizontais (alternado)
    for i, (y0, y1, c) in enumerate([(0,26.7,"#e8f4e8"),(26.7,53.3,"#f4f4e8"),(53.3,80,"#e8f4e8")]):
        ax.add_patch(patches.Rectangle((0,y0),60,y1-y0, facecolor=c, alpha=0.4, zorder=0))

    # Fundo dos corredores verticais (alternado)
    for x0, x1, c in [(0,13.3,"#e8e8f4"),(13.3,26.7,"#f4f4f4"),(26.7,40,"#e8e8f4")]:
        ax.add_patch(patches.Rectangle((x0,0),x1-x0,80, facecolor=c, alpha=0.2, zorder=0))

    # Linhas do campo
    ax.add_patch(patches.Rectangle((0,0),60,80, fill=False, edgecolor=fc, linewidth=2, zorder=3))
    ax.add_patch(patches.Rectangle((0,18),18,44, fill=False, edgecolor=fc, linewidth=1.5, zorder=3))
    ax.add_patch(patches.Rectangle((0,30),6,20,  fill=False, edgecolor=fc, linewidth=1.5, zorder=3))
    ax.axvline(60, color=fc, linewidth=2, zorder=3)

    # Grelha corredores horizontais
    for y in [26.7, 53.3]:
        ax.axhline(y, color="#888888", linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)

    # Grelha corredores verticais (só até x=40)
    for x in [13.3, 26.7]:
        ax.axvline(x, color="#888888", linewidth=1.2, linestyle="--", alpha=0.7, zorder=2)
    ax.axvline(40, color="#cc4444", linewidth=1.5, linestyle="-", alpha=0.6, zorder=2)

    # Labels corredores horizontais
    for y, label in [(13, "Esq"), (40, "Cen"), (67, "Dir")]:
        ax.text(58, y, label, fontsize=8, color="#555555", ha="right", va="center", zorder=4)

    # Labels corredores verticais
    for x, label in [(6.7, "GR"), (20, "Z2"), (33.3, "Z3")]:
        ax.text(x, 78, label, fontsize=7, color="#555555", ha="center", va="top", zorder=4)

    ax.text(41, 78, "Limite\n1ºT", fontsize=6, color="#cc4444", ha="left", va="top", zorder=4)

def heatmap_fig(x_vals, y_vals, title):
    fig, ax = plt.subplots(figsize=(9, 6))
    draw_pitch_grid(ax)
    if len(x_vals) > 2:
        hb = ax.hexbin(x_vals, y_vals, gridsize=18, cmap="YlOrRd",
                       alpha=0.75, extent=(0,60,0,80), mincnt=1, zorder=1)
        plt.colorbar(hb, ax=ax, label="Densidade", shrink=0.7)
    else:
        ax.scatter(x_vals, y_vals, color="red", s=60, zorder=5, alpha=0.8)
    ax.set_title(title, fontsize=11, pad=10, fontweight="bold")
    fig.tight_layout()
    return fig

# ── Gráfico de barras com cores por jogo repetido ──────────────────────────────

def bar_chart_colored(df, col, title, ylabel):
    fig, ax = plt.subplots(figsize=(14, 5))
    base_colors = plt.cm.Set2.colors
    adv_color_map = {}
    color_idx = 0
    bars_info = []

    for _, row in df.iterrows():
        adv = row["opponent"]
        jnum = row["jogo_num"]
        if adv not in adv_color_map:
            adv_color_map[adv] = {}
        if jnum not in adv_color_map[adv]:
            adv_color_map[adv][jnum] = base_colors[color_idx % len(base_colors)]
            color_idx += 1
        bars_info.append((row["label_full"], row[col], adv_color_map[adv][jnum], adv, jnum))

    labels  = [b[0] for b in bars_info]
    values  = [b[1] for b in bars_info]
    colors  = [b[2] for b in bars_info]

    bars = ax.bar(range(len(labels)), values, color=colors, edgecolor="white", linewidth=0.8)

    # Legenda apenas para adversários com 2+ jogos
    repeated = {adv for adv, jmap in adv_color_map.items() if len(jmap) > 1}
    legend_handles = []
    for adv in sorted(repeated):
        for jnum, color in sorted(adv_color_map[adv].items()):
            import matplotlib.patches as mpatches
            legend_handles.append(mpatches.Patch(color=color, label=f"{adv} (J{jnum})"))
    if legend_handles:
        ax.legend(handles=legend_handles, fontsize=8, loc="upper right", title="Jogos repetidos")

    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=12, fontweight="bold", pad=10)
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top","right"]].set_visible(False)
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
    st.caption("Liga Portugal 25/26 | Dados StatsBomb")

    df = carregar_vap(team_matches)

    # Filtros sidebar
    st.sidebar.header("Filtros")

    meses_disponiveis = ["Todos"] + list(dict.fromkeys(df["mes_ano"].tolist()))
    sel_mes = st.sidebar.selectbox("Mês", meses_disponiveis)

    adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
    sel_adv = st.sidebar.selectbox("Adversário", adversarios)

    df_f = df.copy()
    if sel_mes != "Todos":
        df_f = df_f[df_f["mes_ano"] == sel_mes]
    if sel_adv != "Todos":
        df_f = df_f[df_f["opponent"] == sel_adv]

    if df_f.empty:
        st.warning("Nenhum jogo encontrado com os filtros selecionados.")
        st.stop()

    # Resumo
    st.subheader("Resumo Executivo")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("VAP média",         f"{df_f['VAP'].mean():.2f}")
    c2.metric("Maior VAP",         f"{df_f['VAP'].max():.2f}")
    c3.metric("Menor VAP",         f"{df_f['VAP'].min():.2f}")
    c4.metric("Jogo mais crítico",  df_f.loc[df_f["VAP"].idxmax(), "label_full"])
    c5.metric("xG sofrido total",  f"{df_f['team_match_xg_conceded_after_loss'].sum():.2f}")

    # Semáforo
    ultimo = df_f.iloc[-1]
    st.subheader("Semáforo de risco do último jogo")
    st.markdown(f"### {ultimo['Risco']}  |  {ultimo['label_full']}  |  VAP = {ultimo['VAP']:.2f}")

    # Linha cronológica
    st.subheader("Linha cronológica da vulnerabilidade")
    fig_line, ax_line = plt.subplots(figsize=(14, 4))
    ax_line.plot(df_f["label_full"], df_f["VAP"], marker="o", color="#e74c3c",
                 linewidth=2, markersize=6, label="VAP", zorder=3)
    ax_line.plot(df_f["label_full"], df_f["Media_Movel_3"], marker="s", color="#3498db",
                 linewidth=1.5, markersize=4, linestyle="--", label="Média Móvel 3", zorder=2)
    ax_line.axhline(10, color="#2ecc71", linewidth=1, linestyle=":", alpha=0.7)
    ax_line.axhline(20, color="#e67e22", linewidth=1, linestyle=":", alpha=0.7)
    ax_line.fill_between(range(len(df_f)), 0, 10, alpha=0.05, color="green")
    ax_line.fill_between(range(len(df_f)), 10, 20, alpha=0.05, color="orange")
    ax_line.fill_between(range(len(df_f)), 20, df_f["VAP"].max()+2, alpha=0.05, color="red")
    ax_line.set_xticks(range(len(df_f)))
    ax_line.set_xticklabels(df_f["label_full"], rotation=45, ha="right", fontsize=8)
    ax_line.set_ylabel("VAP", fontsize=10)
    ax_line.legend(fontsize=9)
    ax_line.grid(axis="y", alpha=0.3)
    ax_line.spines[["top","right"]].set_visible(False)
    fig_line.tight_layout()
    st.pyplot(fig_line)
    plt.close(fig_line)

    # Gráfico VAP por jogo com cores
    st.subheader("VAP por jogo")
    fig_vap = bar_chart_colored(df_f, "VAP", "VAP por jogo", "VAP")
    st.pyplot(fig_vap)
    plt.close(fig_vap)

    # Gráfico xG por jogo com cores
    st.subheader("xG sofrido após perda por jogo")
    fig_xg = bar_chart_colored(df_f, "team_match_xg_conceded_after_loss",
                                "xG sofrido após perda", "xG")
    st.pyplot(fig_xg)
    plt.close(fig_xg)

    # Tabela
    st.subheader("Tabela completa")
    cols = [c for c in [
        "match_id","match_date","opponent","jogo_num","mes_ano",
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
        ["label_full","VAP","team_match_xg_conceded_after_loss","Risco"]
    ].reset_index(drop=True)
    ranking.index += 1
    st.dataframe(ranking, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — HEATMAPS
# ══════════════════════════════════════════════════════════════════════════════

elif pagina == "🗺️ Heatmaps":
    st.title("🗺️ Heatmaps — Construção e Perdas")
    st.caption("1º terço defensivo | Grelha de corredores horizontais e verticais")

    # Filtros sidebar
    st.sidebar.header("Filtros")

    meses_disponiveis = ["Todos"] + list(dict.fromkeys(team_matches["mes_ano"].tolist()))
    sel_mes = st.sidebar.selectbox("Mês", meses_disponiveis)

    adversarios = ["Todos"] + sorted(team_matches["opponent"].unique().tolist())
    sel_adv = st.sidebar.selectbox("Adversário", adversarios)

    tm_f = team_matches.copy()
    if sel_mes != "Todos":
        tm_f = tm_f[tm_f["mes_ano"] == sel_mes]
    if sel_adv != "Todos":
        tm_f = tm_f[tm_f["opponent"] == sel_adv]

    jogos = tm_f["match_id"].tolist()

    if not jogos:
        st.warning("Nenhum jogo encontrado.")
        st.stop()

    # Carregar eventos
    all_events = []
    with st.spinner(f"A carregar {len(jogos)} jogo(s)..."):
        for mid in jogos:
            ev = carregar_eventos(int(mid))
            all_events.append(ev)

    ev_all = pd.concat(all_events, ignore_index=True)

    TYPE_COL = "type.name"
    POSS_COL = "possession_team.name"
    PASS_OUT = "pass.outcome.name"

    fama = ev_all[ev_all[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower())].copy()
    fama_1t = fama[fama["loc_x"].apply(lambda x: x <= 60 if x is not None else False)].copy()

    loss_mask = (
        (fama_1t[TYPE_COL].isin({"Miscontrol", "Dispossessed"})) |
        (
            (fama_1t[TYPE_COL] == "Pass") &
            (fama_1t.get(PASS_OUT, pd.Series(dtype=str)) == "Incomplete")
        )
    )

    st.markdown(f"**{len(jogos)} jogo(s)** | Adversário: {sel_adv} | Mês: {sel_mes}")

    col1, col2 = st.columns(2)

    with col1:
        passes = fama_1t[fama_1t[TYPE_COL] == "Pass"]
        fig1 = heatmap_fig(
            passes["loc_x"].dropna().tolist(),
            passes["loc_y"].dropna().tolist(),
            f"Passes na Construção (n={len(passes)})"
        )
        st.pyplot(fig1)
        plt.close(fig1)

    with col2:
        perdas = fama_1t[loss_mask]
        fig2 = heatmap_fig(
            perdas["loc_x"].dropna().tolist(),
            perdas["loc_y"].dropna().tolist(),
            f"Perdas de Bola na Construção (n={len(perdas)})"
        )
        st.pyplot(fig2)
        plt.close(fig2)

    # Tabelas de distribuição por corredor
    st.subheader("Distribuição por corredor")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown("**Passes — corredor horizontal**")
        d = fama_1t[fama_1t[TYPE_COL]=="Pass"]["corredor_h"].value_counts().reset_index()
        d.columns = ["Corredor","Passes"]
        st.dataframe(d, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("**Passes — corredor vertical**")
        d = fama_1t[fama_1t[TYPE_COL]=="Pass"]["corredor_v"].value_counts().reset_index()
        d.columns = ["Zona","Passes"]
        st.dataframe(d, use_container_width=True, hide_index=True)

    with c3:
        st.markdown("**Perdas — corredor horizontal**")
        d = fama_1t[loss_mask]["corredor_h"].value_counts().reset_index()
        d.columns = ["Corredor","Perdas"]
        st.dataframe(d, use_container_width=True, hide_index=True)

    with c4:
        st.markdown("**Perdas — corredor vertical**")
        d = fama_1t[loss_mask]["corredor_v"].value_counts().reset_index()
        d.columns = ["Zona","Perdas"]
        st.dataframe(d, use_container_width=True, hide_index=True)

