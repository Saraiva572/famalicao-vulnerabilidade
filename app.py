import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime
import numpy as np

# ── Configurações básicas ─────────────────────────────────────────────────────
st.set_page_config(page_title="Famalicão Analytics", page_icon="⚽", layout="wide")

# ── Credenciais e parâmetros ──────────────────────────────────────────────────
auth = ("tiagofonseca24@hotmail.com", "2csDVEB3")
COMPETITION_ID = 13
SEASON_ID = 318
team_key = "Famalicão"
MESES_PT = {
    1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
    7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"
}

# ── Logos dos clubes — URLs diretas e fiáveis (PNG apenas) ─────────────────────
CLUB_LOGOS = {
    "Famalicão": "https://upload.wikimedia.org/wikipedia/pt/3/3f/FC_Famalic%C3%A3o.png",
    "Benfica": "https://upload.wikimedia.org/wikipedia/pt/0/02/SL_Benfica_logo.png",
    "Porto": "https://upload.wikimedia.org/wikipedia/pt/8/8e/FC_Porto.png",
    "Sporting": "https://upload.wikimedia.org/wikipedia/pt/c/c1/Sporting_CP.png",
    "Braga": "https://upload.wikimedia.org/wikipedia/pt/5/5f/SC_Braga.png",
    "Vitória": "https://upload.wikimedia.org/wikipedia/pt/8/88/Vit%C3%B3ria_Sport_Clube.png",
    "Moreirense": "https://upload.wikimedia.org/wikipedia/pt/9/94/Moreirense_FC.png",
    "Gil Vicente": "https://upload.wikimedia.org/wikipedia/pt/2/2a/Gil_Vicente_FC_logo.png",
    "Santa Clara": "https://upload.wikimedia.org/wikipedia/pt/0/0e/CD_Santa_Clara.png",
    "Rio Ave": "https://upload.wikimedia.org/wikipedia/pt/7/7a/Rio_Ave_Futebol_Clube.png",
    "Arouca": "https://upload.wikimedia.org/wikipedia/pt/0/0e/FC_Arouca_logo.png",
    "Estoril": "https://upload.wikimedia.org/wikipedia/pt/f/f7/GD_Estoril_Praia.png",
    "Casa Pia": "https://upload.wikimedia.org/wikipedia/pt/a/a8/Casa_Pia_AC.png",
    "Tondela": "https://upload.wikimedia.org/wikipedia/pt/8/86/CD_Tondela.png",
    "Nacional": "https://upload.wikimedia.org/wikipedia/pt/0/01/CD_Nacional.png",
    "Estrela Amadora": "https://upload.wikimedia.org/wikipedia/pt/6/6d/CF_Estrela_da_Amadora.png",
    "Estrela": "https://upload.wikimedia.org/wikipedia/pt/6/6d/CF_Estrela_da_Amadora.png",
    "Alverca": "https://upload.wikimedia.org/wikipedia/pt/9/90/FC_Alverca.png",
    "AVS": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/AVS_logo.svg/512px-AVS_logo.svg.png",
    "Boavista": "https://upload.wikimedia.org/wikipedia/pt/8/8b/Boavista_F.C..png",
    "Farense": "https://upload.wikimedia.org/wikipedia/pt/3/36/SC_Farense.png",
}

def get_logo_url(team_name):
    if team_name is None:
        return None
    for key, url in CLUB_LOGOS.items():
        if key.lower() in team_name.lower():
            return url
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def get_all_logos(opponents):
    return {opp: get_logo_url(opp) for opp in opponents}

def lighten_hex(hex_color, factor=0.4):
    hex_color = hex_color.lstrip("#")
    r,g,b = int(hex_color[0:2],16),int(hex_color[2:4],16),int(hex_color[4:6],16)
    r=int(r+(255-r)*factor); g=int(g+(255-g)*factor); b=int(b+(255-b)*factor)
    return f"#{r:02x}{g:02x}{b:02x}"

CLUB_COLORS_LIST = [
    ("Famalicão",          "#004F9E", "#87CEEB"),
    ("Benfica",            "#FF0000", "#FFFFFF"),
    ("Porto",              "#004F9E", "#0066B2"),
    ("Sporting",           "#00843D", "#B3D57C"),
    ("Braga",              "#D71920", "#F4A9A9"),
    ("Vitória",            "#1C1C1C", "#D4AF37"),
    ("Moreirense",         "#145F25", "#AF9713"),
    ("Gil Vicente",        "#ED3124", "#084187"),
    ("Santa Clara",        "#D63935", "#305898"),
    ("Rio Ave",            "#00B958", "#F78B1F"),
    ("FC Arouca",          "#FEF405", "#024CAB"),
    ("Arouca",             "#FEF405", "#024CAB"),
    ("Estoril",            "#FEF000", "#0454A3"),
    ("Casa Pia",           "#1A3E6C", "#6A9BC7"),
    ("Tondela",            "#13A040", "#FFED00"),
    ("Nacional",           "#1C1C1C", "#555555"),
    ("Estrela Amadora",    "#8B0000", "#C44040"),
    ("Estrela",            "#8B0000", "#C44040"),
    ("Alverca",            "#003DA5", "#CC0000"),
    ("AVS",                "#CC2222", "#AAAAAA"),
    ("Boavista",           "#1C1C1C", "#FFFFFF"),
    ("Farense",            "#FFFFFF", "#000000"),
]
DEFAULT_COLORS = ("#888888", "#BBBBBB")

