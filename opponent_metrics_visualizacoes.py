import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO DA PÁGINA
# ══════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Famalicão — Métricas por Adversário",
    page_icon="⚽",
    layout="wide"
)

# ══════════════════════════════════════════════════════════════════════════
# LOGOS DOS CLUBES (base64 — funcionam em qualquer contexto)
# ══════════════════════════════════════════════════════════════════════════

CLUB_LOGOS = {
    "Famalicão": "https://upload.wikimedia.org/wikipedia/pt/4/49/FC_Famalic%C3%A3o.png",
    "AVS": "https://upload.wikimedia.org/wikipedia/pt/e/eb/AVS_Futebol_SAD.png",
    "Alverca": "https://upload.wikimedia.org/wikipedia/pt/8/87/FC_Alverca.png",
    "Benfica": "https://upload.wikimedia.org/wikipedia/pt/0/02/SL_Benfica_logo.svg",
    "Casa Pia AC": "https://upload.wikimedia.org/wikipedia/pt/5/5e/Casa_Pia_AC.png",
    "Estoril": "https://upload.wikimedia.org/wikipedia/pt/1/1e/GD_Estoril_Praia.png",
    "Estrela Amadora": "https://upload.wikimedia.org/wikipedia/pt/f/f8/CF_Estrela_da_Amadora.png",
    "FC Arouca": "https://upload.wikimedia.org/wikipedia/pt/b/b2/FC_Arouca.png",
    "FC Porto": "https://upload.wikimedia.org/wikipedia/pt/8/84/FC_Porto.png",
    "Gil Vicente": "https://upload.wikimedia.org/wikipedia/pt/b/b1/Gil_Vicente_FC_logo.png",
    "Moreirense": "https://upload.wikimedia.org/wikipedia/pt/5/54/Moreirense_FC.png",
    "Nacional": "https://upload.wikimedia.org/wikipedia/pt/2/21/CD_Nacional_logo.png",
    "Rio Ave": "https://upload.wikimedia.org/wikipedia/pt/b/b8/Rio_Ave_FC.png",
    "Santa Clara": "https://upload.wikimedia.org/wikipedia/pt/e/ea/CD_Santa_Clara.png",
    "Sporting Braga": "https://upload.wikimedia.org/wikipedia/pt/d/d1/SC_Braga.png",
    "Sporting CP": "https://upload.wikimedia.org/wikipedia/pt/e/e1/Sporting_Clube_de_Portugal_%28Logo%29.svg",
    "Tondela": "https://upload.wikimedia.org/wikipedia/pt/b/b7/CD_Tondela.png",
    "Vitória Guimarães": "https://upload.wikimedia.org/wikipedia/pt/8/81/Vit%C3%B3ria_SC.png",
}

CLUB_COLORS = {
    "AVS": "#1E3A8A",
    "Alverca": "#009B3A",
    "Benfica": "#E30613",
    "Casa Pia AC": "#1E3A5F",
    "Estoril": "#FFD700",
    "Estrela Amadora": "#E30613",
    "FC Arouca": "#FFD700",
    "FC Porto": "#003893",
    "Gil Vicente": "#E30613",
    "Moreirense": "#006847",
    "Nacional": "#000000",
    "Rio Ave": "#006847",
    "Santa Clara": "#E30613",
    "Sporting Braga": "#E30613",
    "Sporting CP": "#006847",
    "Tondela": "#006847",
    "Vitória Guimarães": "#000000",
}

# ══════════════════════════════════════════════════════════════════════════
# CARREGAR DADOS
# ══════════════════════════════════════════════════════════════════════════

@st.cache_data
def carregar_dados():
    """Carrega o CSV com as métricas por adversário."""
    df = pd.read_csv("opponent_metrics__4_.csv")
    return df

# ══════════════════════════════════════════════════════════════════════════
# FUNÇÕES DE GRÁFICOS (estilo idêntico ao código original)
# ══════════════════════════════════════════════════════════════════════════

