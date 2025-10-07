# gerar_relatorio.py
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import base64
from io import BytesIO
import webbrowser
import os

# --- CONFIGURAÇÕES ---
ARQUIVO_CSV = "repositorios_graphql_completo.csv"
ARQUIVO_HTML = "relatorio_completo.html"
ARQUIVO_PDF = "relatorio_completo.pdf"
NOMES_ALUNOS = "Pedro Reis e Gabriel Fernandes"
TITULO_RELATORIO = "Relatório de Análise de Repositórios Populares do GitHub"

# --- NOVAS SEÇÕES DE TEXTO ---

INTRODUCAO_TEXTO = """
    <div class="rq-section">
        <h3><i class="fas fa-book-open mr-2"></i>Introdução</h3>
        <p>Este estudo tem como objetivo analisar as características comuns entre os 1.000 repositórios mais populares do GitHub, mensurados pelo número de estrelas, a fim de entender os padrões que podem levar ao sucesso de um projeto de código aberto.</p>
        <p>Para guiar nossa análise, formulamos as seguintes hipóteses informais para cada questão de pesquisa (RQ):</p>
        <ul>
            <li><b>RQ01 (Idade):</b> Esperamos que sistemas populares sejam maduros, com vários anos de desenvolvimento contínuo.</li>
            <li><b>RQ02 (Contribuição Externa):</b> Acreditamos que projetos de sucesso recebem um volume muito alto de contribuições externas (Pull Requests).</li>
            <li><b>RQ03 (Releases):</b> Nossa hipótese é que projetos populares lançam novas versões (releases) com boa frequência para entregar valor aos usuários.</li>
            <li><b>RQ04 (Atualização):</b> Esperamos que esses sistemas sejam atualizados constantemente, com novas contribuições de código (pushes) ocorrendo quase diariamente.</li>
            <li><b>RQ05 (Linguagens):</b> Acreditamos que as linguagens mais populares na indústria, como o ecossistema JavaScript (incluindo TypeScript) e Python, dominarão a lista.</li>
            <li><b>RQ06 (Issues):</b> Projetos populares devem ter uma boa gestão de issues, resultando em uma alta porcentagem de issues fechadas.</li>
            <li><b>RQ07 (Bônus):</b> Acreditamos que as métricas de atividade (contribuições, releases e atualizações) podem variar significativamente entre as diferentes comunidades de linguagens de programação.</li>
        </ul>
    </div>
"""

METODOLOGIA_TEXTO = """
    <div class="rq-section">
        <h3><i class="fas fa-cogs mr-2"></i>Metodologia</h3>
        <p>Para responder às questões de pesquisa, adotamos a seguinte metodologia, dividida em três etapas principais:</p>
        <ol>
            <li><b>Coleta de Dados:</b>
                <ul>
                    <li>Utilizamos um script em Python para interagir com a <strong>API GraphQL do GitHub (v4)</strong>.</li>
                    <li>A busca foi configurada para retornar os 1.000 repositórios com o maior número de estrelas (<code>query: "stars:>=1 sort:stars-desc"</code>).</li>
                    <li>Para evitar sobrecarga na API e erros de timeout, a coleta foi dividida em duas fases: uma busca inicial "leve" para obter a lista dos repositórios e, em seguida, requisições individuais para cada um a fim de obter métricas detalhadas.</li>
                    <li>As métricas coletadas para cada repositório foram: nome, estrelas, data de criação, data do último push, linguagem primária, contagem de pull requests aceitas, contagem de releases e contagens de issues totais e fechadas.</li>
                    <li>Os dados brutos foram salvos em um arquivo no formato <strong>CSV</strong> (<code>repositorios_graphql_completo.csv</code>).</li>
                </ul>
            </li>
            <li><b>Processamento e Análise de Dados:</b>
                <ul>
                    <li>O arquivo CSV foi carregado em um DataFrame utilizando a biblioteca <strong>Pandas</strong>.</li>
                    <li>Novas métricas foram calculadas a partir dos dados brutos, como a idade do repositório em dias, os dias desde o último push e a razão de issues fechadas.</li>
                    <li>A análise focou no cálculo de valores de tendência central, especificamente a <strong>mediana</strong>, por ser uma medida mais robusta a outliers em distribuições assimétricas, comuns em dados de popularidade. Para dados categóricos (linguagens), realizamos a contagem de frequência.</li>
                </ul>
            </li>
            <li><b>Visualização e Geração do Relatório:</b>
                <ul>
                    <li>Utilizamos as bibliotecas <strong>Matplotlib</strong> e <strong>Seaborn</strong> para gerar visualizações gráficas (histogramas e gráficos de barras) para cada questão de pesquisa.</li>
                    <li>Um script final em Python foi responsável por consolidar todas as análises, textos e gráficos em um único relatório no formato <strong>HTML</strong>, que foi posteriormente convertido para <strong>PDF</strong>.</li>
                </ul>
            </li>
        </ol>
    </div>
"""


