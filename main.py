# pr_dataset_pipeline.py
import os
import requests
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÕES E CONSTANTES ---

# load_dotenv()

# Configurações da API do GitHub
GITHUB_API_URL = "https://api.github.com/graphql"
try:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except KeyError:
    raise Exception(
        "Token não encontrado. Crie um arquivo .env e adicione GITHUB_TOKEN."
    )

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

# Constantes da Lógica de Coleta
REPOS_TO_FETCH = 200
MIN_PR_COUNT = 100
MIN_REVIEW_COUNT = 1
MIN_DURATION_HOURS = 1

# Constantes de Controle da API
PRS_PER_PAGE = 50  # Um bom equilíbrio entre quantidade de dados e tempo de resposta
PAGES_TO_FETCH_REPOS = 5 # Fetch 5 * 100 = 500 repos para garantir que teremos 200 válidos
REPOS_PER_PAGE = 100
MAX_RETRIES = 5
RETRY_DELAY = 5

# Constantes de Saída
FINAL_CSV_FILE = "github_prs_dataset.csv"
RESULT_DIR = "result"


# --- 2. LÓGICA DE COLETA DE DADOS (GraphQL) ---

SEARCH_REPOS_QUERY = """
query SearchPopularRepos($cursor: String, $perPage: Int!) {
  search(query: "stars:>1 sort:stars-desc", type: REPOSITORY, first: $perPage, after: $cursor) {
    pageInfo {
      endCursor
      hasNextPage
    }
    nodes {
      ... on Repository {
        nameWithOwner
        mergedPRs: pullRequests(states: MERGED) {
          totalCount
        }
        closedPRs: pullRequests(states: CLOSED) {
          totalCount
        }
      }
    }
  }
}
"""

SEARCH_PRS_QUERY = """
query SearchPullRequests($owner: String!, $name: String!, $cursor: String, $perPage: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequests(states: [MERGED, CLOSED], first: $perPage, after: $cursor, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo {
        endCursor
        hasNextPage
      }
      nodes {
        number
        title
        state
        createdAt
        mergedAt
        closedAt
        reviews(first: 1) {
          totalCount
        }
      }
    }
  }
}
"""


def run_graphql_query(query, variables):
    """Função genérica para executar uma query GraphQL com lógica de retry."""
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                GITHUB_API_URL,
                headers=HEADERS,
                json={"query": query, "variables": variables},
                timeout=60,
            )
            response.raise_for_status()
            response_data = response.json()
            if "errors" in response_data:
                print(f"ERRO GraphQL: {response_data['errors']}")
                return None
            return response_data
        except requests.RequestException as e:
            print(
                f"ERRO de requisição: {e}. Tentando novamente... (Tentativa {attempt + 1}/{MAX_RETRIES})"
            )
            time.sleep(RETRY_DELAY * (attempt + 1))
    print(f"ERRO FATAL: Falha na query GraphQL após {MAX_RETRIES} tentativas.")
    return None


def parse_datetime(date_string):
    """Converte uma string de data ISO 8601 para um objeto datetime ciente do fuso horário."""
    if not date_string:
        return None
    return datetime.fromisoformat(date_string.replace("Z", "+00:00"))


def fetch_popular_repos_with_prs_filter():
    """Busca repositórios populares e os filtra pela contagem mínima de PRs."""
    print(f"--- ETAPA 1: Buscando e filtrando os {REPOS_TO_FETCH} repositórios mais populares ---")
    qualified_repos = []
    cursor = None

    for page_num in range(1, PAGES_TO_FETCH_REPOS + 1):
        print(f"Buscando página de repositórios {page_num}/{PAGES_TO_FETCH_REPOS}...")
        variables = {"cursor": cursor, "perPage": REPOS_PER_PAGE}
        response_data = run_graphql_query(SEARCH_REPOS_QUERY, variables)

        if not response_data or "data" not in response_data:
            break

        search_results = response_data.get("data", {}).get("search", {})
        repos = search_results.get("nodes", [])

        for repo in repos:
            if not repo:
                continue
            
            total_prs = repo["mergedPRs"]["totalCount"] + repo["closedPRs"]["totalCount"]
            if total_prs >= MIN_PR_COUNT:
                qualified_repos.append(repo["nameWithOwner"])
                print(f"  [+] Repositório qualificado: {repo['nameWithOwner']} ({total_prs} PRs). Coletados: {len(qualified_repos)}/{REPOS_TO_FETCH}")
                if len(qualified_repos) >= REPOS_TO_FETCH:
                    break
        
        if len(qualified_repos) >= REPOS_TO_FETCH:
            break
        
        page_info = search_results.get("pageInfo", {})
        cursor = page_info.get("endCursor")
        if not page_info.get("hasNextPage"):
            print("INFO: API informou que não há mais páginas de repositórios.")
            break
        time.sleep(1)

    print(f"Sucesso! {len(qualified_repos)} repositórios qualificados foram encontrados.")
    return qualified_repos