def plot_horizontal_bar(df, col_value, title, xlabel, color="#e74c3c", colorscale=None):
    """Gráfico de barras horizontais ordenado."""
    agg = df.sort_values(col_value, ascending=True)
    
    fig = go.Figure()
    
    if colorscale:
        fig.add_trace(go.Bar(
            y=agg["opponent"],
            x=agg[col_value],
            orientation='h',
            marker_color=agg[col_value],
            marker_colorscale=colorscale,
            text=agg[col_value].round(2),
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>" + xlabel + ": %{x:.2f}<extra></extra>"
        ))
    else:
        # Usar cor do clube se disponível
        colors = [CLUB_COLORS.get(opp, color) for opp in agg["opponent"]]
        fig.add_trace(go.Bar(
            y=agg["opponent"],
            x=agg[col_value],
            orientation='h',
            marker_color=colors,
            text=agg[col_value].round(2),
            textposition='outside',
            hovertemplate="<b>%{y}</b><br>" + xlabel + ": %{x:.2f}<extra></extra>"
        ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Arial")),
        xaxis_title=xlabel,
        yaxis_title="",
        height=450,
        plot_bgcolor='white',
        margin=dict(l=120, r=40, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor='#EEEEEE')
    fig.update_yaxes(showgrid=False)
    
    return fig


def plot_stacked_metrics(df, col_mean, col_max, title, ylabel):
    """Gráfico de barras empilhadas (média + máximo)."""
    df_sorted = df.sort_values(col_mean, ascending=False)
    
    fig = go.Figure()
    
    # Barra da média
    fig.add_trace(go.Bar(
        x=df_sorted["opponent"],
        y=df_sorted[col_mean],
        name="Média",
        marker_color="#3498db",
        hovertemplate="<b>%{x}</b><br>Média: %{y:.2f}<extra></extra>"
    ))
    
    # Barra do máximo (empilhada)
    fig.add_trace(go.Bar(
        x=df_sorted["opponent"],
        y=df_sorted[col_max] - df_sorted[col_mean],
        name="Máximo",
        marker_color="#e74c3c",
        hovertemplate="<b>%{x}</b><br>Máximo: " + df_sorted[col_max].astype(str) + "<extra></extra>"
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
    
    return fig


def plot_scatter_comparison(df, x_col, y_col, title, xlabel, ylabel):
    """Scatter plot para comparar duas métricas."""
    fig = go.Figure()
    
    colors = [CLUB_COLORS.get(opp, "#3498db") for opp in df["opponent"]]
    
    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        mode='markers+text',
        marker=dict(
            size=df["n_games"] * 8 + 10,  # Tamanho baseado no nº de jogos
            color=colors,
            line=dict(color='white', width=1.5),
            opacity=0.8
        ),
        text=df["opponent"],
        textposition="top center",
        textfont=dict(size=9),
        hovertemplate="<b>%{text}</b><br>" + xlabel + ": %{x:.2f}<br>" + ylabel + ": %{y:.2f}<extra></extra>"
    ))
    
    # Linhas de referência (média)
    fig.add_hline(y=df[y_col].mean(), line_dash="dash", line_color="#888888", line_width=1, opacity=0.5)
    fig.add_vline(x=df[x_col].mean(), line_dash="dash", line_color="#888888", line_width=1, opacity=0.5)
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Arial")),
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        height=450,
        plot_bgcolor='white',
        margin=dict(l=60, r=40, t=60, b=60),
    )
    fig.update_xaxes(showgrid=True, gridcolor='#EEEEEE')
    fig.update_yaxes(showgrid=True, gridcolor='#EEEEEE')
    
    return fig


def plot_radar_chart(df, opponent):
    """Radar chart para um adversário específico."""
    row = df[df["opponent"] == opponent].iloc[0]
    
    # Normalizar métricas para 0-1
    metrics = ["n_shots_mean", "entry_last_third_mean", "shot_10_15_mean", "progression_mean", "transition_speed_mean"]
    labels = ["Remates (média)", "Entry 3rd (média)", "Remates 10-15s", "Progressão", "Vel. Transição"]
    
    values = []
    for m in metrics:
        max_val = df[m].max()
        if max_val > 0:
            values.append(row[m] / max_val)
        else:
            values.append(0)
    
    values.append(values[0])  # Fechar o radar
    labels.append(labels[0])
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=labels,
        fill='toself',
        fillcolor=CLUB_COLORS.get(opponent, "#3498db") + "40",
        line=dict(color=CLUB_COLORS.get(opponent, "#3498db"), width=2),
        name=opponent
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], showticklabels=False),
            angularaxis=dict(tickfont=dict(size=10))
        ),
        title=dict(text=f"Perfil de Transição: {opponent}", font=dict(size=14)),
        height=400,
        showlegend=False,
        margin=dict(l=60, r=60, t=80, b=60)
    )
    
    return fig