# --- FUNÇÕES DE ANÁLISE E PLOTAGEM ---


def analisar_rq01(df):
    """Analisa a idade dos repositórios (RQ01)."""
    print("Analisando RQ01: Idade dos repositórios...")
    mediana_idade = df["idade_dias"].median()
    mediana_anos = mediana_idade / 365.25

    texto = f"""
    <p><b>Análise:</b> A mediana da idade dos 1.000 repositórios mais populares é de <b>{mediana_idade:.0f} dias</b> (aproximadamente <b>{mediana_anos:.1f} anos</b>).</p>
    <p><b>Discussão:</b> O valor mediano de quase {mediana_anos:.1f} anos confirma a hipótese de que a maioria dos repositórios populares não é recente, possuindo um tempo considerável de existência e desenvolvimento.</p>
    """

    plt.figure(figsize=(10, 6))
    sns.histplot(df["idade_dias"], bins=50, kde=True)
    plt.title("RQ01: Distribuição da Idade dos Repositórios (em dias)", fontsize=16)
    plt.xlabel("Idade (dias)", fontsize=12)
    plt.ylabel("Número de Repositórios", fontsize=12)
    plt.axvline(
        mediana_idade,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mediana: {mediana_idade:.0f} dias",
    )
    plt.legend()
    plt.grid(axis="y", alpha=0.75)

    return texto, plot_to_base64()


def analisar_rq02(df):
    """Analisa o total de pull requests (RQ02)."""
    print("Analisando RQ02: Contribuição externa (Pull Requests)...")
    mediana_prs = df["total_pull_requests_aceitas"].median()

    texto = f"""
    <p><b>Análise:</b> A mediana do total de pull requests aceitas é de <b>{mediana_prs:.0f}</b>.</p>
    <p><b>Discussão:</b> Este valor mediano indica um volume significativo e constante de contribuições da comunidade. O gráfico de distribuição (boxplot) mostra que, embora a mediana seja alta, existem repositórios (outliers) que recebem um volume de contribuições ordens de magnitude maior, como frameworks e bibliotecas de uso massivo.</p>
    """

    plt.figure(figsize=(10, 6))
    sns.boxplot(x=df["total_pull_requests_aceitas"])
    plt.title("RQ02: Distribuição do Total de Pull Requests Aceitas", fontsize=16)
    plt.xlabel("Total de Pull Requests (escala log)", fontsize=12)
    plt.xscale("log")
    plt.grid(axis="x", alpha=0.75)

    return texto, plot_to_base64()


