import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import base64
from io import BytesIO
from datetime import datetime
warnings.filterwarnings('ignore')

# Configurações de visualização
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# ==========================================
# FUNÇÃO PARA CONVERTER IMAGEM EM BASE64
# ==========================================
def fig_to_base64(fig):
    """Converte figura matplotlib em string base64 para embedding em HTML"""
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{image_base64}"

# ==========================================
# 1. CARREGAMENTO E PREPARAÇÃO DOS DADOS
# ==========================================

# Carregar o dataset
df = pd.read_csv('github_prs_dataset.csv', sep=';')

print("=" * 80)
print("RELATÓRIO DE ANÁLISE - LABORATÓRIO 03")
print("Caracterizando a atividade de code review no GitHub")
print("=" * 80)

# Informações básicas do dataset
total_prs = len(df)
total_repos = df['repository'].nunique()
dist_status = df['state'].value_counts()

print(f"\nTotal de Pull Requests analisados: {total_prs}")
print(f"Repositórios únicos: {total_repos}")
print(f"\nDistribuição dos PRs por status:")
print(dist_status)

# Criar variáveis derivadas
df['total_lines_changed'] = df['additions'] + df['deletions']
df['description_length'] = df['title'].fillna('').str.len()

# ==========================================
# 2. ANÁLISE DESCRITIVA GERAL
# ==========================================

print("\n" + "=" * 80)
print("ESTATÍSTICAS DESCRITIVAS")
print("=" * 80)

metricas = ['changed_files', 'additions', 'deletions', 'total_lines_changed', 
            'duration_hours', 'participants_count', 'comments_total', 'review_count']

desc_stats = df[metricas + ['state']].groupby('state').describe()

# Calcular medianas gerais
medianas_gerais = {metrica: df[metrica].median() for metrica in metricas}

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def calcular_correlacao(df, var1, var2, metodo='spearman'):
    """Calcula correlação e p-valor"""
    dados = df[[var1, var2]].dropna()
    
    if metodo == 'spearman':
        corr, p_valor = stats.spearmanr(dados[var1], dados[var2])
    else:
        corr, p_valor = stats.pearsonr(dados[var1], dados[var2])
    
    return corr, p_valor, len(dados)

def interpretar_correlacao(corr):
    """Interpreta o valor da correlação"""
    abs_corr = abs(corr)
    if abs_corr < 0.3:
        return "fraca"
    elif abs_corr < 0.7:
        return "moderada"
    else:
        return "forte"

# ==========================================
# 3. ANÁLISE DAS QUESTÕES DE PESQUISA
# ==========================================

resultados_rqs = {}

print("\n" + "=" * 80)
print("QUESTÕES DE PESQUISA")
print("=" * 80)

# ==========================================
# RQ 01: Tamanho dos PRs vs Status
# ==========================================
print("\n" + "-" * 80)
print("RQ 01: Qual a relação entre o tamanho dos PRs e o feedback final?")
print("-" * 80)

rq01_resultados = []
metricas_tamanho = ['changed_files', 'additions', 'deletions', 'total_lines_changed']

for metrica in metricas_tamanho:
    mediana_merged = df[df['state'] == 'MERGED'][metrica].median()
    mediana_closed = df[df['state'] == 'CLOSED'][metrica].median()
    
    statistic, p_valor = stats.mannwhitneyu(
        df[df['state'] == 'MERGED'][metrica].dropna(),
        df[df['state'] == 'CLOSED'][metrica].dropna()
    )
    
    resultado = {
        'metrica': metrica,
        'mediana_merged': mediana_merged,
        'mediana_closed': mediana_closed,
        'diferenca': abs(mediana_merged - mediana_closed),
        'p_valor': p_valor,
        'significativo': p_valor < 0.05
    }
    rq01_resultados.append(resultado)
    
    print(f"\n{metrica}:")
    print(f"  Mediana MERGED: {mediana_merged:.2f}")
    print(f"  Mediana CLOSED: {mediana_closed:.2f}")
    print(f"  p-valor: {p_valor:.4f} {'✓ Significativo' if p_valor < 0.05 else '✗ Não significativo'}")

resultados_rqs['rq01'] = rq01_resultados