def plot_danger_index(df):
    """Gráfico com índice de perigo calculado."""
    # Calcular índice de perigo composto
    df_calc = df.copy()
    
    # Normalizar cada métrica
    for col in ["n_shots_mean", "entry_last_third_mean", "progression_mean", "transition_speed_mean"]:
        max_val = df_calc[col].max()
        if max_val > 0:
            df_calc[col + "_norm"] = df_calc[col] / max_val
        else:
            df_calc[col + "_norm"] = 0
    
    # Índice composto (pesos ajustáveis)
    df_calc["danger_index"] = (
        df_calc["n_shots_mean_norm"] * 0.30 +
        df_calc["entry_last_third_mean_norm"] * 0.25 +
        df_calc["progression_mean_norm"] * 0.25 +
        df_calc["transition_speed_mean_norm"] * 0.20
    ) * 100
    
    df_calc = df_calc.sort_values("danger_index", ascending=True)
    
    fig = go.Figure()
    
    # Zonas de risco
    fig.add_vrect(x0=0, x1=33, fillcolor="#2ecc71", opacity=0.08, line_width=0)
    fig.add_vrect(x0=33, x1=66, fillcolor="#e67e22", opacity=0.08, line_width=0)
    fig.add_vrect(x0=66, x1=100, fillcolor="#e74c3c", opacity=0.08, line_width=0)
    
    colors = [
        "#2ecc71" if x < 33 else "#e67e22" if x < 66 else "#e74c3c"
        for x in df_calc["danger_index"]
    ]
    
    fig.add_trace(go.Bar(
        y=df_calc["opponent"],
        x=df_calc["danger_index"],
        orientation='h',
        marker_color=colors,
        text=df_calc["danger_index"].round(1),
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Índice de Perigo: %{x:.1f}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text="Índice de Perigo de Transição por Adversário", font=dict(size=14, family="Arial")),
        xaxis_title="Índice de Perigo (0-100)",
        yaxis_title="",
        height=500,
        plot_bgcolor='white',
        margin=dict(l=120, r=40, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor='#EEEEEE', range=[0, 105])
    fig.update_yaxes(showgrid=False)
    
    return fig, df_calc


# ══════════════════════════════════════════════════════════════════════════
# INTERFACE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

# Header
col_logo, col_title = st.columns([1, 10])
with col_logo:
    st.image(CLUB_LOGOS.get("Famalicão", ""), width=70)
with col_title:
    st.title("Famalicão — Métricas de Transição por Adversário")

st.caption("Liga Portugal 25/26 | Análise de Comportamento Adversário após Perda de Bola")

# Carregar dados
try:
    df = carregar_dados()
except FileNotFoundError:
    st.error("❌ Ficheiro 'opponent_metrics__4_.csv' não encontrado. Coloca-o na mesma pasta do script.")
    st.stop()

# ── Filtros ──────────────────────────────────────────────────────────────
st.sidebar.header("Filtros")

# Filtro por adversário
adversarios = ["Todos"] + sorted(df["opponent"].unique().tolist())
sel_adv = st.sidebar.selectbox("Adversário", adversarios)

# Filtro por número mínimo de jogos
min_jogos = st.sidebar.slider("Nº mínimo de jogos", 1, int(df["n_games"].max()), 1)

# Aplicar filtros
df_f = df.copy()
if sel_adv != "Todos":
    df_f = df_f[df_f["opponent"] == sel_adv]
df_f = df_f[df_f["n_games"] >= min_jogos]

if df_f.empty:
    st.warning("Nenhum adversário encontrado com os filtros selecionados.")
    st.stop()

# ══════════════════════════════════════════════════════════════════════════
# RESUMO EXECUTIVO
# ══════════════════════════════════════════════════════════════════════════

st.subheader("📊 Resumo Executivo")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Adversários Analisados", f"{len(df_f)}")
c2.metric("Remates Médios (opp)", f"{df_f['n_shots_mean'].mean():.2f}")
c3.metric("Entry 3rd Média", f"{df_f['entry_last_third_mean'].mean():.2f}")
c4.metric("Progressão Média", f"{df_f['progression_mean'].mean():.1f}m")
c5.metric("Vel. Transição Média", f"{df_f['transition_speed_mean'].mean():.1f}")

# ── Semáforo ─────────────────────────────────────────────────────────────
progression_media = df_f['progression_mean'].mean()
if progression_media < 25:
    semaforo = "🟢 Baixa Progressão Adversária"
elif progression_media < 35:
    semaforo = "🟡 Progressão Moderada"
else:
    semaforo = "🔴 Alta Progressão Adversária"

st.markdown(f"### Nível Geral: {semaforo}")

# ══════════════════════════════════════════════════════════════════════════
# NOTAS EXPLICATIVAS
# ══════════════════════════════════════════════════════════════════════════

with st.expander("ℹ️ O que significa cada métrica?", expanded=False):
    st.markdown("""
**n_shots_mean / n_shots_max** — Número médio e máximo de remates adversários após perda de bola do Famalicão.

---

**entry_last_third_mean / max** — Frequência com que o adversário conseguiu entrar no último terço do campo após recuperar a bola (0-1 = percentagem).

---

**shot_10_15_mean / max** — Remates adversários no intervalo de 10-15 segundos após a perda (transições mais lentas).

---

**progression_mean / max** — Distância média/máxima (em metros) que o adversário avançou no campo após recuperar a bola.

---

**transition_speed_mean / max** — Velocidade média da transição adversária (metros/segundo nos primeiros segundos).

---

**n_games** — Número de jogos analisados contra cada adversário.
    """)

# ══════════════════════════════════════════════════════════════════════════
# ÍNDICE DE PERIGO
# ══════════════════════════════════════════════════════════════════════════

st.subheader("🎯 Índice de Perigo de Transição")
st.caption("Índice composto: 30% remates + 25% entry 3rd + 25% progressão + 20% velocidade")

fig_danger, df_danger = plot_danger_index(df_f)
st.plotly_chart(fig_danger, use_container_width=True)

# Adversário mais perigoso
if len(df_danger) > 0:
    mais_perigoso = df_danger.iloc[-1]["opponent"]
    idx_perigo = df_danger.iloc[-1]["danger_index"]
    st.info(f"⚠️ **Adversário mais perigoso em transição:** {mais_perigoso} (Índice: {idx_perigo:.1f})")

# ══════════════════════════════════════════════════════════════════════════
# GRÁFICOS POR MÉTRICA
# ══════════════════════════════════════════════════════════════════════════

st.subheader("📈 Análise por Métrica")

col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        plot_stacked_metrics(df_f, "progression_mean", "progression_max", 
                            "Progressão Adversária (metros)", "Progressão (m)"),
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        plot_stacked_metrics(df_f, "entry_last_third_mean", "entry_last_third_max",
                            "Entrada no Último Terço", "Entry Last Third"),
        use_container_width=True
    )