def analisar_rq03(df):
    """Analisa o total de releases (RQ03)."""
    print("Analisando RQ03: Frequência de releases...")
    mediana_releases = df["total_releases"].median()

    texto = f"""
    <p><b>Análise:</b> A mediana do total de releases é de <b>{mediana_releases:.0f}</b>.</p>
    <p><b>Discussão:</b> A mediana sugere que a prática de versionamento formal via releases é bem estabelecida entre os projetos populares. Uma mediana de {mediana_releases:.0f} releases ao longo da vida do projeto indica um ciclo de desenvolvimento maduro e organizado.</p>
    """

    plt.figure(figsize=(10, 6))
    sns.boxplot(x=df["total_releases"])
    plt.title("RQ03: Distribuição do Total de Releases", fontsize=16)
    plt.xlabel("Total de Releases (escala log)", fontsize=12)
    plt.xscale("log")
    plt.grid(axis="x", alpha=0.75)

    return texto, plot_to_base64()


def analisar_rq04(df):
    """Analisa a frequência de atualização (RQ04)."""
    print("Analisando RQ04: Frequência de atualização...")
    mediana_atualizacao = df["dias_desde_ultimo_push"].median()

    texto = f"""
    <p><b>Análise:</b> A mediana de dias desde a última atualização é de <b>{mediana_atualizacao:.0f} dias</b>.</p>
    <p><b>Discussão:</b> Uma mediana de {mediana_atualizacao:.0f} dias confirma que são projetos extremamente ativos, com metade dos repositórios tendo recebido código novo neste curto período.</p>
    """

    dados_filtrados = df[df["dias_desde_ultimo_push"] < 365]
    plt.figure(figsize=(10, 6))
    sns.histplot(dados_filtrados["dias_desde_ultimo_push"], bins=50, kde=True)
    plt.title(
        "RQ04: Distribuição de Dias Desde a Última Atualização (no último ano)",
        fontsize=16,
    )
    plt.xlabel("Dias desde o último push", fontsize=12)
    plt.ylabel("Número de Repositórios", fontsize=12)
    plt.axvline(
        mediana_atualizacao,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mediana: {mediana_atualizacao:.0f} dias",
    )
    plt.legend()
    plt.grid(axis="y", alpha=0.75)

    return texto, plot_to_base64()


def analisar_rq05(df):
    """Analisa as linguagens primárias (RQ05)."""
    print("Analisando RQ05: Linguagens primárias...")
    contagem_linguagens = df["linguagem_primaria"].value_counts().nlargest(15)
    tabela_html = contagem_linguagens.to_frame().to_html(
        classes="table table-striped text-center"
    )

    texto = f"""
    <p><b>Análise:</b> A contagem das 15 linguagens primárias mais frequentes é apresentada abaixo.</p>
    <p><b>Discussão:</b> Conforme esperado, o ecossistema JavaScript e Python são dominantes. A presença de Go, Rust e Kotlin reflete tendências modernas no desenvolvimento de software.</p>
    <div style="display: flex; justify-content: center;"><div style="margin-right: 50px;">
    <h4>Contagem de Repositórios por Linguagem (Top 15)</h4>{tabela_html}</div></div>
    """

    plt.figure(figsize=(12, 8))
    sns.barplot(
        x=contagem_linguagens.values,
        y=contagem_linguagens.index,
        palette="viridis",
        orient="h",
    )
    plt.title("RQ05: Top 15 Linguagens Primárias Mais Populares", fontsize=16)
    plt.xlabel("Número de Repositórios", fontsize=12)
    plt.ylabel("Linguagem", fontsize=12)
    plt.tight_layout()

    return texto, plot_to_base64()