# ==========================================
# RQ 02: Tempo vs Status
# ==========================================
print("\n\nRQ 02: Qual a relação entre o tempo de análise e o feedback final?")
print("-" * 80)

mediana_merged_time = df[df['state'] == 'MERGED']['duration_hours'].median()
mediana_closed_time = df[df['state'] == 'CLOSED']['duration_hours'].median()

statistic, p_valor = stats.mannwhitneyu(
    df[df['state'] == 'MERGED']['duration_hours'].dropna(),
    df[df['state'] == 'CLOSED']['duration_hours'].dropna()
)

rq02_resultado = {
    'mediana_merged': mediana_merged_time,
    'mediana_closed': mediana_closed_time,
    'p_valor': p_valor,
    'significativo': p_valor < 0.05
}

print(f"\nMediana MERGED: {mediana_merged_time:.2f} horas")
print(f"Mediana CLOSED: {mediana_closed_time:.2f} horas")
print(f"p-valor: {p_valor:.4f}")

resultados_rqs['rq02'] = rq02_resultado

# ==========================================
# RQ 03: Descrição vs Status
# ==========================================
print("\n\nRQ 03: Qual a relação entre a descrição dos PRs e o feedback final?")
print("-" * 80)

mediana_merged_desc = df[df['state'] == 'MERGED']['description_length'].median()
mediana_closed_desc = df[df['state'] == 'CLOSED']['description_length'].median()

statistic, p_valor = stats.mannwhitneyu(
    df[df['state'] == 'MERGED']['description_length'].dropna(),
    df[df['state'] == 'CLOSED']['description_length'].dropna()
)

rq03_resultado = {
    'mediana_merged': mediana_merged_desc,
    'mediana_closed': mediana_closed_desc,
    'p_valor': p_valor,
    'significativo': p_valor < 0.05
}

print(f"\nMediana MERGED: {mediana_merged_desc:.2f} caracteres")
print(f"Mediana CLOSED: {mediana_closed_desc:.2f} caracteres")
print(f"p-valor: {p_valor:.4f}")

resultados_rqs['rq03'] = rq03_resultado

# ==========================================
# RQ 04: Interações vs Status
# ==========================================
print("\n\nRQ 04: Qual a relação entre as interações nos PRs e o feedback final?")
print("-" * 80)

rq04_resultados = []
metricas_interacao = ['participants_count', 'comments_total']

for metrica in metricas_interacao:
    mediana_merged = df[df['state'] == 'MERGED'][metrica].median()
    mediana_closed = df[df['state'] == 'CLOSED'][metrica].median()
    
    statistic, p_valor = stats.mannwhitneyu(
        df[df['state'] == 'MERGED'][metrica].dropna(),
        df[df['state'] == 'CLOSED'][metrica].dropna()
    )
    
    resultado = {
        'metrica': metrica,
        'mediana_merged': mediana_merged,
        'mediana_closed': mediana_closed,
        'p_valor': p_valor,
        'significativo': p_valor < 0.05
    }
    rq04_resultados.append(resultado)
    
    print(f"\n{metrica}:")
    print(f"  Mediana MERGED: {mediana_merged:.2f}")
    print(f"  Mediana CLOSED: {mediana_closed:.2f}")
    print(f"  p-valor: {p_valor:.4f}")

resultados_rqs['rq04'] = rq04_resultados

# ==========================================
# RQ 05: Tamanho vs Revisões
# ==========================================
print("\n\nRQ 05: Qual a relação entre o tamanho dos PRs e o número de revisões?")
print("-" * 80)

rq05_resultados = []
for metrica in metricas_tamanho:
    corr_spearman, p_valor_spearman, n = calcular_correlacao(df, metrica, 'review_count', 'spearman')
    corr_pearson, p_valor_pearson, _ = calcular_correlacao(df, metrica, 'review_count', 'pearson')
    
    resultado = {
        'metrica': metrica,
        'spearman': corr_spearman,
        'p_spearman': p_valor_spearman,
        'pearson': corr_pearson,
        'p_pearson': p_valor_pearson,
        'interpretacao': interpretar_correlacao(corr_spearman),
        'n': n
    }
    rq05_resultados.append(resultado)
    
    print(f"\n{metrica}:")
    print(f"  Spearman ρ = {corr_spearman:.4f} (p = {p_valor_spearman:.4f})")
    print(f"  Interpretação: {interpretar_correlacao(corr_spearman)}")

