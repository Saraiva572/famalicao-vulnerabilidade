import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Vulnerabilidade à Perda - Famalicão", layout="wide")
st.title("🔴 Famalicão — Análise de Vulnerabilidade à Perda")
st.caption("Dashboard baseado em dados reais StatsBomb")

uploaded_file = st.file_uploader("Carrega o CSV", type="csv")

def classificar_risco(vap):
    if vap < 10:
        return "🟢 Baixo"
    elif vap <= 20:
        return "🟡 Médio"
    return "🔴 Alto"

if uploaded_file is not None:
    raw = uploaded_file.getvalue()
    try:
        text = raw.decode("utf-8")
    except:
        text = raw.decode("cp1252")

    df = pd.read_csv(io.StringIO(text), sep=";")
    df.columns = df.columns.str.strip().str.replace("\ufeff", "", regex=False)

    df["VAP"] = (
        4   * df["team_match_high_press_shots_conceded"] +
        3   * df["team_match_counter_attacking_shots_conceded"] +
        2   * df["team_match_shots_in_clear_conceded"] +
        0.1 * df["team_match_deep_progressions_conceded"]
    )
    df["Risco"] = df["VAP"].apply(classificar_risco)
    df = df.sort_values("match_id").reset_index(drop=True)
    df["Media_Movel_3"] = df["VAP"].rolling(3, min_periods=1).mean()

    # --- Filtro por adversário na sidebar ---
    st.sidebar.header("Filtros")
    adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
    sel_adversario = st.sidebar.selectbox("Adversário", adversarios)

    df_filtered = df.copy() if sel_adversario == "Todos" else df[df["opponent"] == sel_adversario].copy()

    # --- Resumo Executivo ---
    st.subheader("Resumo Executivo")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("VAP média", f"{df_filtered['VAP'].mean():.2f}")
    col2.metric("Maior VAP", f"{df_filtered['VAP'].max():.2f}")
    col3.metric("Menor VAP", f"{df_filtered['VAP'].min():.2f}")
    col4.metric("Jogo mais crítico", df_filtered.loc[df_filtered["VAP"].idxmax(), "opponent"])
    if "team_match_xg_conceded_after_loss" in df_filtered.columns:
        col5.metric("xG sofrido total", f"{df_filtered['team_match_xg_conceded_after_loss'].sum():.2f}")

    # --- Semáforo último jogo ---
    ultimo = df_filtered.iloc[-1]
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
    ] if c in df_filtered.columns]
    st.dataframe(df_filtered[cols], use_container_width=True)

    # --- Ranking ---
    st.subheader("Ranking dos jogos mais vulneráveis")
    rank_cols = [c for c in ["match_date", "opponent", "VAP", "team_match_xg_conceded_after_loss", "Risco"] if c in df_filtered.columns]
    ranking = df_filtered.sort_values("VAP", ascending=False)[rank_cols].reset_index(drop=True)
    ranking.index += 1
    st.dataframe(ranking, use_container_width=True)

    # --- Gráficos com nome do adversário ---
    st.subheader("Linha temporal da vulnerabilidade")
    st.line_chart(df_filtered.set_index("opponent")[["VAP", "Media_Movel_3"]])

    st.subheader("Vulnerabilidade por jogo")
    st.bar_chart(df_filtered.set_index("opponent")["VAP"])

    if "team_match_xg_conceded_after_loss" in df_filtered.columns:
        st.subheader("xG sofrido após perda por jogo")
        st.bar_chart(df_filtered.set_index("opponent")["team_match_xg_conceded_after_loss"])