col3, col4 = st.columns(2)

with col3:
    st.plotly_chart(
        plot_stacked_metrics(df_f, "n_shots_mean", "n_shots_max",
                            "Remates Adversários após Perda", "Remates"),
        use_container_width=True
    )

with col4:
    st.plotly_chart(
        plot_stacked_metrics(df_f, "transition_speed_mean", "transition_speed_max",
                            "Velocidade de Transição", "Vel. Transição"),
        use_container_width=True
    )

# ══════════════════════════════════════════════════════════════════════════
# SCATTER PLOTS
# ══════════════════════════════════════════════════════════════════════════

st.subheader("🔍 Correlações entre Métricas")

col_s1, col_s2 = st.columns(2)

with col_s1:
    st.plotly_chart(
        plot_scatter_comparison(df_f, "progression_mean", "entry_last_third_mean",
                               "Progressão vs Entry Last Third",
                               "Progressão (m)", "Entry Last Third"),
        use_container_width=True
    )

with col_s2:
    st.plotly_chart(
        plot_scatter_comparison(df_f, "progression_mean", "n_shots_mean",
                               "Progressão vs Remates",
                               "Progressão (m)", "Remates (média)"),
        use_container_width=True
    )

# ══════════════════════════════════════════════════════════════════════════
# RADAR CHART (adversário específico)
# ══════════════════════════════════════════════════════════════════════════

