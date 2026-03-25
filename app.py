import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime

# ── Logos dos clubes via TheSportsDB — IDs manuais para garantir clube certo ──

# IDs verificados no TheSportsDB para cada clube da Liga Portugal
TSDB_TEAM_IDS = {
    "Famalicão":         134718,
    "Benfica":           134629,
    "FC Porto":          134626,
    "Sporting CP":       134630,
    "Sporting Braga":    134628,
    "Vitória Guimarães": 134633,
    "Moreirense":        134714,
    "Gil Vicente":       134720,
    "Santa Clara":       134721,
    "Rio Ave":           134716,
    "FC Arouca":         134722,
    "Estoril":           134715,
    "Casa Pia":          134723,
    "Tondela":           134719,
    "Nacional":          134717,   # Nacional da Madeira
    "Estrela Amadora":   134724,
    "Alverca":           134725,
    "AVS":               134726,
}

@st.cache_data(ttl=86400, show_spinner=False)
def get_team_logo_by_id(team_id):
    """Busca logo pelo ID do TheSportsDB."""
    try:
        url = f"https://www.thesportsdb.com/api/v1/json/3/lookupteam.php?id={team_id}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("teams"):
            return data["teams"][0].get("strBadge", None)
    except:
        pass
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_team_logo_by_name(team_name):
    """Fallback: busca logo pelo nome."""
    try:
        search = team_name.replace("FC ", "").replace("CD ", "").replace("GD ", "").strip()
        url = f"https://www.thesportsdb.com/api/v1/json/3/searchteams.php?t={requests.utils.quote(search)}"
        r = requests.get(url, timeout=5)
        data = r.json()
        if data.get("teams"):
            return data["teams"][0].get("strBadge", None)
    except:
        pass
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_all_logos(opponents):
    """Busca logos — primeiro por ID manuais, depois por nome como fallback."""
    logos = {}
    all_teams = list(opponents) + ["Famalicão"]
    for team in all_teams:
        team_id = None
        for key, tid in TSDB_TEAM_IDS.items():
            if key.lower() in team.lower() or team.lower() in key.lower():
                team_id = tid
                break
        if team_id:
            logos[team] = get_team_logo_by_id(team_id)
        else:
            logos[team] = get_team_logo_by_name(team)
    return logos



st.set_page_config(page_title="Famalicão — Análise", layout="wide")

# ── Credenciais ────────────────────────────────────────────────────────────
USER = st.secrets["STATSBOMB_USER"]
PASS = st.secrets["STATSBOMB_PASS"]

COMPETITION_ID    = 13
SEASON_ID         = 318
TEAM_NAME         = "Famalicão"
TRANSITION_WINDOW = 10
DEEP_ENTRY_X      = 80
team_key          = "Famalic"
auth              = (USER, PASS)

MESES_PT = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
            7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

# ── Cores oficiais (primária, secundária) ──────────────────────────────────
# Fonte: brandcolorcode.com / teamcolorcodes.com
def lighten_hex(hex_color, factor=0.35):
    """Torna uma cor hex mais clara misturando com branco."""
    hex_color = hex_color.lstrip("#")
    r, g, b = int(hex_color[0:2],16), int(hex_color[2:4],16), int(hex_color[4:6],16)
    r = int(r + (255-r)*factor)
    g = int(g + (255-g)*factor)
    b = int(b + (255-b)*factor)
    return f"#{r:02X}{g:02X}{b:02X}"