def fetch_valid_prs_for_repo(repo_name):
    """Busca e filtra os PRs de um único repositório de acordo com os critérios."""
    valid_prs = []
    owner, name = repo_name.split("/")
    cursor = None
    
    print(f"  Analisando PRs para {repo_name}...")

    while True:
        variables = {"owner": owner, "name": name, "cursor": cursor, "perPage": PRS_PER_PAGE}
        response_data = run_graphql_query(SEARCH_PRS_QUERY, variables)

        if not response_data or "data" not in response_data or not response_data["data"].get("repository"):
            break

        prs_data = response_data["data"]["repository"].get("pullRequests", {})
        prs = prs_data.get("nodes", [])

        for pr in prs:
            if not pr:
                continue

            # Filtro 1: Mínimo de 1 revisão
            review_count = pr["reviews"]["totalCount"]
            if review_count < MIN_REVIEW_COUNT:
                continue

            # Filtro 2: Duração mínima de 1 hora
            created_at = parse_datetime(pr["createdAt"])
            
            # O momento final é `mergedAt` para PRs merged, ou `closedAt` para os demais
            final_event_at = parse_datetime(pr["mergedAt"] or pr["closedAt"])

            if not created_at or not final_event_at:
                continue
            
            duration = final_event_at - created_at
            if duration >= timedelta(hours=MIN_DURATION_HOURS):
                valid_prs.append({
                    "repository": repo_name,
                    "pr_number": pr["number"],
                    "title": pr["title"],
                    "state": pr["state"],
                    "review_count": review_count,
                    "created_at": pr["createdAt"],
                    "closed_at": pr["mergedAt"] or pr["closedAt"],
                    "duration_hours": round(duration.total_seconds() / 3600, 2),
                })

        page_info = prs_data.get("pageInfo", {})
        cursor = page_info.get("endCursor")
        if not page_info.get("hasNextPage"):
            break
        # Pequeno delay para não sobrecarregar a API em repositórios com muitos PRs
        time.sleep(0.5)
    
    print(f"  -> Encontrados {len(valid_prs)} PRs válidos para {repo_name}.")
    return valid_prs


# --- 3. BLOCO DE EXECUÇÃO PRINCIPAL ---

def main():
    """Orquestra a pipeline de coleta e agregação de dados de PRs."""
    print("== Pipeline de Criação de Dataset de Pull Requests do GitHub ==")
    os.makedirs(RESULT_DIR, exist_ok=True)

    # Etapa 1: Obter a lista de repositórios que atendem aos critérios
    repo_list = fetch_popular_repos_with_prs_filter()
    if not repo_list:
        print("Nenhum repositório qualificado encontrado. Encerrando.")
        return

    # Etapa 2: Iterar sobre os repositórios e coletar os PRs válidos
    print(f"\n--- ETAPA 2: Coletando PRs de {len(repo_list)} repositórios ---")
    all_prs_data = []
    total_repos = len(repo_list)

    for i, repo_name in enumerate(repo_list):
        print(f"\n[ Processando Repositório {i+1}/{total_repos} ]: {repo_name}")
        try:
            prs_for_repo = fetch_valid_prs_for_repo(repo_name)
            if prs_for_repo:
                all_prs_data.extend(prs_for_repo)
        except Exception as e:
            print(f"ERRO inesperado ao processar {repo_name}: {e}. Pulando.")
            continue
    
    if not all_prs_data:
        print("\nNenhum PR que atenda a todos os critérios foi encontrado.")
        return
        
    # Etapa 3: Consolidar os dados em um único arquivo CSV
    print(f"\n--- ETAPA 3: Consolidando todos os dados em '{FINAL_CSV_FILE}' ---")
    final_df = pd.DataFrame(all_prs_data)
    
    output_path = os.path.join(RESULT_DIR, FINAL_CSV_FILE)
    final_df.to_csv(output_path, index=False, encoding="utf-8")
    
    print(f"Arquivo final '{output_path}' salvo com sucesso!")
    print(f"Total de Pull Requests coletados no dataset: {len(final_df)}")
    print("\nProcesso concluído.")

if __name__ == "__main__":
    main()
