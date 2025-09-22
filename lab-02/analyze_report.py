import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from scipy.stats import pearsonr, spearmanr

# --- 1. CONFIGURAÇÕES ---
INPUT_CSV_FILE = "C:\\Users\\Pedro\\Desktop\\Lab\\repo-miner-puc\\lab-02\\result\\all_java_projects_class_metrics.csv"
OUTPUT_HTML_FILE = "relatorio_lab02s02.html"

# --- 2. FUNÇÕES DE ANÁLISE ---


def load_data(filepath):
    """Carrega os dados do CSV, conta repositórios únicos e retorna ambos."""
    try:
        df = pd.read_csv(filepath)
        print(f"Dados carregados com sucesso de '{filepath}'.")

        # Validação das colunas
        required_cols = ["cbo", "loc", "repository"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(
                f"O arquivo CSV deve conter as colunas: {', '.join(required_cols)}."
            )

        # Conta o número de repositórios únicos
        repo_count = df["repository"].nunique()
        print(f"Número de repositórios únicos encontrados: {repo_count}")

        return df, repo_count

    except FileNotFoundError:
        print(f"ERRO: O arquivo '{filepath}' não foi encontrado.")
        print(
            "Por favor, certifique-se de que o arquivo CSV da análise anterior está no mesmo diretório."
        )
        return None, 0
    except Exception as e:
        print(f"Ocorreu um erro ao carregar os dados: {e}")
        return None, 0


def calculate_statistics(df):
    """Calcula estatísticas descritivas para as colunas CBO e LOC."""
    metrics_df = df[["cbo", "loc"]]
    stats = metrics_df.describe()
    print("\n--- Análise Descritiva ---")
    print(stats)
    return stats


def perform_correlation_analysis(df):
    """Calcula a correlação de Pearson e Spearman entre LOC e CBO."""
    df_cleaned = df[["loc", "cbo"]].dropna()
    pearson_corr, _ = pearsonr(df_cleaned["loc"], df_cleaned["cbo"])
    spearman_corr, _ = spearmanr(df_cleaned["loc"], df_cleaned["cbo"])

    print("\n--- Análise de Correlação ---")
    print(f"Correlação de Pearson (LOC vs CBO): {pearson_corr:.4f}")
    print(f"Correlação de Spearman (LOC vs CBO): {spearman_corr:.4f}")

    return pearson_corr, spearman_corr


def create_visualization(df):
    """Cria e salva um gráfico de dispersão para LOC vs CBO."""
    print("\n--- Gerando Visualização ---")
    plt.figure(figsize=(10, 6))
    sns.regplot(
        x="loc",
        y="cbo",
        data=df,
        scatter_kws={"alpha": 0.2, "s": 10},
        line_kws={"color": "red", "linewidth": 2},
    )

    plt.title("Relação entre Tamanho da Classe (LOC) e Acoplamento (CBO)", fontsize=16)
    plt.xlabel("Linhas de Código (LOC)", fontsize=12)
    plt.ylabel("Acoplamento Entre Objetos (CBO)", fontsize=12)

    plt.xlim(0, df["loc"].quantile(0.95))
    plt.ylim(0, df["cbo"].quantile(0.95))

    plt.grid(True, which="both", linestyle="--", linewidth=0.5)

    img_buffer = BytesIO()
    plt.savefig(img_buffer, format="png", bbox_inches="tight")
    plt.close()

    img_base64 = base64.b64encode(img_buffer.getvalue()).decode("utf-8")

    print(f"Gráfico de dispersão gerado com sucesso.")
    return img_base64


# --- 3. GERAÇÃO DO RELATÓRIO HTML ---


def generate_html_report(stats_df, pearson_corr, spearman_corr, img_base64, repo_count):
    """Gera um relatório HTML completo com os resultados da análise."""

    def format_br(value):
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    stats_df_formatted = stats_df.applymap(format_br)
    stats_html = stats_df_formatted.to_html(
        classes="table table-striped table-bordered text-center", justify="center"
    )

    pearson_br = f"{pearson_corr:.4f}".replace(".", ",")
    spearman_br = f"{spearman_corr:.4f}".replace(".", ",")

    conclusion_text = ""
    if spearman_corr > 0.3:
        conclusion_text = f"""
        <p>A análise dos dados suporta fortemente as hipóteses iniciais.</p>
        <ol>
            <li><b>H1 (Classes maiores são mais propensas a ter maior acoplamento):</b> O gráfico de dispersão mostra uma clara tendência positiva. À medida que o valor de LOC (eixo X) aumenta, os valores de CBO (eixo Y) também tendem a aumentar.</li>
            <li><b>H2 (O acoplamento tem correlação com o tamanho):</b> A correlação de Spearman de <strong>{spearman_br}</strong> indica uma correlação positiva moderada entre o tamanho da classe e seu nível de acoplamento.</li>
        </ol>
        <p>Portanto, podemos concluir que, no contexto dos projetos analisados, o tamanho de uma classe é um fator que influencia seu nível de acoplamento.</p>
        """
    else:
        conclusion_text = f"""
        <p>A análise dos dados fornece insights sobre as hipóteses iniciais.</p>
         <ol>
            <li><b>H1 (Classes maiores são mais propensas a ter maior acoplamento):</b> O gráfico de dispersão mostra uma leve tendência positiva.</li>
            <li><b>H2 (O acoplamento tem correlação com o tamanho):</b> A correlação de Spearman de <strong>{spearman_br}</strong> indica uma correlação positiva fraca.</li>
        </ol>
        <p>Concluímos que há uma relação estatística, mas fraca, entre o tamanho e o acoplamento das classes nos projetos analisados.</p>
        """

    # <-- ALTERAÇÃO: Nova seção de introdução
    intro_section = f"""
    <section id="intro">
        <h2>1. Introdução</h2>
        <p>Este relatório apresenta uma análise da relação entre duas importantes métricas de qualidade de software: <b>Tamanho da Classe</b> (medido por Linhas de Código, ou LOC) e <b>Acoplamento Entre Objetos</b> (CBO). O objetivo é investigar se classes maiores tendem a ser mais acopladas a outras classes no sistema.</p>
        <p>Os dados utilizados nesta análise foram coletados de forma automatizada por um pipeline que executou os seguintes passos:</p>
        <ol>
            <li><b>Seleção de Repositórios:</b> O script buscou na API do GitHub os 1.000 repositórios Java com o maior número de estrelas.</li>
            <li><b>Clonagem Local:</b> Cada um dos repositórios selecionados foi clonado para um ambiente local.</li>
            <li><b>Extração de Métricas:</b> A ferramenta de análise estática <b>CK (Chidamber & Kemerer)</b> foi executada sobre o código-fonte de cada projeto para extrair um conjunto de métricas de qualidade em nível de classe.</li>
            <li><b>Consolidação dos Dados:</b> As métricas de todas as classes dos projetos foram agregadas em um único arquivo CSV, que serve como base para este estudo.</li>
        </ol>
        <p>No total, foram analisadas classes de <strong>{repo_count} repositórios Java distintos</strong>, fornecendo um conjunto de dados abrangente para a investigação.</p>
    </section>
    """

    # Template HTML com a nova seção e renumeração
    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório Lab02S02</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body {{ font-family: sans-serif; padding: 2em; }}
            .container {{ max-width: 960px; }}
            h1, h2 {{ color: #333; border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-top: 20px; }}
            img {{ max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 5px; margin-top: 15px; }}
            .table {{ margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header class="text-center">
                <h1>Lab02S02: Um estudo sobre o acoplamento e o tamanho de classes</h1>
                <p class="lead">Relatório de análise da relação entre as métricas LOC e CBO.</p>
            </header>

            {intro_section}

            <section id="stats">
                <h2>2. Análise Descritiva</h2>
                <p>A tabela a seguir apresenta as estatísticas descritivas para as métricas de CBO e LOC.</p>
                {stats_html}
            </section>

            <section id="correlation">
                <h2>3. Análise de Correlação</h2>
                <p>Foram calculados os coeficientes de correlação de Pearson e Spearman.</p>
                <ul>
                    <li><strong>Correlação de Pearson:</strong> {pearson_br}</li>
                    <li><strong>Correlação de Spearman:</strong> {spearman_br}</li>
                </ul>
                <p><em>A correlação de Spearman é geralmente mais robusta para relações não-lineares e outliers.</em></p>
            </section>
            
            <section id="visualization">
                <h2>4. Visualização Gráfica</h2>
                <p>O gráfico de dispersão abaixo ilustra a relação entre LOC e CBO.</p>
                <img src="data:image/png;base64,{img_base64}" alt="Gráfico de Dispersão LOC vs CBO">
            </section>
            
            <section id="conclusion">
                <h2>5. Conclusão sobre as Hipóteses</h2>
                {conclusion_text}
            </section>

        </div>
    </body>
    </html>
    """

    try:
        with open(OUTPUT_HTML_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"\nRelatório final salvo com sucesso em '{OUTPUT_HTML_FILE}'.")
    except Exception as e:
        print(f"ERRO: Falha ao salvar o relatório HTML: {e}")


# --- 4. BLOCO DE EXECUÇÃO PRINCIPAL ---


def main():
    """Orquestra a execução da análise e geração do relatório."""
    print("== Iniciando Análise do Lab02S02 ==")

    df, repo_count = load_data(INPUT_CSV_FILE)
    if df is None:
        return

    stats = calculate_statistics(df)
    pearson_corr, spearman_corr = perform_correlation_analysis(df)
    img_base64 = create_visualization(df)
    generate_html_report(stats, pearson_corr, spearman_corr, img_base64, repo_count)

    print("\n== Análise Concluída ==")


if __name__ == "__main__":
    main()