def get_colors(opponent):
    if opponent is None:
        return DEFAULT_COLORS[0], lighten_hex(DEFAULT_COLORS[0])
    opp_lower = opponent.lower()
    for key, c1, c2 in CLUB_COLORS_LIST:
        if key.lower() in opp_lower:
            return c1, c2
    return DEFAULT_COLORS[0], lighten_hex(DEFAULT_COLORS[0])

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
    if y is None: return "Desconhecido"
    if y < 26.7:  return "Esquerdo"
    if y < 53.3:  return "Central"
    return "Direito"

def corredor_v(x):
    if x is None: return "Desconhecido"
    if x < 13.3:  return "Zona 1 (GR)"
    if x < 26.7:  return "Zona 2"
    return "Zona 3 (Saída)"

# ── Carregar matches ───────────────────────────────────────────────────────────
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

# ── Carregar eventos ───────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="A carregar eventos...")
def carregar_eventos(match_id):
    ev = pd.json_normalize(get_json(
        f"https://data.statsbombservices.com/api/v8/events/{match_id}"), sep=".")
    ev["time_s"] = ev["timestamp"].apply(ts_to_seconds) + (ev["period"] - 1) * 45 * 60
    ev["loc_x"], ev["loc_y"] = zip(*ev["location"].apply(safe_xy))
    ev["corredor_h"] = ev["loc_y"].apply(corredor_h)
    ev["corredor_v"] = ev["loc_x"].apply(corredor_v)
    return ev

# ── Carregar métricas do CSV (GitHub) — Vulnerabilidade ────────────────────────
CSV_URL = "https://raw.githubusercontent.com/Saraiva572/famalicao-vulnerabilidade/main/vulnerabilidade_perda_real_novasmetricas.csv"

@st.cache_data(ttl=0, show_spinner="A carregar métricas...")
def carregar_vap(team_matches):
    try:
        df_csv = pd.read_csv(CSV_URL, sep=";")
    except:
        df_csv = pd.read_csv(CSV_URL)
    if "match_id" in df_csv.columns:
        team_matches = team_matches.merge(df_csv, on="match_id", how="left", suffixes=("", "_csv"))
    else:
        team_matches = team_matches.copy()
        for col in ["team_match_high_press_shots_conceded", "team_match_counter_attacking_shots_conceded",
                    "team_match_shots_in_clear_conceded", "team_match_deep_progressions_conceded",
                    "team_match_xg_conceded_after_loss"]:
            team_matches[col] = 0.0
    for c in ["team_match_high_press_shots_conceded","team_match_counter_attacking_shots_conceded",
              "team_match_shots_in_clear_conceded","team_match_deep_progressions_conceded",
              "team_match_xg_conceded_after_loss"]:
        if c not in team_matches.columns: team_matches[c] = 0.0
        team_matches[c] = pd.to_numeric(team_matches[c], errors="coerce").fillna(0.0)
    team_matches["VAP"] = (
        4*team_matches["team_match_high_press_shots_conceded"] +
        3*team_matches["team_match_counter_attacking_shots_conceded"] +
        2*team_matches["team_match_shots_in_clear_conceded"] +
        0.1*team_matches["team_match_deep_progressions_conceded"]
    )
    team_matches["Risco"] = team_matches["VAP"].apply(classificar_risco)
    team_matches["Media_Movel_3"] = team_matches["VAP"].rolling(3, min_periods=1).mean()
    team_matches["color"] = team_matches["opponent"].apply(lambda o: get_colors(o)[0])
    return team_matches

# ══════════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE ANÁLISE DE CONSTRUÇÃO (baseadas no notebook)
# ══════════════════════════════════════════════════════════════════════════════

VALID_START_POSITIONS = ["Goalkeeper", "Right Center Back", "Left Center Back"]

def extract_end_location(row):
    """Extrai end_x e end_y de várias colunas possíveis - VERSÃO CORRIGIDA"""
    # Para Pass - verificar se a coluna existe E tem valor válido
    if "pass.end_location" in row.index:
        loc = row["pass.end_location"]
        if isinstance(loc, list) and len(loc) >= 2:
            return loc[0], loc[1]
    
    # Para Carry
    if "carry.end_location" in row.index:
        loc = row["carry.end_location"]
        if isinstance(loc, list) and len(loc) >= 2:
            return loc[0], loc[1]
    
    # Fallback para location
    if "location" in row.index:
        loc = row["location"]
        if isinstance(loc, list) and len(loc) >= 2:
            return loc[0], loc[1]
    
    return None, None

