import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import io

st.set_page_config(page_title="Análise de Vulnerabilidade - Famalicão", layout="wide")

# ============================================================
# DADOS EMBUTIDOS - Métricas de Construção (extraídos do notebook)
# ============================================================
METRICAS_CONSTRUCAO_DATA = """opponent,n_shots_mean,n_shots_max,xg_mean,xg_max,entry_last_third_mean,entry_last_third_max,shot_10_15_mean,shot_10_15_max,progression_mean,progression_max,transition_speed_mean,transition_speed_max,danger_score_mean,danger_score_max,n_games
Estrela Amadora,0.00,0,0.00,0.00,0.50,1,0.00,0,39.45,58.7,0.00,0.0,3.95,5.87,1
Moreirense,0.00,0,0.00,0.00,0.40,1,0.00,0,31.84,77.2,0.00,0.0,3.18,7.72,1
Sporting Braga,0.50,1,0.03,0.09,0.67,1,0.00,0,14.92,23.7,2.33,10.0,2.64,4.80,1
FC Arouca,0.25,1,0.01,0.10,0.25,1,0.00,0,20.39,56.1,1.00,7.0,2.60,5.61,2
Rio Ave,0.00,0,0.00,0.00,0.12,1,0.00,0,24.30,71.2,0.00,0.0,2.43,7.12,2
Tondela,0.00,0,0.00,0.00,0.35,1,0.00,0,22.11,48.7,0.00,0.0,2.21,4.87,2
FC Porto,0.00,0,0.00,0.00,0.38,1,0.00,0,21.82,52.3,0.00,0.0,2.18,5.23,1
Vitória Guimarães,0.00,0,0.00,0.00,0.45,1,0.00,0,21.42,44.4,0.00,0.0,2.14,4.44,2
Nacional,0.00,0,0.00,0.00,0.33,1,0.00,0,20.49,47.2,0.00,0.0,2.05,4.72,2
Casa Pia AC,0.00,0,0.00,0.00,0.34,1,0.00,0,19.94,48.3,0.00,0.0,1.99,4.83,2
Santa Clara,0.00,0,0.00,0.00,0.38,1,0.00,0,19.69,42.4,0.00,0.0,1.97,4.24,2
Gil Vicente,0.07,1,0.00,0.02,0.38,1,0.00,0,18.19,51.8,0.14,2.0,1.97,7.28,2
Estoril,0.12,1,0.00,0.04,0.25,1,0.12,1,15.68,38.4,1.62,13.0,1.84,3.84,1
Benfica,0.00,0,0.00,0.00,0.17,1,0.00,0,15.23,24.8,0.00,0.0,1.52,2.48,1
Alverca,0.12,1,0.00,0.03,0.25,1,0.00,0,12.29,30.0,0.50,4.0,1.50,3.00,1
AVS,0.00,0,0.00,0.00,0.22,1,0.00,0,13.85,36.6,0.00,0.0,1.38,3.66,2
Sporting CP,0.12,1,0.00,0.04,0.35,1,0.00,0,10.78,30.4,0.38,3.0,1.35,3.04,2"""

# Carregar dados de métricas de construção
df_construcao = pd.read_csv(io.StringIO(METRICAS_CONSTRUCAO_DATA))

# ============================================================
# SIDEBAR - Navegação
# ============================================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/pt/a/ad/FC_Famalic%C3%A3o.png", width=100)
st.sidebar.title("Famalicão Analytics")

pagina = st.sidebar.radio(
    "Navegação",
    ["📊 Dashboard VAP", "⚽ Métricas de Construção", "🎯 Análise por Adversário"]
)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def classificar_risco(vap):
    if vap < 10:
        return "🟢 Baixo"
    elif vap <= 20:
        return "🟡 Médio"
    return "🔴 Alto"

def classificar_danger(danger):
    if danger < 2.0:
        return "🟢 Baixo"
    elif danger <= 3.0:
        return "🟡 Médio"
    return "🔴 Alto"

