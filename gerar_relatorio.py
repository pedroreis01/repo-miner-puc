import pandas as pd
import io
import base64
import matplotlib.pyplot as plt
import seaborn as sns
import locale


def df_to_html_table(df, title):
    """Converte um DataFrame do pandas em uma tabela HTML estilizada."""
    # Formata os números no DataFrame para o padrão brasileiro
    df_formatted = df.copy()
    for col in df_formatted.columns:
        if pd.api.types.is_numeric_dtype(df_formatted[col]):
            df_formatted[col] = df_formatted[col].apply(
                lambda x: (
                    locale.format_string("%.2f", x, grouping=True)
                    if pd.notnull(x)
                    else ""
                )
            )

    return f"""
    <div class="table-container">
        <h3>{title}</h3>
        {df_formatted.to_html(classes='styled-table', index=True, float_format='{:.2f}'.format)}
    </div>
    """


def plot_to_base64_html(plot_function):
    """Executa uma função de plotagem e retorna a imagem como uma tag HTML base64."""
    img_buffer = io.BytesIO()
    plot_function(img_buffer)
    img_buffer.seek(0)
    img_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")
    img_buffer.close()
    return f'<img src="data:image/png;base64,{img_base64}" alt="Gráfico da Análise">'


def create_report(df):
    """Gera o conteúdo HTML completo do relatório a partir do DataFrame."""

    # --- Análises para cada RQ ---

    # RQ1: Idade do repositório
    rq1_stats = df["idade_dias"].describe().to_frame().T

    def plot_rq1(buf):
        plt.figure(figsize=(10, 6))
        sns.histplot(df["idade_dias"], bins=30, kde=True)
        plt.title("RQ1: Distribuição da Idade dos Repositórios (em dias)")
        plt.xlabel("Idade (dias)")
        plt.ylabel("Frequência (Nº de Repositórios)")
        mean_val = df["idade_dias"].mean()
        plt.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f'Média: {locale.format_string("%.0f", mean_val, grouping=True)}',
        )
        plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # RQ2: Total de pull requests aceitas
    rq2_stats = df["total_pull_requests_aceitas"].describe().to_frame().T

    def plot_rq2(buf):
        plt.figure(figsize=(10, 6))
        sns.histplot(df["total_pull_requests_aceitas"], bins=30, kde=True)
        plt.title("RQ2: Distribuição de Pull Requests Aceitas")
        plt.xlabel("Total de Pull Requests")
        plt.ylabel("Frequência (Nº de Repositórios)")
        mean_val = df["total_pull_requests_aceitas"].mean()
        plt.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f'Média: {locale.format_string("%.0f", mean_val, grouping=True)}',
        )
        plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # RQ3: Total de releases
    rq3_stats = df["total_releases"].describe().to_frame().T

    def plot_rq3(buf):
        plt.figure(figsize=(10, 6))
        sns.histplot(df["total_releases"], bins=30, kde=True)
        plt.title("RQ3: Distribuição de Releases")
        plt.xlabel("Total de Releases")
        plt.ylabel("Frequência (Nº de Repositórios)")
        mean_val = df["total_releases"].mean()
        plt.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f'Média: {locale.format_string("%.0f", mean_val, grouping=True)}',
        )
        plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # RQ4: Dias desde o último push
    rq4_stats = df["dias_desde_ultimo_push"].describe().to_frame().T

    def plot_rq4(buf):
        plt.figure(figsize=(10, 6))
        sns.histplot(df["dias_desde_ultimo_push"], bins=30, kde=True)
        plt.title("RQ4: Distribuição de Dias Desde a Última Atualização")
        plt.xlabel("Dias desde o último push")
        plt.ylabel("Frequência (Nº de Repositórios)")
        mean_val = df["dias_desde_ultimo_push"].mean()
        plt.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f'Média: {locale.format_string("%.0f", mean_val, grouping=True)}',
        )
        plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # RQ5: Linguagem primária
    rq5_counts = df["linguagem_primaria"].value_counts().nlargest(10).reset_index()
    rq5_counts.columns = ["linguagem", "contagem"]

    def plot_rq5(buf):
        plt.figure(figsize=(12, 8))
        sns.barplot(
            x="contagem", y="linguagem", data=rq5_counts, palette="viridis", orient="h"
        )
        plt.title("RQ5: Top 10 Linguagens de Programação Principais")
        plt.xlabel("Número de Repositórios")
        plt.ylabel("Linguagem")
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # RQ6: Razão de issues fechadas
    rq6_stats = df["razao_issues_fechadas"].describe().to_frame().T

    def plot_rq6(buf):
        plt.figure(figsize=(10, 6))
        sns.histplot(df["razao_issues_fechadas"], bins=20, kde=True)
        plt.title("RQ6: Distribuição da Razão de Issues Fechadas")
        plt.xlabel("Razão (Issues Fechadas / Issues Totais)")
        plt.ylabel("Frequência (Nº de Repositórios)")
        mean_val = df["razao_issues_fechadas"].mean()
        plt.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f'Média: {locale.format_string("%.2f", mean_val, grouping=True)}',
        )
        plt.legend()
        plt.tight_layout()
        plt.savefig(buf, format="png")
        plt.close()

    # --- Montagem do HTML ---

    rq5_table_df = rq5_counts.set_index("linguagem")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Relatório de Análise de Repositórios do GitHub</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f4f4;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 900px;
                margin: auto;
                background: #fff;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 0 15px rgba(0,0,0,0.1);
            }}
            h1, h2 {{
                color: #0366d6;
                border-bottom: 2px solid #eaecef;
                padding-bottom: 10px;
            }}
            h3 {{
                color: #24292e;
            }}
            .student-info {{
                text-align: right;
                margin-bottom: 25px;
                font-size: 1em;
                color: #586069;
            }}
            .rq-section {{
                margin-bottom: 40px;
                padding: 20px;
                background-color: #f9f9f9;
                border-left: 5px solid #0366d6;
                border-radius: 5px;
            }}
            .metric {{
                font-style: italic;
                color: #586069;
                margin-bottom: 20px;
            }}
            .styled-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }}
            .styled-table th, .styled-table td {{
                border: 1px solid #ddd;
                padding: 10px;
                text-align: left;
            }}
            .styled-table th {{
                background-color: #0366d6;
                color: white;
            }}
            .styled-table tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .analysis-container {{
                display: flex;
                flex-wrap: wrap;
                gap: 20px;
                align-items: flex-start;
            }}
            .table-container {{
                flex: 1;
                min-width: 400px;
            }}
            img {{
                max-width: 100%;
                height: auto;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Relatório Final: Características de Repositórios Populares</h1>
            
            <div class="student-info">
                <p><strong>Alunos:</strong> Gabriel Fernandes e Pedro Reis</p>
            </div>
            
            <div class="rq-section">
                <h2>RQ 01. Sistemas populares são maduros/antigos?</h2>
                <p class="metric">Métrica: idade do repositório (em dias)</p>
                <div class="analysis-container">
                    {df_to_html_table(rq1_stats, "Estatísticas Descritivas")}
                    {plot_to_base64_html(plot_rq1)}
                </div>
            </div>

            <div class="rq-section">
                <h2>RQ 02. Sistemas populares recebem muita contribuição externa?</h2>
                <p class="metric">Métrica: total de pull requests aceitas</p>
                <div class="analysis-container">
                    {df_to_html_table(rq2_stats, "Estatísticas Descritivas")}
                    {plot_to_base64_html(plot_rq2)}
                </div>
            </div>

            <div class="rq-section">
                <h2>RQ 03. Sistemas populares lançam releases com frequência?</h2>
                <p class="metric">Métrica: total de releases</p>
                <div class="analysis-container">
                    {df_to_html_table(rq3_stats, "Estatísticas Descritivas")}
                    {plot_to_base64_html(plot_rq3)}
                </div>
            </div>

            <div class="rq-section">
                <h2>RQ 04. Sistemas populares são atualizados com frequência?</h2>
                <p class="metric">Métrica: tempo até a última atualização (em dias)</p>
                <div class="analysis-container">
                    {df_to_html_table(rq4_stats, "Estatísticas Descritivas")}
                    {plot_to_base64_html(plot_rq4)}
                </div>
            </div>

            <div class="rq-section">
                <h2>RQ 05. Sistemas populares são escritos nas linguagens mais populares?</h2>
                <p class="metric">Métrica: linguagem primária de cada repositório</p>
                <div class="analysis-container">
                    {df_to_html_table(rq5_table_df, "Contagem das 10 Linguagens Mais Comuns")}
                    {plot_to_base64_html(plot_rq5)}
                </div>
            </div>

            <div class="rq-section">
                <h2>RQ 06. Sistemas populares possuem um alto percentual de issues fechadas?</h2>
                <p class="metric">Métrica: razão entre número de issues fechadas pelo total de issues</p>
                <div class="analysis-container">
                    {df_to_html_table(rq6_stats, "Estatísticas Descritivas")}
                    {plot_to_base64_html(plot_rq6)}
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    try:
        # Tenta definir o locale para o Brasil.
        # Necessário para formatar números com vírgula decimal.
        try:
            locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
        except locale.Error:
            print(
                "Aviso: Locale 'pt_BR.UTF-8' não encontrado. Usando o locale padrão do sistema."
            )
            # Prossegue com o locale padrão, a formatação pode não ser a ideal.

        # Carregar os dados do arquivo CSV
        df_repos = pd.read_csv("repositorios_graphql_completo.csv")
        print("Arquivo CSV 'repositorios_graphql_completo.csv' carregado com sucesso.")

        # Configurar o estilo dos gráficos
        sns.set_style("whitegrid")

        # Gerar o conteúdo HTML
        report_html = create_report(df_repos)

        # Salvar o relatório em um arquivo HTML
        output_filename = "relatorio_repositorios.html"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(report_html)

        print(
            f"Relatório gerado com sucesso! Abra o arquivo '{output_filename}' no seu navegador."
        )

    except FileNotFoundError:
        print("Erro: O arquivo 'repositorios_graphql_completo.csv' não foi encontrado.")
        print(
            "Por favor, certifique-se de que o arquivo CSV está no mesmo diretório que este script."
        )
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
