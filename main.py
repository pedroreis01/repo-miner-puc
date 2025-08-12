# -*- coding: utf-8 -*-

"""
LAB01 - Coleta de características de repositórios populares do GitHub.

Versão 4: MODO DE DEBUG. Este script foi modificado para imprimir as variáveis
enviadas à API, com o objetivo de diagnosticar o erro 'invalid value' para
a variável '$reposPerPage'.
"""

import os
import requests
import csv
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# MUDANÇA 2: Executar a função que carrega as variáveis do .env para o ambiente
load_dotenv()

# --- Constantes ---
GITHUB_API_URL = "https://api.github.com/graphql"
try:
    # O restante do código funciona sem alterações! os.environ agora "enxerga" o token do .env
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except KeyError:
    # A mensagem de erro continua válida se o token não estiver nem no .env nem no ambiente
    raise Exception(
        "Token não encontrado. Verifique se o arquivo .env existe e contém GITHUB_TOKEN, ou se a variável de ambiente está configurada."
    )

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}
OUTPUT_CSV_FILE = "repositorios.csv"

# --- Parâmetros de Coleta ---
REPOS_PER_PAGE = 20
# MUDANÇA PARA DEBUG: Vamos buscar apenas 2 páginas para um teste rápido.
PAGES_TO_FETCH = 5

# --- Query GraphQL ---
GRAPHQL_QUERY = """
query GetPopularRepos($cursor: String, $reposPerPage: Int!) {
  search(query: "stars:>1", type: REPOSITORY, first: $reposPerPage, after: $cursor) {
    repositoryCount
    pageInfo {
      endCursor
      hasNextPage
    }
    nodes {
      ... on Repository {
        nameWithOwner
        stargazerCount
        createdAt
        pushedAt
        primaryLanguage {
          name
        }
        pullRequests(states: MERGED) {
          totalCount
        }
        releases {
          totalCount
        }
        closedIssues: issues(states: CLOSED) {
          totalCount
        }
        totalIssues: issues {
          totalCount
        }
      }
    }
  }
}
"""


def fetch_repositories():
    """
    Busca os repositórios com instrumentação de debug para as variáveis.
    """
    print("Iniciando a coleta de dados dos repositórios (MODO DE DEBUG)...")
    all_repos = []
    cursor = None

    for page_num in range(1, PAGES_TO_FETCH + 1):
        print(f"\n--- Preparando página {page_num}/{PAGES_TO_FETCH} ---")

        # Cria o dicionário de variáveis que será enviado
        variables_to_send = {"cursor": cursor, "reposPerPage": REPOS_PER_PAGE}

        # MUDANÇA PRINCIPAL: Imprime as variáveis para depuração
        print(f"DEBUG: Variáveis que serão enviadas para a API: {variables_to_send}")

        try:
            response = requests.post(
                GITHUB_API_URL,
                headers=HEADERS,
                json={"query": GRAPHQL_QUERY, "variables": variables_to_send},
                timeout=30,
            )

            # Verifica a resposta independentemente do status para ver se há um JSON de erro
            response_data = response.json()

            if "errors" in response_data:
                print(
                    f"ERRO: A API do GitHub retornou um erro: {response_data['errors']}"
                )
                return None

            # Se não houver erro no JSON, verifica o status HTTP
            response.raise_for_status()

        except requests.RequestException as e:
            print(f"ERRO: A requisição HTTP falhou: {e}")
            return None

        print("INFO: Requisição bem-sucedida para esta página.")
        search_results = response_data.get("data", {}).get("search", {})
        repos = search_results.get("nodes", [])
        all_repos.extend(repos)

        page_info = search_results.get("pageInfo", {})
        cursor = page_info.get("endCursor")

        if not page_info.get("hasNextPage"):
            print("INFO: API informou que não há mais páginas. Encerrando a coleta.")
            break

    print(f"\nColeta finalizada. Total de {len(all_repos)} repositórios obtidos.")
    return all_repos


def process_data(repositories):
    """Processa a lista de repositórios para calcular métricas e limpar os dados."""
    print("Processando dados coletados...")
    # (O restante desta função e das outras permanece o mesmo)
    processed_list = []
    now = datetime.now(timezone.utc)
    for repo in repositories:
        if not repo:
            continue
        total_issues = repo.get("totalIssues", {}).get("totalCount", 0)
        closed_issues = repo.get("closedIssues", {}).get("totalCount", 0)
        created_at_str = repo.get("createdAt")
        age_days = (
            (now - datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))).days
            if created_at_str
            else 0
        )
        pushed_at_str = repo.get("pushedAt")
        last_update_days = (
            (now - datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))).days
            if pushed_at_str
            else 0
        )
        closed_issues_ratio = closed_issues / total_issues if total_issues > 0 else 0
        processed_repo = {
            "nome_repositorio": repo.get("nameWithOwner"),
            "estrelas": repo.get("stargazerCount"),
            "linguagem_primaria": (
                repo.get("primaryLanguage", {}).get("name")
                if repo.get("primaryLanguage")
                else "N/A"
            ),
            "idade_dias": age_days,
            "dias_desde_ultimo_push": last_update_days,
            "total_pull_requests_aceitas": repo.get("pullRequests", {}).get(
                "totalCount", 0
            ),
            "total_releases": repo.get("releases", {}).get("totalCount", 0),
            "total_issues": total_issues,
            "issues_fechadas": closed_issues,
            "razao_issues_fechadas": f"{closed_issues_ratio:.4f}",
        }
        processed_list.append(processed_repo)
    print("Processamento de dados concluído.")
    return processed_list


def save_to_csv(data, filename):
    """Salva os dados processados em um arquivo CSV."""
    if not data:
        print("Nenhum dado para salvar.")
        return
    print(f"Salvando dados em '{filename}'...")
    headers = data[0].keys()
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        print(f"Arquivo '{filename}' salvo com sucesso!")
    except IOError as e:
        print(f"Erro ao salvar o arquivo CSV: {e}")


# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    raw_repos = fetch_repositories()
    if raw_repos:
        processed_repos = process_data(raw_repos)
        save_to_csv(processed_repos, OUTPUT_CSV_FILE)
    else:
        print(
            "\nNenhum repositório foi coletado devido a um erro. O script será encerrado."
        )