def analisar_rq06(df):
    """Analisa a razão de issues fechadas (RQ06)."""
    print("Analisando RQ06: Razão de issues fechadas...")
    mediana_razao_issues = df["razao_issues_fechadas"].median()

    texto = f"""
    <p><b>Análise:</b> A mediana da razão entre issues fechadas e o total de issues é de <b>{mediana_razao_issues:.2f}</b> (ou <b>{mediana_razao_issues*100:.0f}%</b>).</p>
    <p><b>Discussão:</b> Uma mediana de {mediana_razao_issues*100:.0f}% é um indicador muito forte de saúde e boa manutenção do projeto. Mostra que a maioria dos projetos populares consegue gerenciar e resolver a grande maioria dos problemas e sugestões que recebem da comunidade.</p>
    """

    plt.figure(figsize=(10, 6))
    sns.histplot(df["razao_issues_fechadas"], bins=40, kde=True)
    plt.title("RQ06: Distribuição da Razão de Issues Fechadas", fontsize=16)
    plt.xlabel("Razão (Issues Fechadas / Total de Issues)", fontsize=12)
    plt.ylabel("Número de Repositórios", fontsize=12)
    plt.axvline(
        mediana_razao_issues,
        color="red",
        linestyle="--",
        linewidth=2,
        label=f"Mediana: {mediana_razao_issues:.2f}",
    )
    plt.legend()
    plt.grid(axis="y", alpha=0.75)

    return texto, plot_to_base64()


def analisar_rq07(df):
    """Analisa métricas por linguagem (RQ07 - Bônus)."""
    print("Analisando RQ07 (Bônus): Métricas por linguagem...")

    top_10_languages = df["linguagem_primaria"].value_counts().nlargest(10).index
    df_top_lang = df[df["linguagem_primaria"].isin(top_10_languages)]

    grouped_stats = (
        df_top_lang.groupby("linguagem_primaria")
        .agg(
            {
                "total_pull_requests_aceitas": "median",
                "total_releases": "median",
                "dias_desde_ultimo_push": "median",
            }
        )
        .sort_values(by="total_pull_requests_aceitas", ascending=False)
    )

    texto = f"""
    <p><b>Análise:</b> O gráfico abaixo compara a mediana de Pull Requests, Releases e Dias desde o Último Push para as 10 linguagens mais populares no dataset.</p>
    <p><b>Discussão:</b> A análise revela nuances interessantes. Por exemplo, linguagens como Rust e Go, apesar de modernas, mostram um alto volume mediano de contribuições, refletindo comunidades vibrantes. A frequência de atualização (menor número de dias desde o último push) é consistentemente baixa em todas as linguagens populares, confirmando que todos são projetos ativos. As diferenças na mediana de releases podem indicar culturas de desenvolvimento distintas entre as comunidades de cada linguagem.</p>
    """

    fig, ax = plt.subplots(3, 1, figsize=(12, 18), sharex=True)

    sns.barplot(
        x=grouped_stats.index,
        y=grouped_stats["total_pull_requests_aceitas"],
        ax=ax[0],
        palette="plasma",
    )
    ax[0].set_title("Mediana de Pull Requests Aceitas por Linguagem", fontsize=14)
    ax[0].set_ylabel("Mediana de PRs")
    ax[0].set_yscale("log")

    sns.barplot(
        x=grouped_stats.index,
        y=grouped_stats["total_releases"],
        ax=ax[1],
        palette="viridis",
    )
    ax[1].set_title("Mediana de Releases por Linguagem", fontsize=14)
    ax[1].set_ylabel("Mediana de Releases")
    ax[1].set_yscale("log")

    sns.barplot(
        x=grouped_stats.index,
        y=grouped_stats["dias_desde_ultimo_push"],
        ax=ax[2],
        palette="coolwarm",
    )
    ax[2].set_title("Mediana de Dias Desde o Último Push por Linguagem", fontsize=14)
    ax[2].set_ylabel("Mediana de Dias")

    plt.xlabel("Linguagem Primária", fontsize=12)
    plt.xticks(rotation=45, ha="right")
    plt.suptitle("RQ07: Comparativo de Métricas por Linguagem", fontsize=20, y=0.95)
    plt.tight_layout(rect=[0, 0, 1, 0.93])

    return texto, plot_to_base64()