resultados_rqs['rq05'] = rq05_resultados

# ==========================================
# RQ 06: Tempo vs Revisões
# ==========================================
print("\n\nRQ 06: Qual a relação entre o tempo de análise e o número de revisões?")
print("-" * 80)

corr_spearman, p_valor_spearman, n = calcular_correlacao(df, 'duration_hours', 'review_count', 'spearman')
corr_pearson, p_valor_pearson, _ = calcular_correlacao(df, 'duration_hours', 'review_count', 'pearson')

rq06_resultado = {
    'spearman': corr_spearman,
    'p_spearman': p_valor_spearman,
    'pearson': corr_pearson,
    'p_pearson': p_valor_pearson,
    'interpretacao': interpretar_correlacao(corr_spearman)
}

print(f"Spearman ρ = {corr_spearman:.4f} (p = {p_valor_spearman:.4f})")
print(f"Interpretação: {interpretar_correlacao(corr_spearman)}")

resultados_rqs['rq06'] = rq06_resultado

# ==========================================
# RQ 07: Descrição vs Revisões
# ==========================================
print("\n\nRQ 07: Qual a relação entre a descrição dos PRs e o número de revisões?")
print("-" * 80)

corr_spearman, p_valor_spearman, n = calcular_correlacao(df, 'description_length', 'review_count', 'spearman')
corr_pearson, p_valor_pearson, _ = calcular_correlacao(df, 'description_length', 'review_count', 'pearson')

rq07_resultado = {
    'spearman': corr_spearman,
    'p_spearman': p_valor_spearman,
    'pearson': corr_pearson,
    'p_pearson': p_valor_pearson,
    'interpretacao': interpretar_correlacao(corr_spearman)
}

print(f"Spearman ρ = {corr_spearman:.4f} (p = {p_valor_spearman:.4f})")

resultados_rqs['rq07'] = rq07_resultado

# ==========================================
# RQ 08: Interações vs Revisões
# ==========================================
print("\n\nRQ 08: Qual a relação entre as interações e o número de revisões?")
print("-" * 80)

rq08_resultados = []
for metrica in metricas_interacao:
    corr_spearman, p_valor_spearman, n = calcular_correlacao(df, metrica, 'review_count', 'spearman')
    corr_pearson, p_valor_pearson, _ = calcular_correlacao(df, metrica, 'review_count', 'pearson')
    
    resultado = {
        'metrica': metrica,
        'spearman': corr_spearman,
        'p_spearman': p_valor_spearman,
        'pearson': corr_pearson,
        'p_pearson': p_valor_pearson,
        'interpretacao': interpretar_correlacao(corr_spearman)
    }
    rq08_resultados.append(resultado)
    
    print(f"\n{metrica}:")
    print(f"  Spearman ρ = {corr_spearman:.4f} (p = {p_valor_spearman:.4f})")

resultados_rqs['rq08'] = rq08_resultados

# ==========================================
# 4. GERAÇÃO DE GRÁFICOS
# ==========================================

print("\n\n" + "=" * 80)
print("GERANDO VISUALIZAÇÕES...")
print("=" * 80)

graficos_base64 = {}

# Gráfico RQ01
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

metricas_plot = [('changed_files', 'Arquivos Alterados'),
                 ('additions', 'Linhas Adicionadas'),
                 ('deletions', 'Linhas Removidas'),
                 ('total_lines_changed', 'Total de Linhas Modificadas')]

for idx, (metrica, titulo) in enumerate(metricas_plot):
    ax = axes[idx // 2, idx % 2]
    df.boxplot(column=metrica, by='state', ax=ax)
    ax.set_title(titulo, fontsize=11, fontweight='bold', pad=10)
    ax.set_xlabel('Status do PR', fontsize=10)
    ax.set_ylabel('Quantidade', fontsize=10)
    ax.get_figure().suptitle('')

plt.suptitle('RQ01: Relação entre Tamanho dos PRs e Feedback Final', 
             fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.98])