st.subheader("🕸️ Perfil de Transição por Adversário")

sel_radar = st.selectbox("Seleciona um adversário para ver o perfil radar:", df_f["opponent"].tolist())

if sel_radar:
    col_r1, col_r2 = st.columns([1, 2])
    
    with col_r1:
        st.plotly_chart(plot_radar_chart(df_f, sel_radar), use_container_width=True)
    
    with col_r2:
        # Detalhes do adversário
        row = df_f[df_f["opponent"] == sel_radar].iloc[0]
        st.markdown(f"### {sel_radar}")
        st.markdown(f"**Jogos analisados:** {int(row['n_games'])}")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Remates (média)", f"{row['n_shots_mean']:.2f}")
            st.metric("Entry Last Third (média)", f"{row['entry_last_third_mean']:.2f}")
            st.metric("Remates 10-15s (média)", f"{row['shot_10_15_mean']:.2f}")
        
        with c2:
            st.metric("Progressão (média)", f"{row['progression_mean']:.1f}m")
            st.metric("Progressão (máx)", f"{row['progression_max']:.1f}m")
            st.metric("Vel. Transição (média)", f"{row['transition_speed_mean']:.1f}")

# ══════════════════════════════════════════════════════════════════════════
# RANKING E TABELA COMPLETA
# ══════════════════════════════════════════════════════════════════════════

st.subheader("📋 Ranking de Adversários")

# Adicionar índice de perigo à tabela
df_display = df_danger[["opponent", "danger_index", "n_games"]].merge(
    df_f[["opponent", "n_shots_mean", "entry_last_third_mean", "progression_mean", "transition_speed_mean"]],
    on="opponent"
)
df_display = df_display.sort_values("danger_index", ascending=False).reset_index(drop=True)
df_display.index += 1

# Renomear colunas
df_display.columns = ["Adversário", "Índice Perigo", "Jogos", "Remates (média)", 
                      "Entry 3rd (média)", "Progressão (média)", "Vel. Transição (média)"]

# Formatar
df_display["Índice Perigo"] = df_display["Índice Perigo"].round(1)
df_display["Remates (média)"] = df_display["Remates (média)"].round(2)
df_display["Entry 3rd (média)"] = df_display["Entry 3rd (média)"].round(2)
df_display["Progressão (média)"] = df_display["Progressão (média)"].round(1)
df_display["Vel. Transição (média)"] = df_display["Vel. Transição (média)"].round(1)

st.dataframe(df_display, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════
# TABELA COMPLETA (RAW)
# ══════════════════════════════════════════════════════════════════════════

with st.expander("📄 Ver tabela completa (dados originais)", expanded=False):
    st.dataframe(df_f, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════

st.markdown("---")
st.caption("Dados processados a partir de métricas de transição por adversário | Liga Portugal 25/26")
