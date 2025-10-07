# java_metrics_pipeline_final.py
import os
import requests
import csv
import time
import shutil
import subprocess
import sys
import pandas as pd
import stat
from datetime import datetime, timezone
from dotenv import load_dotenv
from git import Repo

# --- 1. CONFIGURAÇÕES E CONSTANTES ---

load_dotenv()

# Configurações da API do GitHub
GITHUB_API_URL = "https://api.github.com/graphql"
try:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except KeyError:
    raise Exception(
        "Token não encontrado. Verifique se o arquivo .env existe e contém GITHUB_TOKEN."
    )

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
REPOS_PER_PAGE = 100  # Agora esta constante será usada corretamente
PAGES_TO_FETCH = 10
MAX_RETRIES = 3
RETRY_DELAY = 5

REPOS_BASE_DIR = "cloned_repos"
CK_JAR_PATH = os.path.join("CK", "ck-0.7.0.jar")
FINAL_CSV_FILE = "all_java_projects_class_metrics.csv"
RESULT_BASE_PATH = "result"


def remove_readonly(func, path, _):
    """Error handler para shutil.rmtree."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


# --- 2. LÓGICA DE COLETA DE DADOS (GraphQL) ---

# --- ALTERAÇÃO: A query agora aceita a variável $perPage ---
SEARCH_JAVA_REPOS_QUERY = """
query SearchPopularJavaRepos($cursor: String, $perPage: Int!) {
  search(query: "language:Java sort:stars-desc", type: REPOSITORY, first: $perPage, after: $cursor) {
    pageInfo { endCursor, hasNextPage }
    nodes { ... on Repository { nameWithOwner } }
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
                timeout=45,
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


def fetch_top_java_repos():
    """Busca a lista dos 1000 repositórios Java mais populares."""
    print("--- ETAPA 1: Buscando a lista de repositórios Java no GitHub ---")
    all_repos = []
    cursor = None
    for page_num in range(1, PAGES_TO_FETCH + 1):
        print(f"Buscando página de repositórios {page_num}/{PAGES_TO_FETCH}...")

        # --- ALTERAÇÃO: Passando a constante REPOS_PER_PAGE para a query ---
        variables = {"cursor": cursor, "perPage": REPOS_PER_PAGE}
        response_data = run_graphql_query(SEARCH_JAVA_REPOS_QUERY, variables)

        if not response_data:
            break
        search_results = response_data.get("data", {}).get("search", {})
        all_repos.extend(
            repo["nameWithOwner"] for repo in search_results.get("nodes", []) if repo
        )
        page_info = search_results.get("pageInfo", {})
        cursor = page_info.get("endCursor")
        if not page_info.get("hasNextPage"):
            print("INFO: API informou que não há mais páginas.")
            break
        time.sleep(1)
    print(f"Sucesso! Lista com {len(all_repos)} repositórios coletada.")
    return all_repos


# --- 3. LÓGICA DE ANÁLISE (CK TOOL) ---


def clone_repo_if_not_exists(repo_url, dest_dir):
    """Clona um repositório apenas se o diretório de destino não existir."""
    if os.path.exists(dest_dir):
        print(f"Repositório já existe em '{dest_dir}'. Pulando clone.")
        return
    print(f"Clonando repositório de {repo_url} para '{dest_dir}'...")
    Repo.clone_from(repo_url, dest_dir, depth=1)


def run_ck(jar_path, repo_dir, output_dir):
    """Executa o CK Tool e retorna o caminho para o class.csv."""
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, onerror=remove_readonly)
    os.makedirs(output_dir)

    print(f"Executando CK Tool no diretório '{repo_dir}'...")
    cmd = ["java", "-jar", jar_path, repo_dir, "true", "0", "true", output_dir + os.sep]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o CK: {e.stderr}")
        return None
    class_csv_path = os.path.join(output_dir, "class.csv")
    if not os.path.exists(class_csv_path):
        print("Aviso: class.csv não foi gerado pelo CK.")
        return None
    return class_csv_path


# --- 4. BLOCO DE EXECUÇÃO PRINCIPAL ---


def main():
    """Orquestra a pipeline de coleta, análise e agregação."""
    print("== Pipeline de Extração de Métricas CK para Projetos Java ==")

    os.makedirs(REPOS_BASE_DIR, exist_ok=True)

    if not os.path.exists(CK_JAR_PATH):
        print(f"Erro: CK JAR não encontrado em '{CK_JAR_PATH}'.")
        sys.exit(1)

    repo_list = fetch_top_java_repos()
    if not repo_list:
        print("Nenhum repositório encontrado. Encerrando.")
        return

    print(f"\n--- ETAPA 2: Analisando {len(repo_list)} repositórios com o CK Tool ---")
    all_metrics_dfs = []
    total_repos = len(repo_list)

    for i, repo_name in enumerate(repo_list):
        print(f"\n[ Processando {i+1}/{total_repos} ]: {repo_name}")
        repo_url = f"https://github.com/{repo_name}.git"

        folder_name = repo_name.replace("/", "_")
        repo_path = os.path.join(REPOS_BASE_DIR, folder_name)

        ck_output_path = os.path.join(RESULT_BASE_PATH, folder_name + "_ck_output")

        try:
            clone_repo_if_not_exists(repo_url, repo_path)
            class_csv_path = run_ck(CK_JAR_PATH, repo_path, ck_output_path)

            if class_csv_path:
                df_class = pd.read_csv(class_csv_path)
                df_class["repository"] = repo_name
                all_metrics_dfs.append(df_class)
                print(f"Sucesso! {len(df_class)} classes analisadas para {repo_name}.")
            else:
                print(f"AVISO: Falha na análise do repositório {repo_name}. Pulando.")

        except Exception as e:
            print(f"ERRO inesperado ao processar {repo_name}: {e}. Pulando.")
            continue

    if not all_metrics_dfs:
        print("\nNenhuma métrica foi extraída com sucesso. Nenhum arquivo foi gerado.")
        return

    print(f"\n--- ETAPA 3: Consolidando todos os dados em '{FINAL_CSV_FILE}' ---")
    final_df = pd.concat(all_metrics_dfs, ignore_index=True)
    cols = ["repository"] + [col for col in final_df.columns if col != "repository"]
    final_df = final_df[cols]
    final_df.to_csv(
        RESULT_BASE_PATH + "/" + FINAL_CSV_FILE, index=False, encoding="utf-8"
    )
    print(f"Arquivo final '{FINAL_CSV_FILE}' salvo com sucesso!")
    print(f"Total de classes analisadas em todos os repositórios: {len(final_df)}")
    print(
        "\nProcesso concluído. Os repositórios clonados foram mantidos na pasta 'cloned_repos'."
    )


if __name__ == "__main__":
    main()