graficos_base64['rq01'] = fig_to_base64(fig)
print("✓ Gráfico RQ01 gerado")

# Gráfico RQ02
fig, ax = plt.subplots(figsize=(10, 6))
df.boxplot(column='duration_hours', by='state', ax=ax)
ax.set_xlabel('Status do PR', fontsize=11)
ax.set_ylabel('Duração (horas)', fontsize=11)
ax.get_figure().suptitle('')
plt.title('RQ02: Tempo de Análise por Status do PR', 
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
graficos_base64['rq02'] = fig_to_base64(fig)
print("✓ Gráfico RQ02 gerado")

# Gráfico RQ03
fig, ax = plt.subplots(figsize=(10, 6))
df.boxplot(column='description_length', by='state', ax=ax)
ax.set_xlabel('Status do PR', fontsize=11)
ax.set_ylabel('Comprimento (caracteres)', fontsize=11)
ax.get_figure().suptitle('')
plt.title('RQ03: Comprimento da Descrição por Status do PR', 
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
graficos_base64['rq03'] = fig_to_base64(fig)
print("✓ Gráfico RQ03 gerado")

# Gráfico RQ04
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for idx, (metrica, titulo) in enumerate([('participants_count', 'Participantes'), 
                                          ('comments_total', 'Comentários Totais')]):
    ax = axes[idx]
    df.boxplot(column=metrica, by='state', ax=ax)
    ax.set_title(titulo, fontsize=11, fontweight='bold', pad=10)
    ax.set_xlabel('Status do PR', fontsize=10)
    ax.set_ylabel('Quantidade', fontsize=10)
    ax.get_figure().suptitle('')

plt.suptitle('RQ04: Interações nos PRs por Status', 
             fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.98])
graficos_base64['rq04'] = fig_to_base64(fig)
print("✓ Gráfico RQ04 gerado")

# Gráfico RQ05
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

for idx, (metrica, titulo) in enumerate(metricas_plot):
    ax = axes[idx // 2, idx % 2]
    ax.scatter(df[metrica], df['review_count'], alpha=0.5, s=20)
    ax.set_xlabel(titulo, fontsize=10)
    ax.set_ylabel('Número de Revisões', fontsize=10)
    ax.set_title(titulo, fontsize=11, fontweight='bold', pad=10)
    
    # Linha de tendência
    dados_validos = df[[metrica, 'review_count']].dropna()
    if len(dados_validos) > 1:
        z = np.polyfit(dados_validos[metrica], dados_validos['review_count'], 1)
        p = np.poly1d(z)
        x_sorted = np.sort(dados_validos[metrica])
        ax.plot(x_sorted, p(x_sorted), "r--", alpha=0.8, linewidth=2)
    
    # Correlação
    corr, _ = stats.spearmanr(dados_validos[metrica], dados_validos['review_count'])
    ax.text(0.05, 0.95, f'ρ = {corr:.3f}', transform=ax.transAxes, 
            fontsize=10, verticalalignment='top', 
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

plt.suptitle('RQ05: Relação entre Tamanho dos PRs e Número de Revisões', 
             fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.98])
graficos_base64['rq05'] = fig_to_base64(fig)
print("✓ Gráfico RQ05 gerado")

# Gráfico RQ06
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df['duration_hours'], df['review_count'], alpha=0.5)
ax.set_xlabel('Duração (horas)', fontsize=11)
ax.set_ylabel('Número de Revisões', fontsize=11)

dados_validos = df[['duration_hours', 'review_count']].dropna()
corr, _ = stats.spearmanr(dados_validos['duration_hours'], dados_validos['review_count'])
ax.text(0.05, 0.95, f'Correlação de Spearman: ρ = {corr:.3f}', 
        transform=ax.transAxes, fontsize=10, verticalalignment='top', 
        bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.9))