def plot_to_base64():
    """Converte um plot do matplotlib para uma string base64 para embutir no HTML."""
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return f"data:image/png;base64,{img_base64}"


def gerar_html(conteudo):
    """Gera o arquivo HTML final a partir de uma lista de seções."""
    html_template = f"""
    <!DOCTYPE html><html lang="pt-br"><head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{TITULO_RELATORIO}</title>
        <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; padding: 40px; background-color: #f8f9fa; line-height: 1.6; }}
            .container {{ max-width: 1200px; }}
            h1, h2, h3 {{ color: #343a40; }}
            h1 {{ text-align: center; margin-bottom: 20px; font-weight: 300; }}
            h2.autores {{ text-align: center; font-size: 1.2em; color: #6c757d; margin-bottom: 50px; font-weight: 400; }}
            .rq-section {{ margin-bottom: 40px; padding: 30px; border: 1px solid #dee2e6; border-radius: 8px; background-color: #fff; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }}
            .rq-section h3 {{ border-bottom: 2px solid #007bff; padding-bottom: 10px; margin-bottom: 20px; color: #007bff; font-weight: 500;}}
            .grafico {{ text-align: center; margin-top: 25px; padding: 15px; background-color: #f8f9fa; border-radius: 5px; }}
            li {{ margin-bottom: 8px; }}
        </style>
    </head><body><div class="container">
        <h1>{TITULO_RELATORIO}</h1>
        <h2 class="autores">Alunos: {NOMES_ALUNOS}</h2>
        
        {INTRODUCAO_TEXTO}
        {METODOLOGIA_TEXTO}
        
        <div class="rq-section">
            <h3><i class="fas fa-chart-bar mr-2"></i>Resultados e Discussões</h3>
            <p>A seguir, apresentamos os resultados detalhados para cada questão de pesquisa.</p>
        </div>

        {"".join(conteudo)}
        
    </div></body></html>
    """
    with open(ARQUIVO_HTML, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"\\nRelatório '{ARQUIVO_HTML}' gerado com sucesso!")


# --- BLOCO DE EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    try:
        df = pd.read_csv(ARQUIVO_CSV)
    except FileNotFoundError:
        print(f"ERRO: O arquivo '{ARQUIVO_CSV}' não foi encontrado.")
        print("Execute o script 'coleta_graphql.py' primeiro para gerar os dados.")
        exit()

    sessoes_rq = [
        ("01", "Sistemas populares são maduros/antigos?", analisar_rq01),
        ("02", "Sistemas populares recebem muita contribuição externa?", analisar_rq02),
        ("03", "Sistemas populares lançam releases com frequência?", analisar_rq03),
        ("04", "Sistemas populares são atualizados com frequência?", analisar_rq04),
        (
            "05",
            "Sistemas populares são escritos nas linguagens mais populares?",
            analisar_rq05,
        ),
        (
            "06",
            "Sistemas populares possuem um alto percentual de issues fechadas?",
            analisar_rq06,
        ),
        (
            "07 (Bônus)",
            "As métricas de atividade variam entre as linguagens mais populares?",
            analisar_rq07,
        ),
    ]

    html_content = []
    for rq_num, titulo, funcao_analise in sessoes_rq:
        section_html = f'<div class="rq-section"><h3>RQ{rq_num}: {titulo}</h3>'

        texto, grafico_b64 = funcao_analise(df)
        section_html += texto
        if grafico_b64:
            section_html += f'<div class="grafico"><img src="{grafico_b64}" class="img-fluid" alt="Gráfico para RQ{rq_num}"></div>'

        section_html += "</div>"
        html_content.append(section_html)

    gerar_html(html_content)

    try:
        webbrowser.open("file://" + os.path.realpath(ARQUIVO_HTML))
    except Exception as e:
        print(
            f"Não foi possível abrir o relatório no navegador. Abra o arquivo '{ARQUIVO_HTML}' manualmente."
        )
