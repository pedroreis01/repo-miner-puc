# coleta_graphql.py
import os
import requests
import csv
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# --- Constantes e Configurações ---
GITHUB_API_URL = "https://api.github.com/graphql"
try:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except KeyError:
    raise Exception(
        "Token não encontrado. Verifique se o arquivo .env existe e contém GITHUB_TOKEN."
    )

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}
OUTPUT_CSV_FILE = "repositorios_graphql_completo.csv"
REPOS_PER_PAGE = 100
PAGES_TO_FETCH = 10
MAX_RETRIES = 3
RETRY_DELAY = 5

# --- MUDANÇA: Query dividida em duas para maior robustez ---

# Query 1: Busca "leve" para obter a lista de repositórios
SEARCH_REPOS_QUERY = """
query SearchPopularRepos($cursor: String, $reposPerPage: Int!) {
  search(query: "stars:>=1 sort:stars-desc", type: REPOSITORY, first: $reposPerPage, after: $cursor) {
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
      }
    }
  }
}
"""

# Query 2: Busca "pesada" para obter detalhes de UM repositório por vez
GET_REPO_DETAILS_QUERY = """
query GetRepoDetails($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
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
"""


def run_query(query, variables):
    """Função genérica para executar uma query com lógica de retry."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GITHUB_API_URL,
                headers=HEADERS,
                json={"query": query, "variables": variables},
                timeout=45,
            )
            if 500 <= response.status_code < 600:
                print(
                    f"AVISO: Recebido status {response.status_code}. Tentando novamente em {RETRY_DELAY}s... (Tentativa {attempt + 1}/{MAX_RETRIES})"
                )
                time.sleep(
                    RETRY_DELAY * (attempt + 1)
                )  # Aumenta o delay a cada tentativa
                continue

            response.raise_for_status()
            response_data = response.json()

            if "errors" in response_data:
                print(f"ERRO GraphQL: {response_data['errors']}")
                return None

            return response_data

        except requests.RequestException as e:
            print(
                f"ERRO de requisição: {e}. Tentando novamente em {RETRY_DELAY}s... (Tentativa {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY * (attempt + 1))

    print(f"ERRO FATAL: Falha na query após {MAX_RETRIES} tentativas.")
    return None


def fetch_repo_list():
    """Etapa 1: Busca a lista de 1000 repositórios com dados básicos."""
    print("--- ETAPA 1: Buscando a lista de 1000 repositórios ---")
    all_repos = []
    cursor = None
    for page_num in range(1, PAGES_TO_FETCH + 1):
        print(f"Buscando página de repositórios {page_num}/{PAGES_TO_FETCH}...")
        variables = {"cursor": cursor, "reposPerPage": REPOS_PER_PAGE}
        response_data = run_query(SEARCH_REPOS_QUERY, variables)

        if not response_data:
            return None  # Falha na busca da lista

        search_results = response_data.get("data", {}).get("search", {})
        repos = search_results.get("nodes", [])
        all_repos.extend(repos)

        page_info = search_results.get("pageInfo", {})
        cursor = page_info.get("endCursor")

        if not page_info.get("hasNextPage"):
            print(
                "INFO: API informou que não há mais páginas. Encerrando busca da lista."
            )
            break
        time.sleep(1)

    print(f"Sucesso! Lista com {len(all_repos)} repositórios coletada.")
    return all_repos


def fetch_all_repo_details(repo_list):
    """Etapa 2: Itera sobre a lista e busca os detalhes de cada repositório."""
    print("\n--- ETAPA 2: Buscando detalhes para cada repositório ---")
    detailed_repos = []
    total_repos = len(repo_list)
    for i, basic_repo_info in enumerate(repo_list):
        if not basic_repo_info:
            continue

        full_name = basic_repo_info.get("nameWithOwner")
        if not full_name or "/" not in full_name:
            print(f"AVISO: Repositório inválido ou sem nome na posição {i+1}. Pulando.")
            continue

        owner, name = full_name.split("/")
        print(f"Buscando detalhes de [{i+1}/{total_repos}]: {full_name}...")

        variables = {"owner": owner, "name": name}
        details_data = run_query(GET_REPO_DETAILS_QUERY, variables)

        if details_data:
            repo_details = details_data.get("data", {}).get("repository", {})
            # Combina os dados básicos com os detalhes
            combined_info = {**basic_repo_info, **repo_details}
            detailed_repos.append(combined_info)
        else:
            print(
                f"AVISO: Falha ao buscar detalhes para {full_name}. Repositório será pulado."
            )

        time.sleep(0.5)  # Pausa para não sobrecarregar a API

    return detailed_repos


def process_and_save_data(repositories, filename):
    """Processa os dados combinados e salva em um arquivo CSV."""
    if not repositories:
        print("Nenhum dado para processar ou salvar.")
        return

    print(f"\n--- ETAPA 3: Processando dados e salvando em '{filename}' ---")
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
            "razao_issues_fechadas": closed_issues_ratio,
        }
        processed_list.append(processed_repo)
    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            headers = processed_list[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(processed_list)
        print(f"Arquivo '{filename}' salvo com sucesso!")
    except (IOError, IndexError) as e:
        print(f"Erro ao salvar o arquivo CSV: {e}")


# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    # Etapa 1
    basic_repo_list = fetch_repo_list()

    if basic_repo_list:
        # Etapa 2
        full_repo_data = fetch_all_repo_details(basic_repo_list)
        # Etapa 3
        if full_repo_data:
            process_and_save_data(full_repo_data, OUTPUT_CSV_FILE)