plt.title('RQ06: Relação entre Tempo de Análise e Número de Revisões', 
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
graficos_base64['rq06'] = fig_to_base64(fig)
print("✓ Gráfico RQ06 gerado")

# Gráfico RQ07
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(df['description_length'], df['review_count'], alpha=0.5)
ax.set_xlabel('Comprimento da Descrição (caracteres)', fontsize=11)
ax.set_ylabel('Número de Revisões', fontsize=11)

dados_validos = df[['description_length', 'review_count']].dropna()
corr, _ = stats.spearmanr(dados_validos['description_length'], dados_validos['review_count'])
ax.text(0.05, 0.95, f'Correlação de Spearman: ρ = {corr:.3f}', 
        transform=ax.transAxes, fontsize=10, verticalalignment='top', 
        bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.9))
plt.title('RQ07: Relação entre Descrição dos PRs e Número de Revisões', 
          fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
graficos_base64['rq07'] = fig_to_base64(fig)
print("✓ Gráfico RQ07 gerado")

# Gráfico RQ08
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

for idx, (metrica, titulo) in enumerate([('participants_count', 'Participantes'), 
                                          ('comments_total', 'Comentários Totais')]):
    ax = axes[idx]
    ax.scatter(df[metrica], df['review_count'], alpha=0.5)
    ax.set_xlabel(titulo, fontsize=11)
    ax.set_ylabel('Número de Revisões', fontsize=11)
    ax.set_title(titulo, fontsize=11, fontweight='bold', pad=10)
    
    dados_validos = df[[metrica, 'review_count']].dropna()
    corr, _ = stats.spearmanr(dados_validos[metrica], dados_validos['review_count'])
    ax.text(0.05, 0.95, f'ρ = {corr:.3f}', transform=ax.transAxes, 
            fontsize=10, verticalalignment='top', 
            bbox=dict(boxstyle='round', facecolor='#f8f9fa', alpha=0.9))

plt.suptitle('RQ08: Relação entre Interações e Número de Revisões', 
             fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.98])
graficos_base64['rq08'] = fig_to_base64(fig)
print("✓ Gráfico RQ08 gerado")

# ==========================================
# 5. GERAÇÃO DO HTML (SEGUINDO O PADRÃO)
# ==========================================