# Lista ordenada: mais específico primeiro para evitar matches errados
CLUB_COLORS_LIST = [
    ("Sporting Braga",    "#DC0B15", "#868257"),
    ("Sporting CP",       "#008057", "#F3C242"),
    ("Sporting",          "#008057", "#F3C242"),
    ("Benfica",           "#E83030", "#F27070"),
    ("FC Porto",          "#00428C", "#0080C6"),
    ("Porto",             "#00428C", "#0080C6"),
    ("Vitória Guimarães", "#1C1C1C", "#D4AF37"),
    ("Vitória SC",        "#1C1C1C", "#D4AF37"),
    ("Vitória",           "#1C1C1C", "#D4AF37"),
    ("Moreirense",        "#145F25", "#AF9713"),
    ("Gil Vicente",       "#ED3124", "#084187"),
    ("Santa Clara",       "#D63935", "#305898"),
    ("Rio Ave",           "#00B958", "#F78B1F"),
    ("FC Arouca",         "#FEF405", "#024CAB"),
    ("Arouca",            "#FEF405", "#024CAB"),
    ("Estoril",           "#FEF000", "#0454A3"),
    ("Casa Pia",          "#1A3E6C", "#6A9BC7"),
    ("Tondela",           "#13A040", "#FFED00"),
    ("Nacional",          "#1C1C1C", "#555555"),
    ("Estrela Amadora",   "#8B0000", "#C44040"),
    ("Estrela",           "#8B0000", "#C44040"),
    ("Alverca",           "#003DA5", "#CC0000"),
    ("AVS",               "#CC2222", "#AAAAAA"),
]
DEFAULT_COLORS = ("#888888", "#BBBBBB")

def get_colors(opponent):
    opp_lower = opponent.lower()
    for key, c1, c2 in CLUB_COLORS_LIST:
        if key.lower() in opp_lower:
            return c1, c2
    return DEFAULT_COLORS[0], lighten_hex(DEFAULT_COLORS[0])

# ── Helpers ────────────────────────────────────────────────────────────────

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
    if y is None: return "Desconhecido"
    if y < 26.7:  return "Esquerdo"
    if y < 53.3:  return "Central"
    return "Direito"

def corredor_v(x):
    if x is None: return "Desconhecido"
    if x < 13.3:  return "Zona 1 (GR)"
    if x < 26.7:  return "Zona 2"
    return "Zona 3 (Saída)"

# ── Carregar matches ───────────────────────────────────────────────────────

@st.cache_data(ttl=0, show_spinner="A carregar lista de jogos...")
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
    tm["jogo_num"]   = tm.groupby("opponent").cumcount() + 1
    tm["label_full"] = tm.apply(
        lambda r: r["opponent"] + (f" (J{r['jogo_num']})" if tm[tm["opponent"]==r["opponent"]].shape[0]>1 else ""),
        axis=1
    )
    return tm.sort_values("match_date").reset_index(drop=True)

# ── Carregar eventos ───────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="A carregar eventos...")
def carregar_eventos(match_id):
    ev = pd.json_normalize(get_json(
        f"https://data.statsbombservices.com/api/v8/events/{match_id}"), sep=".")
    ev["time_s"] = ev["timestamp"].apply(ts_to_seconds) + (ev["period"] - 1) * 45 * 60
    ev["loc_x"], ev["loc_y"] = zip(*ev["location"].apply(safe_xy))
    ev["corredor_h"] = ev["loc_y"].apply(corredor_h)
    ev["corredor_v"] = ev["loc_x"].apply(corredor_v)
    return ev

# ── Calcular VAP ───────────────────────────────────────────────────────────