def analyze_build_up_possessions(events_df, team_name="Famalicão"):
    """
    Analisa posses de 1ª fase de construção do Famalicão.
    Retorna summary e actions DataFrames.
    """
    # Filtrar eventos do Famalicão
    if "team.name" not in events_df.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    fam_events = events_df[events_df["team.name"].str.contains(team_name, case=False, na=False)].copy()
    
    if fam_events.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    sequence_summary_list = []
    sequence_actions_list = []
    
    # Agrupar por match_id e possession
    if "match_id" not in fam_events.columns:
        fam_events["match_id"] = 0
    
    # Verificar se coluna possession existe
    if "possession" not in fam_events.columns:
        return pd.DataFrame(), pd.DataFrame()
    
    grouped = fam_events.groupby(["match_id", "possession"])
    
    for (match_id, poss_id), poss_df in grouped:
        try:
            poss_df = poss_df.sort_values(by=["period", "index"]).reset_index(drop=True)
            
            # Encontrar primeiro Pass na posição válida
            if "type.name" not in poss_df.columns:
                continue
            
            passes = poss_df[poss_df["type.name"] == "Pass"]
            
            if "position.name" not in passes.columns:
                continue
            
            valid_first = passes[passes["position.name"].isin(VALID_START_POSITIONS)]
            
            if valid_first.empty:
                continue
            
            first_pass = valid_first.iloc[0]
            first_idx = first_pass.name
            
            # Filtrar sequência a partir do primeiro passe
            sequence = poss_df.loc[first_idx:].copy()
            sequence = sequence[sequence["type.name"].isin(["Pass", "Carry"])]
            
            if len(sequence) < 3:
                continue
            
            # Contar jogadores distintos
            if "player.name" not in sequence.columns:
                continue
            
            n_players = sequence["player.name"].dropna().nunique()
            if n_players < 3:
                continue
            
            # Calcular end_x para cada ação
            sequence = sequence.reset_index(drop=True)
            sequence["action_number"] = range(1, len(sequence) + 1)
            
            # CORREÇÃO: usar apply com result_type para evitar problemas
            end_coords = sequence.apply(extract_end_location, axis=1, result_type='expand')
            if end_coords.shape[1] >= 2:
                sequence["end_x"] = end_coords[0]
                sequence["end_y"] = end_coords[1]
            else:
                sequence["end_x"] = None
                sequence["end_y"] = None
            
            # Validar sucesso
            validated_partial = False
            validated_total = False
            partial_start = partial_end = None
            total_start = total_end = None
            
            for i in range(len(sequence) - 2):
                curr_x = sequence.loc[i, "end_x"]
                next1_x = sequence.loc[i + 1, "end_x"] if i + 1 < len(sequence) else None
                next2_x = sequence.loc[i + 2, "end_x"] if i + 2 < len(sequence) else None
                
                if pd.notna(curr_x) and pd.notna(next1_x) and pd.notna(next2_x):
                    # Sucesso parcial: x > 40
                    if not validated_partial and curr_x > 40 and next1_x > 40 and next2_x > 40:
                        validated_partial = True
                        partial_start = int(sequence.loc[i, "action_number"])
                        partial_end = int(sequence.loc[i + 2, "action_number"])
                    
                    # Sucesso total: x > 60
                    if curr_x > 60 and next1_x > 60 and next2_x > 60:
                        validated_total = True
                        total_start = int(sequence.loc[i, "action_number"])
                        total_end = int(sequence.loc[i + 2, "action_number"])
                        break
            
            # Determinar outcome
            if validated_total:
                outcome = "success_total"
            elif validated_partial:
                outcome = "success_partial"
            else:
                outcome = "unsuccessful"
            
            # Start location
            start_loc = first_pass["location"] if "location" in first_pass.index else [None, None]
            start_x = start_loc[0] if isinstance(start_loc, list) else None
            start_y = start_loc[1] if isinstance(start_loc, list) and len(start_loc) > 1 else None
            
            # End location do primeiro passe
            first_end_x, first_end_y = extract_end_location(first_pass)
            
            sequence_summary_list.append({
                "match_id": match_id,
                "possession": poss_id,
                "first_player": first_pass["player.name"] if "player.name" in first_pass.index else "Desconhecido",
                "first_position": first_pass["position.name"] if "position.name" in first_pass.index else "Desconhecido",
                "first_start_x": start_x,
                "first_start_y": start_y,
                "first_end_x": first_end_x,
                "n_actions": len(sequence),
                "n_players": n_players,
                "validated_partial": validated_partial,
                "validated_total": validated_total,
                "outcome": outcome,
            })
            
            # Guardar ações
            for _, row in sequence.iterrows():
                sequence_actions_list.append({
                    "match_id": match_id,
                    "possession": poss_id,
                    "action_number": row["action_number"],
                    "type": row["type.name"] if "type.name" in row.index else "",
                    "player": row["player.name"] if "player.name" in row.index else "",
                    "position": row["position.name"] if "position.name" in row.index else "",
                    "end_x": row["end_x"],
                    "end_y": row["end_y"],
                    "outcome": outcome,
                })
        except Exception as e:
            # Log silencioso e continua
            continue
    
    summary_df = pd.DataFrame(sequence_summary_list)
    actions_df = pd.DataFrame(sequence_actions_list)
    
    return summary_df, actions_df

def calculate_build_up_metrics(summary_df, team_matches):
    """Calcula métricas agregadas por jogo"""
    if summary_df.empty:
        return pd.DataFrame()
    
    # Agregar por match_id
    match_agg = summary_df.groupby("match_id").agg({
        "possession": "count",
        "validated_partial": "sum",
        "validated_total": "sum",
        "n_actions": "mean",
        "n_players": "mean",
    }).reset_index()
    
    match_agg.columns = ["match_id", "n_build_ups", "n_partial", "n_total", "avg_actions", "avg_players"]
    
    # Calcular taxas de sucesso
    match_agg["n_unsuccessful"] = match_agg["n_build_ups"] - match_agg["n_partial"] - match_agg["n_total"]
    match_agg["success_rate_total"] = (match_agg["n_total"] / match_agg["n_build_ups"] * 100).round(1)
    match_agg["success_rate_partial"] = (match_agg["n_partial"] / match_agg["n_build_ups"] * 100).round(1)
    match_agg["success_rate_any"] = ((match_agg["n_total"] + match_agg["n_partial"]) / match_agg["n_build_ups"] * 100).round(1)
    
    # Merge com team_matches para obter opponent e label
    if "match_id" in team_matches.columns:
        match_agg = match_agg.merge(
            team_matches[["match_id", "opponent", "label_full", "match_date", "mes_ano"]],
            on="match_id",
            how="left"
        )
    
    return match_agg