html_content = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Análise de Repositórios Populares do GitHub</title>
    <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            padding: 40px;
            background-color: #f8f9fa;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1200px;
        }}
        h1, h2, h3 {{
            color: #343a40;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 20px;
            font-weight: 300;
        }}
        h2.autores {{
            text-align: center;
            font-size: 1.2em;
            color: #6c757d;
            margin-bottom: 50px;
            font-weight: 400;
        }}
        .rq-section {{
            margin-bottom: 40px;
            padding: 30px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            background-color: #fff;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
        }}
        .rq-section h3 {{
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
            margin-bottom: 20px;
            color: #007bff;
            font-weight: 500;
        }}
        .grafico {{
            text-align: center;
            margin-top: 25px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
        li {{
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>Relatório de Análise de Repositórios Populares do GitHub</h1>
    <h2 class="autores">Alunos: [Seu Nome Aqui]</h2>
    
    <div class="rq-section">
        <h3><i class="fas fa-book-open mr-2"></i>Introdução</h3>
        <p>Este estudo tem como objetivo analisar as características de code review em Pull Requests de repositórios populares do GitHub, a fim de entender os padrões que podem levar à aceitação ou rejeição de contribuições.</p>
        
        <p>Para guiar nossa análise, formulamos as seguintes hipóteses informais para cada questão de pesquisa (RQ):</p>
        <ul>
            <li><b>RQ01: Tamanho</b> – Esperamos que PRs menores tenham maior taxa de aceitação.</li>
            <li><b>RQ02: Tempo de Análise</b> – Acreditamos que PRs aceitos sejam revisados mais rapidamente.</li>
            <li><b>RQ03: Descrição</b> – Nossa hipótese é que descrições mais completas facilitam a aceitação.</li>
            <li><b>RQ04: Interações</b> – Esperamos que maior engajamento correlacione com aceitação.</li>
            <li><b>RQ05: Tamanho vs Revisões</b> – Acreditamos que PRs maiores exijam mais revisões.</li>
            <li><b>RQ06: Tempo vs Revisões</b> – Esperamos correlação positiva entre tempo e número de revisões.</li>
            <li><b>RQ07: Descrição vs Revisões</b> – Acreditamos que descrições mais longas gerem mais discussão.</li>
            <li><b>RQ08: Interações vs Revisões</b> – Esperamos forte correlação entre participação e revisões.</li>
        </ul>
    </div>
    
    <div class="rq-section">
        <h3><i class="fas fa-cogs mr-2"></i>Metodologia</h3>
        <p>Para responder às questões de pesquisa, adotamos a seguinte metodologia, dividida em três etapas principais:</p>
        
        <ol>
            <li><b>Coleta de Dados</b>
                <ul>
                    <li>Utilizamos um dataset com <strong>{total_prs}</strong> Pull Requests de <strong>{total_repos}</strong> repositórios populares.</li>
                    <li>As métricas coletadas incluem: status, tamanho (arquivos, adições, deleções), tempo de análise, participantes e comentários.</li>
                    <li>Os dados foram salvos em formato <strong>CSV</strong> (<code>github_prs_dataset.csv</code>).</li>
                </ul>
            </li>
            <li><b>Processamento e Análise de Dados</b>
                <ul>
                    <li>O arquivo CSV foi carregado utilizando a biblioteca <strong>Pandas</strong>.</li>
                    <li>Novas métricas foram calculadas (ex: total_lines_changed, description_length).</li>
                    <li>A análise focou na <strong>mediana</strong>, por ser mais robusta a outliers.</li>
                    <li>Utilizamos o <strong>teste de Mann-Whitney U</strong> para comparações entre grupos e <strong>Correlação de Spearman</strong> para relações entre variáveis.</li>
                </ul>
            </li>
            <li><b>Visualização e Geração do Relatório</b>
                <ul>
                    <li>Utilizamos <strong>Matplotlib</strong> e <strong>Seaborn</strong> para visualizações (boxplots e scatter plots).</li>
                    <li>Um script Python consolidou análises, textos e gráficos em relatório <strong>HTML</strong>.</li>
                </ul>
            </li>
        </ol>
    </div>
    
    <div class="rq-section">
        <h3><i class="fas fa-chart-bar mr-2"></i>Resultados e Discussões</h3>
        <p>A seguir, apresentamos os resultados detalhados para cada questão de pesquisa.</p>
    </div>
    
    <!-- RQ01 -->
    <div class="rq-section">
        <h3>RQ01: Sistemas populares são maduros/antigos?</h3>
        <p><b>Análise:</b> A mediana da idade dos 1.000 repositórios mais populares é de <b>3058 dias</b> (aproximadamente <b>8.4 anos</b>).</p>
        <p><b>Discussão:</b> O valor mediano de quase 8.4 anos confirma a hipótese de que a maioria dos repositórios populares não é recente, possuindo um tempo considerável de existência e desenvolvimento.</p>
        
        <table class="table table-bordered text-center mt-3">
            <tr>
                <th>Métrica</th>
                <th>Mediana MERGED</th>
                <th>Mediana CLOSED</th>
                <th>p-valor</th>
                <th>Significativo?</th>
            </tr>
"""

for r in rq01_resultados:
    status_class = 'table-success' if r['significativo'] else 'table-warning'
    status_text = '✓ Sim' if r['significativo'] else '✗ Não'
    html_content += f"""
            <tr class="{status_class}">
                <td><code>{r['metrica']}</code></td>
                <td>{r['mediana_merged']:.2f}</td>
                <td>{r['mediana_closed']:.2f}</td>
                <td>{r['p_valor']:.4f}</td>
                <td>{status_text}</td>
            </tr>
"""

html_content += f"""
        </table>
        
        <div class="grafico">
            <img src="{graficos_base64['rq01']}" class="img-fluid" alt="Gráfico para RQ01">
        </div>
    </div>
    
    <!-- RQ02 -->
    <div class="rq-section">
        <h3>RQ02: Qual a relação entre o tempo de análise e o feedback final?</h3>
        <p><b>Análise:</b> Mediana MERGED: <b>{rq02_resultado['mediana_merged']:.2f}</b> horas | 
        Mediana CLOSED: <b>{rq02_resultado['mediana_closed']:.2f}</b> horas</p>
        <p><b>p-valor:</b> {rq02_resultado['p_valor']:.4f} 
        {'<span class="badge badge-success">Significativo</span>' if rq02_resultado['significativo'] else '<span class="badge badge-warning">Não significativo</span>'}</p>
        <p><b>Discussão:</b> {'O tempo de análise apresenta diferença significativa entre PRs aceitos e rejeitados.' if rq02_resultado['significativo'] else 'O tempo de análise não apresenta diferença significativa.'}</p>
        
        <div class="grafico">
            <img src="{graficos_base64['rq02']}" class="img-fluid" alt="Gráfico para RQ02">
        </div>
    </div>
    
    <!-- RQ03 -->
    <div class="rq-section">
        <h3>RQ03: Qual a relação entre a descrição dos PRs e o feedback final?</h3>
        <p><b>Análise:</b> Mediana MERGED: <b>{rq03_resultado['mediana_merged']:.2f}</b> caracteres | 
        Mediana CLOSED: <b>{rq03_resultado['mediana_closed']:.2f}</b> caracteres</p>
        <p><b>p-valor:</b> {rq03_resultado['p_valor']:.4f} 
        {'<span class="badge badge-success">Significativo</span>' if rq03_resultado['significativo'] else '<span class="badge badge-warning">Não significativo</span>'}</p>
        
        <div class="grafico">
            <img src="{graficos_base64['rq03']}" class="img-fluid" alt="Gráfico para RQ03">
        </div>
    </div>
    
    <!-- RQ04 -->
    <div class="rq-section">
        <h3>RQ04: Qual a relação entre as interações nos PRs e o feedback final?</h3>
        <table class="table table-bordered text-center mt-3">
            <tr>
                <th>Métrica</th>
                <th>Mediana MERGED</th>
                <th>Mediana CLOSED</th>
                <th>p-valor</th>
                <th>Significativo?</th>
            </tr>
"""

for r in rq04_resultados:
    status_class = 'table-success' if r['significativo'] else 'table-warning'
    status_text = '✓ Sim' if r['significativo'] else '✗ Não'
    html_content += f"""
            <tr class="{status_class}">
                <td><code>{r['metrica']}</code></td>
                <td>{r['mediana_merged']:.2f}</td>
                <td>{r['mediana_closed']:.2f}</td>
                <td>{r['p_valor']:.4f}</td>
                <td>{status_text}</td>
            </tr>
"""

html_content += f"""
        </table>
        
        <div class="grafico">
            <img src="{graficos_base64['rq04']}" class="img-fluid" alt="Gráfico para RQ04">
        </div>
    </div>
    
    <!-- RQ05 -->
    <div class="rq-section">
        <h3>RQ05: Qual a relação entre o tamanho dos PRs e o número de revisões?</h3>
        <table class="table table-bordered text-center mt-3">
            <tr>
                <th>Métrica</th>
                <th>Correlação Spearman (ρ)</th>
                <th>p-valor</th>
                <th>Interpretação</th>
            </tr>
"""

for r in rq05_resultados:
    html_content += f"""
            <tr>
                <td><code>{r['metrica']}</code></td>
                <td>{r['spearman']:.4f}</td>
                <td>{r['p_spearman']:.4f}</td>
                <td><span class="badge badge-info">{r['interpretacao'].capitalize()}</span></td>
            </tr>
"""

html_content += f"""
        </table>
        
        <div class="grafico">
            <img src="{graficos_base64['rq05']}" class="img-fluid" alt="Gráfico para RQ05">
        </div>
    </div>
    
    <!-- RQ06 -->
    <div class="rq-section">
        <h3>RQ06: Qual a relação entre o tempo de análise e o número de revisões?</h3>
        <p><b>Correlação de Spearman:</b> ρ = {rq06_resultado['spearman']:.4f} (p-valor: {rq06_resultado['p_spearman']:.4f})</p>
        <p><b>Interpretação:</b> <span class="badge badge-info">{rq06_resultado['interpretacao'].capitalize()}</span></p>
        
        <div class="grafico">
            <img src="{graficos_base64['rq06']}" class="img-fluid" alt="Gráfico para RQ06">
        </div>
    </div>
    
    <!-- RQ07 -->
    <div class="rq-section">
        <h3>RQ07: Qual a relação entre a descrição dos PRs e o número de revisões?</h3>
        <p><b>Correlação de Spearman:</b> ρ = {rq07_resultado['spearman']:.4f} (p-valor: {rq07_resultado['p_spearman']:.4f})</p>
        <p><b>Interpretação:</b> <span class="badge badge-info">{rq07_resultado['interpretacao'].capitalize()}</span></p>
        
        <div class="grafico">
            <img src="{graficos_base64['rq07']}" class="img-fluid" alt="Gráfico para RQ07">
        </div>
    </div>
    
    <!-- RQ08 -->
    <div class="rq-section">
        <h3>RQ08: Qual a relação entre as interações e o número de revisões?</h3>
        <table class="table table-bordered text-center mt-3">
            <tr>
                <th>Métrica</th>
                <th>Correlação Spearman (ρ)</th>
                <th>p-valor</th>
                <th>Interpretação</th>
            </tr>
"""

for r in rq08_resultados:
    html_content += f"""
            <tr>
                <td><code>{r['metrica']}</code></td>
                <td>{r['spearman']:.4f}</td>
                <td>{r['p_spearman']:.4f}</td>
                <td><span class="badge badge-info">{r['interpretacao'].capitalize()}</span></td>
            </tr>
"""

html_content += f"""
        </table>
        
        <div class="grafico">
            <img src="{graficos_base64['rq08']}" class="img-fluid" alt="Gráfico para RQ08">
        </div>
    </div>
    
    <!-- Conclusão -->
    <div class="rq-section">
        <h3><i class="fas fa-check-circle mr-2"></i>Conclusão</h3>
        <p>Este estudo analisou <strong>{total_prs}</strong> Pull Requests de <strong>{total_repos}</strong> repositórios populares do GitHub, revelando padrões importantes sobre code review.</p>
        
        <p><b>Principais Achados:</b></p>
        <ul>
            <li>Testes estatísticos rigorosos (Mann-Whitney U e Spearman) garantiram a confiabilidade dos resultados.</li>
            <li>Os fatores analisados fornecem insights valiosos para desenvolvedores otimizarem suas contribuições.</li>
            <li>A análise confirma/refuta hipóteses sobre práticas eficazes de code review.</li>
        </ul>
        
        <p><b>Recomendações Práticas:</b></p>
        <ul>
            <li><strong>Para Contribuidores:</strong> Manter PRs concisos, bem documentados e com escopo limitado facilita a aprovação.</li>
            <li><strong>Para Revisores:</strong> Estabelecer critérios claros e feedback construtivo acelera o processo.</li>
            <li><strong>Para Projetos:</strong> Documentar guidelines de contribuição melhora a qualidade geral.</li>
        </ul>
    </div>
    
    <div class="text-center text-muted mt-5">
        <p>Relatório gerado automaticamente em {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}</p>
        <p>Laboratório de Experimentação de Software - Lab03</p>
    </div>
</div>
</body>
</html>
"""

# Salvar HTML
with open('relatorio_lab03.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("\n✓ Relatório HTML gerado: relatorio_lab03.html")

# ==========================================
# 6. EXPORTAR RESUMO CSV
# ==========================================

resumo = pd.DataFrame({
    'Métrica': metricas,
    'Mediana_Geral': [df[m].median() for m in metricas],
    'Mediana_MERGED': [df[df['state'] == 'MERGED'][m].median() for m in metricas],
    'Mediana_CLOSED': [df[df['state'] == 'CLOSED'][m].median() for m in metricas],
    'Media_Geral': [df[m].mean() for m in metricas],
    'Desvio_Padrao': [df[m].std() for m in metricas]
})

resumo.to_csv('resumo_estatistico.csv', index=False)
print("✓ Resumo estatístico salvo: resumo_estatistico.csv")

print("\n" + "=" * 80)
print("ANÁLISE CONCLUÍDA COM SUCESSO!")
print("=" * 80)
print("\nArquivos gerados:")
print("  - relatorio_lab03.html (RELATÓRIO COMPLETO)")
print("  - resumo_estatistico.csv")
print("\n" + "=" * 80)
