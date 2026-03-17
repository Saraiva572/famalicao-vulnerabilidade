import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Vulnerabilidade à Perda - Famalicão", layout="wide")
st.title("🔴 Famalicão — Análise de Vulnerabilidade à Perda")
st.caption("Dashboard baseado em dados reais StatsBomb — atualizado automaticamente")

# --- Credenciais via Streamlit Secrets ---
USER = st.secrets["STATSBOMB_USER"]
PASS = st.secrets["STATSBOMB_PASS"]

COMPETITION_ID    = 13
SEASON_ID         = 318
TEAM_NAME         = "Famalicão"
TRANSITION_WINDOW = 10
DEEP_ENTRY_X      = 80
team_key          = "Famalic"
auth              = (USER, PASS)

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

def safe_x(loc):
    if isinstance(loc, list) and len(loc) >= 1:
        return loc[0]
    return None

def classificar_risco(vap):
    if vap < 10:
        return "🟢 Baixo"
    elif vap <= 20:
        return "🟡 Médio"
    return "🔴 Alto"

@st.cache_data(ttl=3600, show_spinner="A carregar dados da API StatsBomb...")
def carregar_dados():
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
    team_matches = matches[mask].copy()

    def get_opponent(row):
        if team_key.lower() in row[HOME_COL].lower():
            return row[AWAY_COL]
        return row[HOME_COL]

    team_matches["opponent"]   = team_matches.apply(get_opponent, axis=1)
    team_matches["match_date"] = pd.to_datetime(team_matches["match_date"])
    team_matches = team_matches.sort_values("match_date").reset_index(drop=True)

    results = []

    for _, row in team_matches.iterrows():
        match_id   = int(row["match_id"])
        match_date = row["match_date"].strftime("%Y-%m-%d")
        opponent   = row["opponent"]

        ev = pd.json_normalize(
            get_json(f"https://data.statsbombservices.com/api/v8/events/{match_id}"),
            sep="."
        )

        TYPE_COL    = "type.name"
        POSS_COL    = "possession_team.name"
        PATTERN_COL = "play_pattern.name"
        PASS_OUT    = "pass.outcome.name"
        SHOT_XG     = "shot.statsbomb_xg"

        ev["time_s"] = ev["timestamp"].apply(ts_to_seconds) + (ev["period"] - 1) * 45 * 60
        ev["loc_x"]  = ev["location"].apply(safe_x)

        fama_ev = ev[ev[POSS_COL].apply(
            lambda x: team_key.lower() in str(x).lower()
        )].copy()

        loss_mask = (
            (fama_ev[TYPE_COL].isin({"Miscontrol", "Dispossessed"})) |
            (
                (fama_ev[TYPE_COL] == "Pass") &
                (fama_ev.get(PASS_OUT, pd.Series(dtype=str)) == "Incomplete") &
                (fama_ev["loc_x"].apply(lambda x: x <= 40 if x is not None else False))
            )
        )
        losses = fama_ev[loss_mask].copy()

        high_press_shots  = 0
        counter_shots     = 0
        shots_in_clear    = 0
        deep_progressions = 0
        xg_total          = 0.0

        for _, loss_event in losses.iterrows():
            loss_time       = loss_event["time_s"]
            loss_possession = loss_event["possession"]

            opp_after = ev[
                (ev["possession"] > loss_possession) &
                (ev["time_s"] >= loss_time) &
                (ev["time_s"] <= loss_time + TRANSITION_WINDOW) &
                (~ev[POSS_COL].apply(lambda x: team_key.lower() in str(x).lower()))
            ]
            if opp_after.empty:
                continue

            shots_after = opp_after[opp_after[TYPE_COL] == "Shot"]
            for _, shot in shots_after.iterrows():
                play_pat = str(shot.get(PATTERN_COL, ""))
                if "Counter" in play_pat:
                    counter_shots += 1
                elif shot["time_s"] - loss_time <= 5:
                    high_press_shots += 1
                xg_val = shot.get(SHOT_XG, 0) or 0
                if xg_val >= 0.15:
                    shots_in_clear += 1
                xg_total += xg_val

            deep_entries = opp_after[
                opp_after["loc_x"].apply(lambda x: x >= DEEP_ENTRY_X if x is not None else False)
            ]
            deep_progressions += len(deep_entries)

        results.append({
            "match_id":   match_id,
            "match_date": match_date,
            "opponent":   opponent,
            "team_name":  TEAM_NAME,
            "team_match_high_press_shots_conceded":        high_press_shots,
            "team_match_counter_attacking_shots_conceded": counter_shots,
            "team_match_shots_in_clear_conceded":          shots_in_clear,
            "team_match_deep_progressions_conceded":       deep_progressions,
            "team_match_xg_conceded_after_loss":           round(xg_total, 3),
        })

    df = pd.DataFrame(results)
    df["VAP"] = (
        4   * df["team_match_high_press_shots_conceded"] +
        3   * df["team_match_counter_attacking_shots_conceded"] +
        2   * df["team_match_shots_in_clear_conceded"] +
        0.1 * df["team_match_deep_progressions_conceded"]
    )
    df["Risco"]        = df["VAP"].apply(classificar_risco)
    df["Media_Movel_3"] = df["VAP"].rolling(3, min_periods=1).mean()
    return df