# ============================================================
# PÁGINA 1: Dashboard VAP (original)
# ============================================================
if pagina == "📊 Dashboard VAP":
    st.title("📊 Análise de Vulnerabilidade à Perda (VAP)")
    st.caption("Dashboard para avaliar vulnerabilidade após perda de bola - Dados da API")
    
    uploaded_file = st.file_uploader("Carrega o CSV de vulnerabilidade", type="csv")
    
    if uploaded_file is not None:
        raw = uploaded_file.getvalue()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("cp1252")
        
        df = pd.read_csv(io.StringIO(text), sep=";")
        df.columns = df.columns.str.strip().str.replace("\ufeff", "", regex=False)
        
        df["VAP"] = (
            4 * df["team_match_high_press_shots_conceded"]
            + 3 * df["team_match_counter_attacking_shots_conceded"]
            + 2 * df["team_match_shots_in_clear_conceded"]
            + 0.1 * df["team_match_deep_progressions_conceded"]
        )
        
        df["Risco"] = df["VAP"].apply(classificar_risco)
        df = df.sort_values("match_id").reset_index(drop=True)
        df["Media_Movel_3"] = df["VAP"].rolling(3, min_periods=1).mean()
        
        # Métricas resumo
        st.subheader("Resumo Executivo")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("VAP média", f"{df['VAP'].mean():.2f}")
        col2.metric("Maior VAP", f"{df['VAP'].max():.2f}")
        col3.metric("Menor VAP", f"{df['VAP'].min():.2f}")
        col4.metric("Jogo mais crítico", int(df.loc[df["VAP"].idxmax(), "match_id"]))
        
        # Semáforo
        st.subheader("Semáforo de risco do último jogo")
        ultimo = df.iloc[-1]
        st.markdown(f"### {ultimo['Risco']}  |  Jogo {int(ultimo['match_id'])}  |  VAP = {ultimo['VAP']:.2f}")
        
        # Gráficos
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Evolução da Vulnerabilidade")
            fig = px.line(df, x="match_id", y=["VAP", "Media_Movel_3"],
                         labels={"value": "Score", "variable": "Métrica"},
                         title="VAP e Média Móvel (3 jogos)")
            fig.update_layout(hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("VAP por Jogo")
            fig = px.bar(df, x="match_id", y="VAP", color="Risco",
                        color_discrete_map={"🟢 Baixo": "#2ecc71", "🟡 Médio": "#f1c40f", "🔴 Alto": "#e74c3c"})
            st.plotly_chart(fig, use_container_width=True)
        
        # Tabela
        st.subheader("Tabela Completa")
        st.dataframe(
            df[["match_id", "team_name", "team_match_high_press_shots_conceded",
                "team_match_counter_attacking_shots_conceded", "team_match_shots_in_clear_conceded",
                "team_match_deep_progressions_conceded", "VAP", "Risco", "Media_Movel_3"]],
            use_container_width=True
        )
    else:
        st.info("👆 Carrega o ficheiro CSV para começar a análise")

# ============================================================
# PÁGINA 2: Métricas de Construção
# ============================================================
elif pagina == "⚽ Métricas de Construção":
    st.title("⚽ Métricas de Construção / Perda")
    st.caption("Análise de vulnerabilidade baseada em eventos StatsBomb - O que acontece quando perdemos a bola na construção")
    
    # Ordenar por danger_score
    df_sorted = df_construcao.sort_values("danger_score_mean", ascending=False)
    
    # Métricas resumo
    st.subheader("📈 Resumo Global")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Danger Score Médio", f"{df_sorted['danger_score_mean'].mean():.2f}")
    col2.metric("Adversário + Perigoso", df_sorted.iloc[0]['opponent'])
    col3.metric("Progressão Média", f"{df_sorted['progression_mean'].mean():.1f}m")
    col4.metric("Total de Jogos", int(df_sorted['n_games'].sum()))
    
    # Gráfico principal - Danger Score por Adversário
    st.subheader("🎯 Danger Score por Adversário")
    
    fig = px.bar(
        df_sorted,
        x="danger_score_mean",
        y="opponent",
        orientation="h",
        color="danger_score_mean",
        color_continuous_scale=["#2ecc71", "#f1c40f", "#e74c3c"],
        labels={"danger_score_mean": "Danger Score", "opponent": "Adversário"}
    )
    fig.update_layout(
        yaxis=dict(categoryorder="total ascending"),
        height=500,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Duas colunas para mais gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📏 Progressão Média (metros)")
        fig = px.bar(
            df_sorted.sort_values("progression_mean", ascending=True),
            x="progression_mean",
            y="opponent",
            orientation="h",
            color="progression_mean",
            color_continuous_scale="Reds"
        )
        fig.update_layout(yaxis=dict(categoryorder="total ascending"), height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚡ Velocidade de Transição")
        fig = px.bar(
            df_sorted.sort_values("transition_speed_mean", ascending=True),
            x="transition_speed_mean",
            y="opponent",
            orientation="h",
            color="transition_speed_mean",
            color_continuous_scale="Blues"
        )
        fig.update_layout(yaxis=dict(categoryorder="total ascending"), height=450, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # Scatter plot - Progressão vs Danger Score
    st.subheader("🔍 Relação: Progressão vs Danger Score")
    fig = px.scatter(
        df_sorted,
        x="progression_mean",
        y="danger_score_mean",
        size="n_games",
        color="entry_last_third_mean",
        hover_name="opponent",
        labels={
            "progression_mean": "Progressão Média (m)",
            "danger_score_mean": "Danger Score",
            "entry_last_third_mean": "Entradas Último Terço",
            "n_games": "Nº Jogos"
        },
        color_continuous_scale="RdYlGn_r"
    )
    fig.update_layout(height=450)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela completa
    st.subheader("📋 Tabela Completa")
    df_display = df_sorted[["opponent", "danger_score_mean", "danger_score_max", 
                            "progression_mean", "entry_last_third_mean", 
                            "transition_speed_mean", "n_games"]].copy()
    df_display.columns = ["Adversário", "Danger (Média)", "Danger (Máx)", 
                          "Progressão (m)", "Entradas Últ. Terço", 
                          "Vel. Transição", "Jogos"]
    df_display["Risco"] = df_display["Danger (Média)"].apply(classificar_danger)
    st.dataframe(df_display, use_container_width=True)

# ============================================================
# PÁGINA 3: Análise por Adversário
# ============================================================
elif pagina == "🎯 Análise por Adversário":
    st.title("🎯 Análise Detalhada por Adversário")
    st.caption("Perfil completo de vulnerabilidade contra cada adversário")
    
    # Seletor de adversário
    adversario = st.selectbox(
        "Seleciona o adversário",
        df_construcao.sort_values("danger_score_mean", ascending=False)["opponent"].tolist()
    )
    
    # Dados do adversário selecionado
    dados = df_construcao[df_construcao["opponent"] == adversario].iloc[0]
    
    # Cards de métricas
    st.subheader(f"📊 Métricas vs {adversario}")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Danger Score", f"{dados['danger_score_mean']:.2f}", 
                delta=f"Máx: {dados['danger_score_max']:.2f}")
    col2.metric("Progressão", f"{dados['progression_mean']:.1f}m",
                delta=f"Máx: {dados['progression_max']:.1f}m")
    col3.metric("Entradas Últ. Terço", f"{dados['entry_last_third_mean']:.2f}",
                delta=f"Máx: {dados['entry_last_third_max']}")
    col4.metric("Jogos Analisados", int(dados['n_games']))
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Remates", f"{dados['n_shots_mean']:.2f}",
                delta=f"Máx: {dados['n_shots_max']}")
    col2.metric("xG", f"{dados['xg_mean']:.3f}",
                delta=f"Máx: {dados['xg_max']:.3f}")
    col3.metric("Remate 10-15s", f"{dados['shot_10_15_mean']:.2f}",
                delta=f"Máx: {dados['shot_10_15_max']}")
    col4.metric("Vel. Transição", f"{dados['transition_speed_mean']:.2f}",
                delta=f"Máx: {dados['transition_speed_max']:.1f}")
    
    # Radar Chart
    st.subheader("🎯 Perfil de Ameaça")
    
    # Normalizar valores para o radar (0-1)
    categorias = ["Danger Score", "Progressão", "Ent. Últ. Terço", "Remates", "Vel. Transição"]
    
    max_vals = {
        "danger": df_construcao["danger_score_mean"].max(),
        "prog": df_construcao["progression_mean"].max(),
        "entry": df_construcao["entry_last_third_mean"].max(),
        "shots": max(df_construcao["n_shots_mean"].max(), 0.01),
        "speed": max(df_construcao["transition_speed_mean"].max(), 0.01)
    }
    
    valores = [
        dados["danger_score_mean"] / max_vals["danger"],
        dados["progression_mean"] / max_vals["prog"],
        dados["entry_last_third_mean"] / max_vals["entry"],
        dados["n_shots_mean"] / max_vals["shots"],
        dados["transition_speed_mean"] / max_vals["speed"]
    ]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=valores + [valores[0]],
        theta=categorias + [categorias[0]],
        fill='toself',
        name=adversario,
        line_color='#e74c3c',
        fillcolor='rgba(231, 76, 60, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1])
        ),
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Comparação com média
    st.subheader("📈 Comparação com Média da Liga")
    
    comparacao = pd.DataFrame({
        "Métrica": ["Danger Score", "Progressão (m)", "Entradas Últ. Terço", "Vel. Transição"],
        adversario: [dados["danger_score_mean"], dados["progression_mean"], 
                    dados["entry_last_third_mean"], dados["transition_speed_mean"]],
        "Média Liga": [df_construcao["danger_score_mean"].mean(), 
                       df_construcao["progression_mean"].mean(),
                       df_construcao["entry_last_third_mean"].mean(),
                       df_construcao["transition_speed_mean"].mean()]
    })
    
    fig = px.bar(
        comparacao.melt(id_vars="Métrica", var_name="Grupo", value_name="Valor"),
        x="Métrica",
        y="Valor",
        color="Grupo",
        barmode="group",
        color_discrete_map={adversario: "#e74c3c", "Média Liga": "#3498db"}
    )
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)
    
    # Classificação de risco
    st.subheader("⚠️ Avaliação de Risco")
    danger = dados["danger_score_mean"]
    if danger >= 3.0:
        st.error(f"🔴 **RISCO ALTO** - {adversario} é muito perigoso nas transições após recuperação. Atenção redobrada na saída de bola!")
    elif danger >= 2.0:
        st.warning(f"🟡 **RISCO MÉDIO** - {adversario} consegue criar algum perigo após recuperar a bola. Manter organização defensiva.")
    else:
        st.success(f"🟢 **RISCO BAIXO** - {adversario} tem dificuldade em criar perigo imediato após recuperação.")

# ============================================================
# FOOTER
# ============================================================
st.sidebar.markdown("---")
st.sidebar.caption("FC Famalicão - Análise de Performance")
st.sidebar.caption("Dados: StatsBomb | Época 2025/26")
