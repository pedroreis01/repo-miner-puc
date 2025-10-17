# pr_dataset_pipeline.py
import os
import requests
import time
import pandas as pd
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# --- 1. CONFIGURAÇÕES E CONSTANTES ---

load_dotenv()

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
# Número máximo de candidatos a repositórios para avaliar
MAX_CANDIDATE_REPOS = 500
# Quantidade alvo de PRs válidos por repositório
TARGET_PRS_PER_REPO = 100
# Número alvo de repositórios que atingem TARGET_PRS_PER_REPO
TARGET_REPOS_COUNT = 201
MIN_PR_COUNT = 50
MIN_REVIEW_COUNT = 1
MIN_DURATION_HOURS = 1

# Constantes de Controle da API
PRS_PER_PAGE = 50  # Um bom equilíbrio entre quantidade de dados e tempo de resposta
# 50 por página x 10 páginas = 500 candidatos
PAGES_TO_FETCH_REPOS = 10
REPOS_PER_PAGE = 50
MAX_RETRIES = 5
RETRY_DELAY = 5

# Constantes de Saída
REPO_LIST_CSV_FILE = "selected_repositories.csv"
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
        changedFiles
        additions
        deletions
        participants {
          totalCount
        }
        comments {
          totalCount
        }
        reviewThreads {
          totalCount
        }
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
    print(
        f"--- ETAPA 1: Buscando e filtrando até {MAX_CANDIDATE_REPOS} repositórios mais populares (mín. {MIN_PR_COUNT} PRs) ---"
    )
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

            total_prs = (
                repo["mergedPRs"]["totalCount"] + repo["closedPRs"]["totalCount"]
            )
            if total_prs >= MIN_PR_COUNT:
                qualified_repos.append(repo["nameWithOwner"])
                print(
                    f"  [+] Repositório qualificado: {repo['nameWithOwner']} ({total_prs} PRs). Coletados: {len(qualified_repos)}/{MAX_CANDIDATE_REPOS}"
                )
                if len(qualified_repos) >= MAX_CANDIDATE_REPOS:
                    break

        if len(qualified_repos) >= MAX_CANDIDATE_REPOS:
            break

        page_info = search_results.get("pageInfo", {})
        cursor = page_info.get("endCursor")
        if not page_info.get("hasNextPage"):
            print("INFO: API informou que não há mais páginas de repositórios.")
            break
        time.sleep(1)

    print(
        f"Sucesso! {len(qualified_repos)} repositórios qualificados foram encontrados (limite {MAX_CANDIDATE_REPOS})."
    )
    return qualified_repos