# ── Gráficos de barras ────────────────────────────────────────────────────────
def plotly_stacked_bar(df, col_j1, col_j2, title, ylabel):
    df_sorted = df.sort_values("match_date")

    is_j2 = df_sorted["label_full"].str.contains(r"\(J2\)", regex=True, na=False)
    j1_df = df_sorted[~is_j2]
    j2_df = df_sorted[is_j2]

    fig = go.Figure()

    # Barras J1 — cor sólida do clube
    fig.add_trace(go.Bar(
        x=j1_df["label_full"],
        y=j1_df[col_j1],
        marker=dict(
            color=[get_colors(o)[0] for o in j1_df["opponent"]],
            line=dict(color="white", width=0.8),
        ),
        name="1º Jogo",
        hovertemplate="<b>%{x}</b><br>" + ylabel + ": %{y:.3f}<extra></extra>",
    ))

    # Barras J2 — cor secundária + hachura diagonal
    if not j2_df.empty:
        fig.add_trace(go.Bar(
            x=j2_df["label_full"],
            y=j2_df[col_j1],
            marker=dict(
                color=[get_colors(o)[1] for o in j2_df["opponent"]],
                pattern=dict(shape="/", size=8, solidity=0.45),
                line=dict(color="white", width=0.8),
            ),
            name="2º Jogo",
            hovertemplate="<b>%{x}</b><br>" + ylabel + ": %{y:.3f}<extra></extra>",
        ))

    fig.update_layout(
        barmode="overlay",
        title=dict(text=title, font=dict(size=15, family="Arial", color="#1a1a2e")),
        xaxis=dict(
            title="Adversário",
            tickangle=-45,
            tickfont=dict(size=10),
            showgrid=False,
        ),
        yaxis=dict(
            title=ylabel,
            tickfont=dict(size=11),
            showgrid=True,
            gridcolor="#E5E5E5",
            zeroline=True,
            zerolinecolor="#cccccc",
        ),
        plot_bgcolor="white",
        paper_bgcolor="#fafafa",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#ddd", borderwidth=1,
            font=dict(size=12),
        ),
        height=500,
        margin=dict(l=55, r=20, t=75, b=140),
        hovermode="x unified",
    )
    return fig

# ── Plotly: linha cronológica ──────────────────────────────────────────────────
def plotly_line_chart(df, y_col, title, ylabel):
    fig = go.Figure()
    ymax = max(df[y_col].max() + 3, 25)
    fig.add_hrect(y0=0,  y1=10,   fillcolor="#2ecc71", opacity=0.14, line_width=0)
    fig.add_hrect(y0=10, y1=20,   fillcolor="#e67e22", opacity=0.14, line_width=0)
    fig.add_hrect(y0=20, y1=ymax, fillcolor="#e74c3c", opacity=0.14, line_width=0)
    fig.add_hline(y=10, line_dash="dot", line_color="#27ae60", line_width=1.5, opacity=0.8,
                  annotation_text="Baixo/Médio", annotation_position="right",
                  annotation_font=dict(size=10, color="#27ae60"))
    fig.add_hline(y=20, line_dash="dot", line_color="#e67e22", line_width=1.5, opacity=0.8,
                  annotation_text="Médio/Alto", annotation_position="right",
                  annotation_font=dict(size=10, color="#e67e22"))

    fig.add_trace(go.Scatter(
        x=df["label_full"], y=df[y_col],
        mode="lines+markers",
        line=dict(color="#e74c3c", width=2),
        marker=dict(color=df["color"].tolist() if "color" in df.columns else "#e74c3c", 
                   size=10, line=dict(color="white", width=1.5)),
        name=ylabel,
    ))

    if "Media_Movel_3" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["label_full"], y=df["Media_Movel_3"],
            mode="lines+markers",
            line=dict(color="#3498db", width=1.5, dash="dash"),
            marker=dict(symbol="square", size=6, color="#3498db"),
            name="Média Móvel 3",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Arial", color="#1a1a2e")),
        xaxis=dict(tickangle=-45, tickfont=dict(size=10), showgrid=False),
        yaxis=dict(title=ylabel, range=[0, ymax], tickfont=dict(size=11)),
        plot_bgcolor="white",
        paper_bgcolor="#fafafa",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#ddd", borderwidth=1,
        ),
        height=430,
        margin=dict(l=55, r=80, t=70, b=130),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#E5E5E5", zeroline=True, zerolinecolor="#ccc")
    return fig

# ── Campo com grelha ───────────────────────────────────────────────────────────
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