@st.cache_data(ttl=0, show_spinner="A calcular métricas...")
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

        c1, c2 = get_colors(opponent)
        color = c1 if jogo_num == 1 else c2

        results.append({
            "match_id": match_id, "match_date": match_date,
            "opponent": opponent, "jogo_num": jogo_num,
            "mes_ano": mes_ano, "label_full": label_full,
            "color": color, "color_primary": c1, "color_secondary": c2,
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

# ── Plotly: barras empilhadas por adversário ───────────────────────────────

def plotly_stacked_bars(df, col, title, ylabel, logos=None):
    adv_order = df.drop_duplicates("opponent", keep="first")["opponent"].tolist()

    fig = go.Figure()

    # J1 — base de todos os adversários
    x_vals, y_j1, y_j2, colors_j1, colors_j2 = [], [], [], [], []
    hover_j1, hover_j2 = [], []

    for adv in adv_order:
        jogos = df[df["opponent"] == adv].sort_values("jogo_num")
        c1, c2 = get_colors(adv)
        v1 = float(jogos[col].iloc[0])
        x_vals.append(adv)
        y_j1.append(v1)
        colors_j1.append(c1)
        hover_j1.append(f"<b>{jogos['label_full'].iloc[0]}</b><br>{ylabel}: {v1:.2f}<br>{jogos['match_date'].iloc[0]}")

        if len(jogos) > 1:
            v2 = float(jogos[col].iloc[1])
            y_j2.append(v2)
            colors_j2.append(c2)
            hover_j2.append(f"<b>{jogos['label_full'].iloc[1]}</b><br>{ylabel}: {v2:.2f}<br>{jogos['match_date'].iloc[1]}")
        else:
            y_j2.append(0)
            colors_j2.append("rgba(0,0,0,0)")
            hover_j2.append("")

    fig.add_trace(go.Bar(
        x=x_vals, y=y_j1,
        marker_color=colors_j1,
        name="1º Jogo",
        hovertemplate="%{customdata}<extra></extra>",
        customdata=hover_j1,
    ))

    # J2 — empilhado por cima
    visible_j2 = [v for v in y_j2 if v > 0]
    if visible_j2:
        fig.add_trace(go.Bar(
            x=x_vals, y=y_j2,
            marker_color=colors_j2,
            marker_pattern_shape="/",
            name="2º Jogo",
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_j2,
        ))

    fig.update_layout(
        barmode="stack",
        title=dict(text=title, font=dict(size=14, family="Arial")),
        xaxis=dict(title="Adversário", tickangle=-35),
        yaxis=dict(title=ylabel),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=420,
        margin=dict(l=40, r=20, t=60, b=100),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")

    # Adicionar logos por cima das barras — tamanho fixo independente da barra
    if logos:
        max_val = df.groupby("opponent")[col].sum().max()
        logo_size = max_val * 0.10  # tamanho fixo relativo ao eixo Y
        gap      = max_val * 0.03   # espaço entre topo da barra e logo
        for i, adv in enumerate(adv_order):
            logo_url = logos.get(adv)
            if logo_url:
                total = float(df[df["opponent"]==adv][col].sum())
                fig.add_layout_image(dict(
                    source=logo_url + "/tiny",
                    x=i,
                    y=total + gap,
                    xref="x", yref="y",
                    sizex=0.55,
                    sizey=logo_size,
                    xanchor="center",
                    yanchor="bottom",
                    layer="above",
                ))
        # Aumentar o eixo Y para caber os logos
        fig.update_yaxes(range=[0, max_val + logo_size + gap * 4])

    return fig

# ── Plotly: linha cronológica ──────────────────────────────────────────────

def plotly_line_chart(df, title):
    fig = go.Figure()

    # Zonas de risco
    ymax = max(df["VAP"].max() + 3, 25)
    fig.add_hrect(y0=0,  y1=10,   fillcolor="#2ecc71", opacity=0.06, line_width=0)
    fig.add_hrect(y0=10, y1=20,   fillcolor="#e67e22", opacity=0.06, line_width=0)
    fig.add_hrect(y0=20, y1=ymax, fillcolor="#e74c3c", opacity=0.06, line_width=0)
    fig.add_hline(y=10, line_dash="dot", line_color="#2ecc71", line_width=1, opacity=0.6)
    fig.add_hline(y=20, line_dash="dot", line_color="#e67e22", line_width=1, opacity=0.6)

    # Linha VAP
    fig.add_trace(go.Scatter(
        x=df["label_full"], y=df["VAP"],
        mode="lines",
        line=dict(color="#e74c3c", width=2),
        name="VAP",
        showlegend=True,
    ))

    # Pontos coloridos com cor do clube
    fig.add_trace(go.Scatter(
        x=df["label_full"], y=df["VAP"],
        mode="markers",
        marker=dict(color=df["color"].tolist(), size=10,
                    line=dict(color="white", width=1.5)),
        name="VAP (cor do clube)",
        hovertemplate="<b>%{x}</b><br>VAP: %{y:.2f}<br>%{customdata}<extra></extra>",
        customdata=df.apply(lambda r: f"xG: {r['team_match_xg_conceded_after_loss']:.2f} | {r['Risco']}", axis=1),
    ))

    # Média Móvel 3
    fig.add_trace(go.Scatter(
        x=df["label_full"], y=df["Media_Movel_3"],
        mode="lines+markers",
        line=dict(color="#3498db", width=1.5, dash="dash"),
        marker=dict(symbol="square", size=6, color="#3498db"),
        name="Média Móvel 3",
    ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Arial")),
        xaxis=dict(tickangle=-35),
        yaxis=dict(title="VAP", range=[0, ymax]),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=400,
        margin=dict(l=40, r=20, t=60, b=120),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#EEEEEE")
    return fig

# ── Campo com grelha ───────────────────────────────────────────────────────

def draw_pitch_grid(ax):
    ax.set_facecolor("#f0f0e8")
    fc = "#333333"
    ax.set_xlim(0, 60); ax.set_ylim(0, 80)
    ax.set_aspect("equal"); ax.axis("off")
    for y0, y1, c in [(0,26.7,"#e8f4e8"),(26.7,53.3,"#f4f4e8"),(53.3,80,"#e8f4e8")]:
        ax.add_patch(patches.Rectangle((0,y0),60,y1-y0,facecolor=c,alpha=0.35,zorder=0))
    for x0, x1, c in [(0,13.3,"#e8e8f4"),(13.3,26.7,"#f4f4f4"),(26.7,40,"#e8e8f4")]:
        ax.add_patch(patches.Rectangle((x0,0),x1-x0,80,facecolor=c,alpha=0.2,zorder=0))
    ax.add_patch(patches.Rectangle((0,0),60,80,fill=False,edgecolor=fc,linewidth=2,zorder=3))
    ax.add_patch(patches.Rectangle((0,18),18,44,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    ax.add_patch(patches.Rectangle((0,30),6,20,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    ax.axvline(60,color=fc,linewidth=2,zorder=3)
    for y in [26.7,53.3]:
        ax.axhline(y,color="#888888",linewidth=1.2,linestyle="--",alpha=0.7,zorder=2)
    for x in [13.3,26.7]:
        ax.axvline(x,color="#888888",linewidth=1.2,linestyle="--",alpha=0.7,zorder=2)
    ax.axvline(40,color="#cc4444",linewidth=1.5,linestyle="-",alpha=0.6,zorder=2)
    for y, lbl in [(13,"Esq"),(40,"Cen"),(67,"Dir")]:
        ax.text(58,y,lbl,fontsize=8,color="#555",ha="right",va="center",zorder=4)
    for x, lbl in [(6.7,"GR"),(20,"Z2"),(33.3,"Z3")]:
        ax.text(x,78,lbl,fontsize=7,color="#555",ha="center",va="top",zorder=4)
    ax.text(41,78,"Limite\n1ºT",fontsize=6,color="#cc4444",ha="left",va="top",zorder=4)

def heatmap_fig(x_vals, y_vals, title):
    fig, ax = plt.subplots(figsize=(9,6))
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


# ══════════════════════════════════════════════════════════════════════════
# NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════════════

pagina = st.sidebar.radio("📂 Página", ["📊 Vulnerabilidade", "🗺️ Heatmaps"])
team_matches = carregar_matches()

# Carregar logos (cached 24h) — tem de ser depois de team_matches
all_opponents = list(team_matches["opponent"].unique())
logos = get_all_logos(tuple(all_opponents))
fama_logo = logos.get("Famalicão", None)

# ══════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — VULNERABILIDADE
# ══════════════════════════════════════════════════════════════════════════

if pagina == "📊 Vulnerabilidade":
    col_logo, col_title = st.columns([1, 10])
    with col_logo:
        if fama_logo:
            st.image(fama_logo + "/small", width=70)
        else:
            st.markdown("🔴")
    with col_title:
        st.title("Famalicão — Vulnerabilidade após Perda")
    st.caption(f"Liga Portugal 25/26 | Dados StatsBomb | ⚡ Dados atualizados em tempo real")

    df = carregar_vap(team_matches)

    # Filtros
    st.sidebar.header("Filtros")
    meses = ["Todos"] + list(dict.fromkeys(df["mes_ano"].tolist()))
    sel_mes = st.sidebar.selectbox("Mês", meses)
    adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
    sel_adv = st.sidebar.selectbox("Adversário", adversarios)

    df_f = df.copy()
    if sel_mes != "Todos": df_f = df_f[df_f["mes_ano"] == sel_mes]
    if sel_adv != "Todos": df_f = df_f[df_f["opponent"] == sel_adv]

    if df_f.empty:
        st.warning("Nenhum jogo encontrado."); st.stop()

    # Resumo
    st.subheader("Resumo Executivo")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("VAP média",        f"{df_f['VAP'].mean():.2f}")
    c2.metric("Maior VAP",        f"{df_f['VAP'].max():.2f}")
    c3.metric("Menor VAP",        f"{df_f['VAP'].min():.2f}")
    c4.metric("Jogo mais crítico", df_f.loc[df_f["VAP"].idxmax(),"label_full"])
    c5.metric("xG sofrido total", f"{df_f['team_match_xg_conceded_after_loss'].sum():.2f}")

    # Semáforo
    ultimo = df_f.iloc[-1]
    st.subheader("Semáforo de risco do último jogo")
    st.markdown(f"### {ultimo['Risco']}  |  {ultimo['label_full']}  |  VAP = {ultimo['VAP']:.2f}")

    # Linha cronológica
    st.subheader("Linha cronológica da vulnerabilidade")
    st.plotly_chart(plotly_line_chart(df_f.reset_index(drop=True),
                    "VAP por jogo — linha cronológica"), use_container_width=True)

    # Barras VAP
    st.subheader("VAP por adversário")
    st.plotly_chart(plotly_stacked_bars(df_f, "VAP", "VAP por adversário", "VAP", logos=logos),
                    use_container_width=True)

    # Barras xG
    st.subheader("xG sofrido após perda por adversário")
    st.plotly_chart(plotly_stacked_bars(df_f, "team_match_xg_conceded_after_loss",
                    "xG sofrido após perda", "xG", logos=logos), use_container_width=True)

    # Tabela com logos
    st.subheader("Tabela completa")
    df_display = df_f.copy()
    df_display.insert(0, "Logo", df_display["opponent"].apply(
        lambda x: logos.get(x, "") or ""
    ))
    cols = ["Logo"] + [c for c in [
        "match_id","match_date","opponent","jogo_num","mes_ano",
        "team_match_high_press_shots_conceded",
        "team_match_counter_attacking_shots_conceded",
        "team_match_shots_in_clear_conceded",
        "team_match_deep_progressions_conceded",
        "team_match_xg_conceded_after_loss",
        "VAP","Risco","Media_Movel_3"
    ] if c in df_display.columns]
    st.data_editor(
        df_display[cols],
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", width="small")
        },
        use_container_width=True,
        hide_index=True,
        disabled=True,
    )

    # Ranking
    st.subheader("Ranking dos jogos mais vulneráveis")
    ranking = df_f.sort_values("VAP", ascending=False)[
        ["label_full","VAP","team_match_xg_conceded_after_loss","Risco"]
    ].reset_index(drop=True)
    ranking.index += 1
    st.dataframe(ranking, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — HEATMAPS
# ══════════════════════════════════════════════════════════════════════════

elif pagina == "🗺️ Heatmaps":
    st.title("🗺️ Heatmaps — Construção e Perdas")
    st.caption(f"Liga Portugal 25/26 | Dados StatsBomb | ⚡ Dados atualizados em tempo real")

    st.sidebar.header("Filtros")
    meses = ["Todos"] + list(dict.fromkeys(team_matches["mes_ano"].tolist()))
    sel_mes = st.sidebar.selectbox("Mês", meses)
    adversarios = ["Todos"] + sorted(team_matches["opponent"].unique().tolist())
    sel_adv = st.sidebar.selectbox("Adversário", adversarios)

    tm_f = team_matches.copy()
    if sel_mes != "Todos": tm_f = tm_f[tm_f["mes_ano"] == sel_mes]
    if sel_adv != "Todos": tm_f = tm_f[tm_f["opponent"] == sel_adv]

    jogos = tm_f["match_id"].tolist()
    if not jogos:
        st.warning("Nenhum jogo encontrado."); st.stop()

    all_events = []
    with st.spinner(f"A carregar {len(jogos)} jogo(s)..."):
        for mid in jogos:
            all_events.append(carregar_eventos(int(mid)))

    ev_all = pd.concat(all_events, ignore_index=True)
    TYPE_COL = "type.name"; POSS_COL = "possession_team.name"; PASS_OUT = "pass.outcome.name"

    fama    = ev_all[ev_all[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower())].copy()
    fama_1t = fama[fama["loc_x"].apply(lambda x: x <= 60 if x is not None else False)].copy()
    loss_mask = (
        (fama_1t[TYPE_COL].isin({"Miscontrol","Dispossessed"})) |
        ((fama_1t[TYPE_COL]=="Pass") & (fama_1t.get(PASS_OUT,pd.Series(dtype=str))=="Incomplete"))
    )

    st.markdown(f"**{len(jogos)} jogo(s)** | Adversário: {sel_adv} | Mês: {sel_mes}")

    col1, col2 = st.columns(2)
    with col1:
        passes = fama_1t[fama_1t[TYPE_COL]=="Pass"]
        fig1 = heatmap_fig(passes["loc_x"].dropna().tolist(),
                           passes["loc_y"].dropna().tolist(),
                           f"Passes na Construção (n={len(passes)})")
        st.pyplot(fig1); plt.close(fig1)

    with col2:
        perdas = fama_1t[loss_mask]
        fig2 = heatmap_fig(perdas["loc_x"].dropna().tolist(),
                           perdas["loc_y"].dropna().tolist(),
                           f"Perdas de Bola na Construção (n={len(perdas)})")
        st.pyplot(fig2); plt.close(fig2)

    st.subheader("Distribuição por corredor")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown("**Passes — horizontal**")
        d = fama_1t[fama_1t[TYPE_COL]=="Pass"]["corredor_h"].value_counts().reset_index()
        d.columns=["Corredor","Passes"]; st.dataframe(d,use_container_width=True,hide_index=True)
    with c2:
        st.markdown("**Passes — vertical**")
        d = fama_1t[fama_1t[TYPE_COL]=="Pass"]["corredor_v"].value_counts().reset_index()
        d.columns=["Zona","Passes"]; st.dataframe(d,use_container_width=True,hide_index=True)
    with c3:
        st.markdown("**Perdas — horizontal**")
        d = fama_1t[loss_mask]["corredor_h"].value_counts().reset_index()
        d.columns=["Corredor","Perdas"]; st.dataframe(d,use_container_width=True,hide_index=True)
    with c4:
        st.markdown("**Perdas — vertical**")
        d = fama_1t[loss_mask]["corredor_v"].value_counts().reset_index()
        d.columns=["Zona","Perdas"]; st.dataframe(d,use_container_width=True,hide_index=True)
