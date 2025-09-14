import os
import subprocess
import requests
import pandas as pd
import time

# ==============
# CONFIGURAÇÕES
# ==============
# O token deve ser mantido privado.
# Em ambientes de produção, use variáveis de ambiente.
TOKEN = ""
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
graphql_url = "https://api.github.com/graphql"

# O arquivo ck.jar deve estar na mesma pasta deste script.
CK_JAR = "ck.jar"

# Pasta onde os repositórios serão clonados.
REPOS_DIR = "repositorios_java"
os.makedirs(REPOS_DIR, exist_ok=True)

# ==============
# CONSULTA GRAPHQL E COLETA DE REPOSITÓRIOS
# ==============
query = """
query ($cursor: String) {
  search(query: "language:Java stars:>0 sort:stars-desc", type: REPOSITORY, first: 25, after: $cursor) {
    pageInfo {
      endCursor
      hasNextPage
    }
    edges {
      node {
        ... on Repository {
          id
          full_name: nameWithOwner
          html_url: url
          stargazers_count: stargazerCount
          created_at: createdAt
          updated_at: updatedAt
          primaryLanguage {
            name
          }
          releases {
            totalCount
          }
        }
      }
    }
  }
}
"""

# Inicializa a lista de repositórios para evitar NameError.
repositorios = []
cursor = None

for i in range(40):  # Para coletar até 1000 repositórios (40 * 25).
    print(f"Coletando dados... Página {i+1}")
    try:
        response = requests.post(graphql_url, headers=HEADERS, json={"query": query, "variables": {"cursor": cursor}})
        response.raise_for_status()  # Lança um erro para status HTTP 4xx/5xx.
        data = response.json()
        
        if "errors" in data:
            print("Erro na resposta da API:", data["errors"])
            break
        
        search_data = data["data"]["search"]
        
        for edge in search_data["edges"]:
            repo = edge["node"]
            primary_language = repo["primaryLanguage"]["name"] if repo["primaryLanguage"] else ""
            repositorios.append({
                "id": repo["id"],
                "full_name": repo["full_name"],
                "html_url": repo["html_url"],
                "stargazers_count": repo["stargazers_count"],
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
                "primary_language": primary_language,
                "releases": repo["releases"]["totalCount"]
            })

        cursor = search_data["pageInfo"]["endCursor"]
        if not search_data["pageInfo"]["hasNextPage"]:
            break
        
        time.sleep(2)  # Pausa para evitar limites de rate da API.

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição da API: {e}")
        break

# Salva a lista de repositórios se a coleta for bem-sucedida.
if repositorios:
    df = pd.DataFrame(repositorios)
    df.to_csv("github_top_1000_java.csv", index=False)
    print("Lista de repositórios salva em 'github_top_1000_java.csv'.")
    
    # ==============
    # CLONAR 1 REPOSITÓRIO (exemplo: o primeiro da lista)
    # ==============
    primeiro_repo = repositorios[0]["full_name"]
    repo_url = f"https://github.com/{primeiro_repo}.git"
    repo_path = os.path.join(REPOS_DIR, primeiro_repo.replace("/", "_"))

    if not os.path.exists(repo_path):
        print(f"Clonando repositório {primeiro_repo}...")
        subprocess.run(["git", "clone", repo_url, repo_path])
    
    # ==============
    # RODAR CK NO REPOSITÓRIO
    # ==============
    print("Executando CK...")
    
    # Define o caminho de saída para o CSV na raiz do projeto.
    ck_output_csv = "ck_results.csv"

    try:
        # A nova ordem de parâmetros deve funcionar com a versão jar-with-dependencies.
        subprocess.run([
            "java", "-jar", CK_JAR, repo_path, ck_output_csv
        ], check=True)
        print(f"Métricas salvas em: {ck_output_csv}")
    except FileNotFoundError:
        print(f"Erro: O arquivo '{CK_JAR}' não foi encontrado. Verifique o caminho.")
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o CK: {e}")
else:
    print("Não foi possível coletar repositórios para análise.")