def draw_full_pitch(ax):
    """Desenha campo completo (120x80) para visualizar progressão"""
    ax.set_facecolor("#f0f0e8")
    fc = "#333333"
    ax.set_xlim(0, 120); ax.set_ylim(0, 80)
    ax.set_aspect("equal"); ax.axis("off")
    
    # Zonas de terços
    for x0, x1, c in [(0,40,"#d4edda"),(40,80,"#fff3cd"),(80,120,"#f8d7da")]:
        ax.add_patch(patches.Rectangle((x0,0),x1-x0,80,facecolor=c,alpha=0.3,zorder=0))
    
    # Linhas do campo
    ax.add_patch(patches.Rectangle((0,0),120,80,fill=False,edgecolor=fc,linewidth=2,zorder=3))
    ax.axvline(60,color=fc,linewidth=1.5,zorder=3)  # Meio-campo
    
    # Grandes áreas
    ax.add_patch(patches.Rectangle((0,18),18,44,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    ax.add_patch(patches.Rectangle((102,18),18,44,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    
    # Pequenas áreas
    ax.add_patch(patches.Rectangle((0,30),6,20,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    ax.add_patch(patches.Rectangle((114,30),6,20,fill=False,edgecolor=fc,linewidth=1.5,zorder=3))
    
    # Linhas de referência (40 e 60)
    ax.axvline(40,color="#28a745",linewidth=2,linestyle="--",alpha=0.7,zorder=2)
    ax.axvline(60,color="#fd7e14",linewidth=2,linestyle="--",alpha=0.7,zorder=2)
    
    # Labels
    ax.text(20, -3, "1º Terço (Construção)", fontsize=9, ha="center", color="#155724", fontweight="bold")
    ax.text(60, -3, "2º Terço", fontsize=9, ha="center", color="#856404", fontweight="bold")
    ax.text(100, -3, "3º Terço (Finalização)", fontsize=9, ha="center", color="#721c24", fontweight="bold")
    ax.text(40, 82, "x=40", fontsize=8, ha="center", color="#28a745")
    ax.text(60, 82, "x=60", fontsize=8, ha="center", color="#fd7e14")

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

def build_up_progression_chart(actions_df, outcome_filter=None):
    """Gráfico de progressão das sequências de construção"""
    if actions_df.empty:
        return None
    
    df = actions_df.copy()
    if outcome_filter:
        df = df[df["outcome"] == outcome_filter]
    
    if df.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 6))
    draw_full_pitch(ax)
    
    colors = {"success_total": "#28a745", "success_partial": "#fd7e14", "unsuccessful": "#dc3545"}
    
    # Plotar cada sequência como linha
    for (mid, poss), group in df.groupby(["match_id", "possession"]):
        group = group.sort_values("action_number")
        xs = group["end_x"].dropna().tolist()
        ys = group["end_y"].dropna().tolist()
        outcome = group["outcome"].iloc[0]
        color = colors.get(outcome, "#888888")
        
        if len(xs) >= 2:
            ax.plot(xs, ys, color=color, alpha=0.3, linewidth=1, zorder=1)
            ax.scatter(xs[-1], ys[-1], color=color, s=30, alpha=0.5, zorder=2)
    
    ax.set_title("Progressão das Sequências de Construção", fontsize=12, fontweight="bold", pad=15)
    
    # Legenda
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color="#28a745", linewidth=2, label="Sucesso Total (x>60)"),
        Line2D([0], [0], color="#fd7e14", linewidth=2, label="Sucesso Parcial (x>40)"),
        Line2D([0], [0], color="#dc3545", linewidth=2, label="Sem Sucesso"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=8)
    
    fig.tight_layout()
    return fig

# ── Header estilizado ─────────────────────────────────────────────────────────
def render_header(title, subtitle="Liga Portugal 25/26 · Dados StatsBomb · Atualizado em tempo real"):
    logo_url = CLUB_LOGOS.get("Famalicão", "")
    st.markdown(f"""
    <div style="display:flex; align-items:center; background:linear-gradient(90deg, #003d7a 0%, #0066cc 100%);
                padding:14px 22px; border-radius:10px; margin-bottom:18px; gap:18px;
                box-shadow:0 3px 10px rgba(0,0,0,0.18);">
        <img src="{logo_url}" width="62"
             style="object-fit:contain; filter:drop-shadow(0 2px 5px rgba(0,0,0,0.35)); flex-shrink:0;">
        <div>
            <div style="color:white; font-size:1.55rem; font-weight:700; letter-spacing:-0.3px;
                        font-family:Arial,sans-serif; line-height:1.2;">{title}</div>
            <div style="color:#b3d4ff; font-size:0.78rem; margin-top:4px;
                        font-family:Arial,sans-serif;">{subtitle}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════════════════

pagina = st.sidebar.radio("📂 Página", ["📊 Vulnerabilidade", "🏗️ Construção", "🗺️ Heatmaps"])
team_matches = carregar_matches()

# Carregar logos
all_opponents = list(team_matches["opponent"].unique())
logos = get_all_logos(tuple(all_opponents))
fama_logo = CLUB_LOGOS.get("Famalicão")

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 1 — VULNERABILIDADE
# ══════════════════════════════════════════════════════════════════════════════

if pagina == "📊 Vulnerabilidade":
    render_header("Famalicão — Vulnerabilidade após Perda")

    df = carregar_vap(team_matches)

    for col, default in [
        ("exposicao_defensiva_pct", 0.0),
        ("counterpress_efficiency_pct", 0.0),
        ("transition_risk_index", 0.0),
        ("n_losses", 0),
    ]:
        if col not in df.columns:
            df[col] = default

    df["TRI_MM3"] = df["transition_risk_index"].rolling(3, min_periods=1).mean()

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

    # Resumo Executivo
    st.subheader("Resumo Executivo")
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("TRI médio", f"{df_f['transition_risk_index'].mean():.1f}", help="Transition Risk Index médio")
    c2.metric("xG sofrido total", f"{df_f['team_match_xg_conceded_after_loss'].sum():.2f}")
    c3.metric("Exposição Defensiva média", f"{df_f['exposicao_defensiva_pct'].mean():.1f}%")
    c4.metric("Counterpress médio", f"{df_f['counterpress_efficiency_pct'].mean():.1f}%")
    c5.metric("Jogo mais crítico (TRI)", df_f.loc[df_f["transition_risk_index"].idxmax(), "label_full"])

    # Semáforo
    ultimo = df_f.iloc[-1]
    tri_ult = ultimo["transition_risk_index"]
    if tri_ult < 10:   semaforo = "🟢 Baixo Risco"
    elif tri_ult < 20: semaforo = "🟡 Risco Médio"
    else:              semaforo = "🔴 Alto Risco"
    st.subheader("Semáforo de risco do último jogo")
    st.markdown(f"### {semaforo}  |  {ultimo['label_full']}  |  TRI = {tri_ult:.1f}")

    # Notas explicativas
    with st.expander("ℹ️ O que significa cada métrica?", expanded=False):
        st.markdown("""
**Transition Risk Index (TRI)** — Índice composto de risco (0-100) que combina:
- xG sofrido após perda (40%), Remates por perda (25%), Entradas no último terço (20%), Progressão adversária (15%)

**xG sofrido após perda** — Expected Goals dos remates adversários nos 10s após cada perda no 1º terço.

**Exposição Defensiva %** — Percentagem de perdas que geraram remate adversário em 10 segundos.

**Counterpress Efficiency %** — Percentagem de perdas recuperadas em 5 segundos (counterpress bem-sucedido).
""")

    # Gráfico TRI ao longo do tempo
    st.subheader("Evolução do Transition Risk Index (TRI)")
    df_f["Media_Movel_3"] = df_f["transition_risk_index"].rolling(3, min_periods=1).mean()
    fig_tri = plotly_line_chart(df_f, "transition_risk_index", "TRI por Jogo (com média móvel 3)", "TRI")
    st.plotly_chart(fig_tri, use_container_width=True)

    # Gráficos de barras
    st.subheader("Métricas por Adversário")
    col1, col2 = st.columns(2)
    with col1:
        fig1 = plotly_stacked_bar(df_f, "team_match_xg_conceded_after_loss", "team_match_xg_conceded_after_loss",
                                  "xG Sofrido após Perda", "xG")
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = plotly_stacked_bar(df_f, "exposicao_defensiva_pct", "exposicao_defensiva_pct",
                                  "Exposição Defensiva %", "%")
        st.plotly_chart(fig2, use_container_width=True)

    # VAP histórico (expander)
    with st.expander("📈 VAP (Índice Histórico)", expanded=False):
        fig_vap = plotly_line_chart(df_f, "VAP", "VAP por Jogo", "VAP")
        st.plotly_chart(fig_vap, use_container_width=True)

    # Tabela
    st.subheader("Dados Detalhados")
    df_display = df_f.copy()
    df_display["Logo"] = df_display["opponent"].apply(lambda o: logos.get(o))
    cols = ["Logo","label_full","n_losses","team_match_xg_conceded_after_loss",
            "exposicao_defensiva_pct","counterpress_efficiency_pct","transition_risk_index","VAP"]
    cols = [c for c in cols if c in df_display.columns]
    st.data_editor(
        df_display[cols],
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", width="small"),
            "label_full": st.column_config.TextColumn("Jogo"),
            "n_losses": st.column_config.NumberColumn("Perdas", format="%d"),
            "team_match_xg_conceded_after_loss": st.column_config.NumberColumn("xG sofrido", format="%.3f"),
            "exposicao_defensiva_pct": st.column_config.NumberColumn("Exp. Def. %", format="%.1f%%"),
            "counterpress_efficiency_pct": st.column_config.NumberColumn("Counterpress %", format="%.1f%%"),
            "transition_risk_index": st.column_config.NumberColumn("TRI", format="%.1f"),
            "VAP": st.column_config.NumberColumn("VAP", format="%.1f"),
        },
        use_container_width=True, hide_index=True, disabled=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 2 — CONSTRUÇÃO
# ══════════════════════════════════════════════════════════════════════════════

elif pagina == "🏗️ Construção":
    render_header("Famalicão — Análise da 1ª Fase de Construção")

    # Filtros
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

    # Carregar eventos
    all_events = []
    with st.spinner(f"A analisar {len(jogos)} jogo(s)..."):
        for mid in jogos:
            ev = carregar_eventos(int(mid))
            ev["match_id"] = mid
            all_events.append(ev)

    ev_all = pd.concat(all_events, ignore_index=True)

    # Analisar construção
    with st.spinner("A processar sequências de construção..."):
        summary_df, actions_df = analyze_build_up_possessions(ev_all, team_key)

    if summary_df.empty:
        st.warning("Não foram encontradas sequências de construção válidas.")
        st.stop()

    # Calcular métricas por jogo
    metrics_df = calculate_build_up_metrics(summary_df, tm_f)

    # ── Resumo Executivo ───────────────────────────────────────────────────────
    st.subheader("📊 Resumo Executivo")
    
    total_builds = len(summary_df)
    total_success = len(summary_df[summary_df["outcome"] == "success_total"])
    partial_success = len(summary_df[summary_df["outcome"] == "success_partial"])
    unsuccessful = len(summary_df[summary_df["outcome"] == "unsuccessful"])
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total de Construções", total_builds)
    c2.metric("Sucesso Total", f"{total_success} ({total_success/total_builds*100:.1f}%)", 
              help="Atingiu x > 60 em 3 ações consecutivas")
    c3.metric("Sucesso Parcial", f"{partial_success} ({partial_success/total_builds*100:.1f}%)",
              help="Atingiu x > 40 mas não x > 60")
    c4.metric("Sem Sucesso", f"{unsuccessful} ({unsuccessful/total_builds*100:.1f}%)",
              help="Nunca atingiu x > 40")
    c5.metric("Média de Ações/Sequência", f"{summary_df['n_actions'].mean():.1f}")

    # ── Semáforo da última jornada ─────────────────────────────────────────────
    if not metrics_df.empty and "match_date" in metrics_df.columns:
        ultimo_jogo = metrics_df.sort_values("match_date").iloc[-1]
        taxa_sucesso = ultimo_jogo.get("success_rate_any", 0)
        
        if taxa_sucesso >= 60:
            semaforo = "🟢 Construção Eficaz"
        elif taxa_sucesso >= 40:
            semaforo = "🟡 Construção Moderada"
        else:
            semaforo = "🔴 Construção Ineficaz"
        
        st.subheader("Semáforo do último jogo")
        st.markdown(f"### {semaforo} | {ultimo_jogo.get('label_full', 'N/A')} | Taxa de Sucesso: {taxa_sucesso:.1f}%")

    # ── Notas explicativas ─────────────────────────────────────────────────────
    with st.expander("ℹ️ O que significa cada métrica?", expanded=False):
        st.markdown("""
**1ª Fase de Construção** — Sequências de posse que:
- Começam com passe do GK, Central Direito ou Central Esquerdo
- Envolvem pelo menos 3 jogadores distintos
- Incluem apenas passes e conduções

**Outcomes:**
- 🟢 **Sucesso Total**: 3 ações consecutivas terminam com x > 60 (passou o meio-campo)
- 🟡 **Sucesso Parcial**: 3 ações consecutivas terminam com x > 40 (saiu da zona de pressão)
- 🔴 **Sem Sucesso**: Nunca atingiu x > 40

**Taxa de Sucesso** — Percentagem de sequências que atingiram pelo menos sucesso parcial (x > 40).
""")

    # ── Distribuição de Outcomes (Donut Chart) ─────────────────────────────────
    st.subheader("📈 Distribuição dos Outcomes")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # Donut chart
        labels = ["Sucesso Total", "Sucesso Parcial", "Sem Sucesso"]
        values = [total_success, partial_success, unsuccessful]
        colors = ["#28a745", "#fd7e14", "#dc3545"]
        
        fig_donut = go.Figure(data=[go.Pie(
            labels=labels, values=values,
            hole=0.5,
            marker_colors=colors,
            textinfo="label+percent",
            textposition="outside",
        )])
        fig_donut.update_layout(
            showlegend=False,
            height=350,
            margin=dict(l=20, r=20, t=30, b=20),
            annotations=[dict(text=f"{total_builds}", x=0.5, y=0.5, font_size=28, showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    
    with col2:
        # Evolução por jogo
        if not metrics_df.empty and "match_date" in metrics_df.columns:
            metrics_df = metrics_df.sort_values("match_date")
            
            fig_evol = go.Figure()
            fig_evol.add_trace(go.Bar(
                x=metrics_df["label_full"],
                y=metrics_df["n_total"],
                name="Sucesso Total",
                marker_color="#28a745",
            ))
            fig_evol.add_trace(go.Bar(
                x=metrics_df["label_full"],
                y=metrics_df["n_partial"],
                name="Sucesso Parcial",
                marker_color="#fd7e14",
            ))
            fig_evol.add_trace(go.Bar(
                x=metrics_df["label_full"],
                y=metrics_df["n_unsuccessful"],
                name="Sem Sucesso",
                marker_color="#dc3545",
            ))
            
            fig_evol.update_layout(
                barmode="stack",
                title="Outcomes por Jogo",
                xaxis_tickangle=-35,
                height=350,
                legend=dict(orientation="h", y=1.1),
                plot_bgcolor="white",
            )
            st.plotly_chart(fig_evol, use_container_width=True)

    # ── Taxa de Sucesso ao Longo do Tempo ──────────────────────────────────────
    st.subheader("📉 Taxa de Sucesso por Jogo")
    
    if not metrics_df.empty:
        metrics_df["color"] = metrics_df["opponent"].apply(lambda o: get_colors(o)[0])
        metrics_df["Media_Movel_3"] = metrics_df["success_rate_any"].rolling(3, min_periods=1).mean()
        
        fig_taxa = go.Figure()
        
        # Zonas de referência
        fig_taxa.add_hrect(y0=60, y1=100, fillcolor="#28a745", opacity=0.18, line_width=0)
        fig_taxa.add_hrect(y0=40, y1=60, fillcolor="#fd7e14", opacity=0.18, line_width=0)
        fig_taxa.add_hrect(y0=0, y1=40, fillcolor="#dc3545", opacity=0.18, line_width=0)
        fig_taxa.add_hline(y=60, line_dash="dot", line_color="#28a745", line_width=1.5, opacity=0.8,
                           annotation_text="Eficaz (60%)", annotation_position="right",
                           annotation_font=dict(size=10, color="#28a745"))
        fig_taxa.add_hline(y=40, line_dash="dot", line_color="#dc3545", line_width=1.5, opacity=0.8,
                           annotation_text="Crítico (40%)", annotation_position="right",
                           annotation_font=dict(size=10, color="#dc3545"))
        
        fig_taxa.add_trace(go.Scatter(
            x=metrics_df["label_full"],
            y=metrics_df["success_rate_any"],
            mode="lines+markers",
            line=dict(color="#004F9E", width=2),
            marker=dict(color=metrics_df["color"].tolist(), size=12, line=dict(color="white", width=2)),
            name="Taxa de Sucesso",
            hovertemplate="<b>%{x}</b><br>Taxa: %{y:.1f}%<extra></extra>",
        ))
        
        fig_taxa.add_trace(go.Scatter(
            x=metrics_df["label_full"],
            y=metrics_df["Media_Movel_3"],
            mode="lines",
            line=dict(color="#3498db", width=2, dash="dash"),
            name="Média Móvel 3",
        ))
        
        fig_taxa.update_layout(
            title=dict(text="Taxa de Sucesso (%) — Construções com x > 40",
                       font=dict(size=15, family="Arial", color="#1a1a2e")),
            xaxis=dict(tickangle=-45, tickfont=dict(size=10), showgrid=False),
            yaxis=dict(title="%", range=[0, 100], tickfont=dict(size=11)),
            height=430,
            plot_bgcolor="white",
            paper_bgcolor="#fafafa",
            legend=dict(
                orientation="h", y=1.02, yanchor="bottom", x=1, xanchor="right",
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#ddd", borderwidth=1,
            ),
            margin=dict(l=55, r=100, t=70, b=130),
        )
        fig_taxa.update_xaxes(showgrid=False)
        fig_taxa.update_yaxes(showgrid=True, gridcolor="#E5E5E5", zeroline=True, zerolinecolor="#ccc")
        
        st.plotly_chart(fig_taxa, use_container_width=True)

    # ── Heatmap de Início das Construções ──────────────────────────────────────
    st.subheader("🗺️ Visualização Espacial")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Início das Sequências (1º Passe)**")
        start_x = summary_df["first_start_x"].dropna().tolist()
        start_y = summary_df["first_start_y"].dropna().tolist()
        
        if start_x:
            fig_start = heatmap_fig(start_x, start_y, f"Origem das Construções (n={len(start_x)})")
            st.pyplot(fig_start)
            plt.close(fig_start)
    
    with col2:
        st.markdown("**Progressão das Sequências**")
        if not actions_df.empty:
            fig_prog = build_up_progression_chart(actions_df)
            if fig_prog:
                st.pyplot(fig_prog)
                plt.close(fig_prog)

    # ── Jogadores mais envolvidos ──────────────────────────────────────────────
    st.subheader("👥 Jogadores na Construção")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Jogadores que iniciam construções**")
        starters = summary_df["first_player"].value_counts().head(10).reset_index()
        starters.columns = ["Jogador", "Construções Iniciadas"]
        st.dataframe(starters, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("**Jogadores mais participativos**")
        if not actions_df.empty:
            participants = actions_df["player"].value_counts().head(10).reset_index()
            participants.columns = ["Jogador", "Ações"]
            st.dataframe(participants, use_container_width=True, hide_index=True)

    # ── Tabela Detalhada por Jogo ──────────────────────────────────────────────
    st.subheader("📋 Dados por Jogo")
    
    if not metrics_df.empty:
        display_cols = ["label_full", "n_build_ups", "n_total", "n_partial", "n_unsuccessful", 
                       "success_rate_any", "avg_actions", "avg_players"]
        display_cols = [c for c in display_cols if c in metrics_df.columns]
        
        st.data_editor(
            metrics_df[display_cols],
            column_config={
                "label_full": st.column_config.TextColumn("Jogo"),
                "n_build_ups": st.column_config.NumberColumn("Total Construções", format="%d"),
                "n_total": st.column_config.NumberColumn("Sucesso Total", format="%d"),
                "n_partial": st.column_config.NumberColumn("Sucesso Parcial", format="%d"),
                "n_unsuccessful": st.column_config.NumberColumn("Sem Sucesso", format="%d"),
                "success_rate_any": st.column_config.NumberColumn("Taxa Sucesso %", format="%.1f%%"),
                "avg_actions": st.column_config.NumberColumn("Média Ações", format="%.1f"),
                "avg_players": st.column_config.NumberColumn("Média Jogadores", format="%.1f"),
            },
            use_container_width=True, hide_index=True, disabled=True,
        )

# ══════════════════════════════════════════════════════════════════════════════
# PÁGINA 3 — HEATMAPS
# ══════════════════════════════════════════════════════════════════════════════

elif pagina == "🗺️ Heatmaps":
    render_header("Heatmaps — Construção e Perdas")

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