def fetch_valid_prs_for_repo(repo_name):
    """Busca e filtra os PRs de um único repositório de acordo com os critérios."""
    valid_prs = []
    owner, name = repo_name.split("/")
    cursor = None

    print(f"  Analisando PRs para {repo_name}...")

    while True:
        variables = {
            "owner": owner,
            "name": name,
            "cursor": cursor,
            "perPage": PRS_PER_PAGE,
        }
        response_data = run_graphql_query(SEARCH_PRS_QUERY, variables)

        if (
            not response_data
            or "data" not in response_data
            or not response_data["data"].get("repository")
        ):
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
                # Métricas adicionais da PR
                changed_files = pr.get("changedFiles")
                additions = pr.get("additions")
                deletions = pr.get("deletions")
                participants_count = (
                    pr.get("participants", {}).get("totalCount") if pr.get("participants") else None
                )
                issue_comments_count = (
                    pr.get("comments", {}).get("totalCount") if pr.get("comments") else None
                )
                review_threads_count = (
                    pr.get("reviewThreads", {}).get("totalCount") if pr.get("reviewThreads") else None
                )
                # Comentários totais (issue comments + threads de review)
                comments_total = None
                if issue_comments_count is not None or review_threads_count is not None:
                    comments_total = (issue_comments_count or 0) + (review_threads_count or 0)
                valid_prs.append(
                    {
                        "repository": repo_name,
                        "pr_number": pr["number"],
                        "title": pr["title"],
                        "state": pr["state"],
                        "review_count": review_count,
                        "created_at": pr["createdAt"],
                        "closed_at": pr["mergedAt"] or pr["closedAt"],
                        "duration_hours": round(duration.total_seconds() / 3600, 2),
                        "changed_files": changed_files,
                        "additions": additions,
                        "deletions": deletions,
                        "participants_count": participants_count,
                        "issue_comments_count": issue_comments_count,
                        "review_threads_count": review_threads_count,
                        "comments_total": comments_total,
                    }
                )
                # Se já atingimos o alvo por repositório, encerramos a coleta deste repo
                if len(valid_prs) >= TARGET_PRS_PER_REPO:
                    break

        # Se batemos o limite no meio da página, não precisamos paginar mais
        if len(valid_prs) >= TARGET_PRS_PER_REPO:
            break

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

    # --- ETAPA 1.5: Salvando a lista de {len(repo_list)} repositórios qualificados ---
    print(
        f"\n--- ETAPA 1.5: Salvando a lista de {len(repo_list)} repositórios qualificados ---"
    )
    repo_df = pd.DataFrame(repo_list, columns=["repository_name"])
    repo_output_path = os.path.join(RESULT_DIR, REPO_LIST_CSV_FILE)
    repo_df.to_csv(repo_output_path, index=False, encoding="utf-8")
    print(f"Arquivo de repositórios '{repo_output_path}' salvo com sucesso!")
    # --- FIM DO NOVO BLOCO ---

    # Etapa 2: Iterar sobre os repositórios e coletar PRs válidos, parando quando 201 repositórios atingirem 100 PRs
    print(f"\n--- ETAPA 2: Coletando PRs de até {len(repo_list)} repositórios (alvo: {TARGET_REPOS_COUNT} repos x {TARGET_PRS_PER_REPO} PRs) ---")
    all_prs_data = []
    repos_completed = 0
    total_repos = len(repo_list)

    for i, repo_name in enumerate(repo_list):
        # Pare se já atingimos o total de repositórios desejado
        if repos_completed >= TARGET_REPOS_COUNT:
            print(f"\nAlvo atingido: {repos_completed} repositórios com {TARGET_PRS_PER_REPO} PRs. Encerrando.")
            break

        print(f"\n[ Processando Repositório {i+1}/{total_repos} ]: {repo_name}")
        try:
            prs_for_repo = fetch_valid_prs_for_repo(repo_name)
            if prs_for_repo:
                # Se o repositório atingiu o alvo, só contamos se chegou a 100 PRs
                if len(prs_for_repo) >= TARGET_PRS_PER_REPO:
                    # Garante que apenas 100 sejam adicionados, mesmo que por alguma razão passe do alvo
                    all_prs_data.extend(prs_for_repo[:TARGET_PRS_PER_REPO])
                    repos_completed += 1
                    print(f"  -> Repositório atingiu {TARGET_PRS_PER_REPO} PRs válidos. Total de repositórios completos: {repos_completed}/{TARGET_REPOS_COUNT}")
                else:
                    # Caso não tenha atingido a meta, não conta para o total de repositórios completos
                    print(f"  -> Repositório NÃO atingiu {TARGET_PRS_PER_REPO} PRs válidos (obteve {len(prs_for_repo)}).")
        except Exception as e:
            print(f"ERRO inesperado ao processar {repo_name}: {e}. Pulando.")
            continue

    if not all_prs_data:
        print("\nNenhum PR que atenda a todos os critérios foi encontrado.")
        return

    # Etapa 3: Consolidar os dados em um único arquivo CSV
    print(f"\n--- ETAPA 3: Consolidando todos os dados em '{FINAL_CSV_FILE}' ---")
    final_df = pd.DataFrame(all_prs_data)
    # Garante que a coluna 'title' seja a última no CSV
    if "title" in final_df.columns:
        cols = [c for c in final_df.columns if c != "title"] + ["title"]
        final_df = final_df[cols]

    output_path = os.path.join(RESULT_DIR, FINAL_CSV_FILE)
    final_df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"Arquivo final '{output_path}' salvo com sucesso!")
    print(f"Total de Pull Requests coletados no dataset: {len(final_df)}")
    print("\nProcesso concluído.")


if __name__ == "__main__":
    main()