# --- Carregar dados ---
df = carregar_dados()

# --- Filtro por adversário ---
st.sidebar.header("Filtros")
adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
sel = st.sidebar.selectbox("Adversário", adversarios)
df_f = df.copy() if sel == "Todos" else df[df["opponent"] == sel].copy()

# --- Resumo Executivo ---
st.subheader("Resumo Executivo")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("VAP média", f"{df_f['VAP'].mean():.2f}")
col2.metric("Maior VAP", f"{df_f['VAP'].max():.2f}")
col3.metric("Menor VAP", f"{df_f['VAP'].min():.2f}")
col4.metric("Jogo mais crítico", df_f.loc[df_f["VAP"].idxmax(), "opponent"])
col5.metric("xG sofrido total", f"{df_f['team_match_xg_conceded_after_loss'].sum():.2f}")

# --- Semáforo último jogo ---
ultimo = df_f.iloc[-1]
st.subheader("Semáforo de risco do último jogo")
st.markdown(f"### {ultimo['Risco']}  |  vs {ultimo['opponent']}  |  VAP = {ultimo['VAP']:.2f}")

# --- Tabela completa ---
st.subheader("Tabela completa")
cols = [c for c in [
    "match_id", "match_date", "opponent",
    "team_match_high_press_shots_conceded",
    "team_match_counter_attacking_shots_conceded",
    "team_match_shots_in_clear_conceded",
    "team_match_deep_progressions_conceded",
    "team_match_xg_conceded_after_loss",
    "VAP", "Risco", "Media_Movel_3"
] if c in df_f.columns]
st.dataframe(df_f[cols], use_container_width=True)

# --- Ranking ---
st.subheader("Ranking dos jogos mais vulneráveis")
ranking = df_f.sort_values("VAP", ascending=False)[
    ["match_date", "opponent", "VAP", "team_match_xg_conceded_after_loss", "Risco"]
].reset_index(drop=True)
ranking.index += 1
st.dataframe(ranking, use_container_width=True)

# --- Gráficos ---
st.subheader("Linha temporal da vulnerabilidade")
st.line_chart(df_f.set_index("opponent")[["VAP", "Media_Movel_3"]])

st.subheader("Vulnerabilidade por jogo")
st.bar_chart(df_f.set_index("opponent")["VAP"])

st.subheader("xG sofrido após perda por jogo")
st.bar_chart(df_f.set_index("opponent")["team_match_xg_conceded_after_loss"])

