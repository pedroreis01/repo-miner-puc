# -*- coding: utf-8 -*-

"""
LAB01 - Coleta de características de repositórios populares do GitHub.

Versão 6: Modificado para usar a API REST em vez de GraphQL.
"""

import os
import requests
import csv
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

# --- Constantes ---
# MUDANÇA: URL aponta para o endpoint de busca da API REST
GITHUB_API_URL = "https://api.github.com/search/repositories"
try:
    GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
except KeyError:
    raise Exception(
        "Token não encontrado. Verifique se o arquivo .env existe e contém GITHUB_TOKEN."
    )

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",  # Cabeçalho padrão para a API REST
}
OUTPUT_CSV_FILE = "top_1000_repositorios_rest_api.csv"

# --- Parâmetros de Coleta ---
REPOS_PER_PAGE = 1000  # A API REST permite no máximo 100 por página
PAGES_TO_FETCH = 1  # 10 páginas de 100 para obter 1000 repositórios


def fetch_repositories():
    """
    Busca os repositórios mais estrelados do GitHub usando a API REST.
    """
    print(
        f"Iniciando a coleta dos {REPOS_PER_PAGE * PAGES_TO_FETCH} repositórios via API REST..."
    )
    all_repos = []

    for page_num in range(1, PAGES_TO_FETCH + 1):
        print(f"\n--- buscando página {page_num}/{PAGES_TO_FETCH} ---")

        # MUDANÇA: Parâmetros de busca para a API REST
        params = {
            "q": "stars:>=1",  # O termo da busca
            "sort": "stars",  # Critério de ordenação
            "order": "desc",  # Ordem decrescente
            "per_page": REPOS_PER_PAGE,
            "page": page_num,
        }

        try:
            # MUDANÇA: Usamos requests.get() com 'params' em vez de post com json
            response = requests.get(
                GITHUB_API_URL,
                headers=HEADERS,
                params=params,
                timeout=30,
            )

            print(f"DEBUG: Status Code: {response.status_code}")
            response.raise_for_status()  # Lança um erro para status como 4xx ou 5xx

            response_data = response.json()

            # MUDANÇA: Na API REST, os resultados estão na chave 'items'
            repos = response_data.get("items", [])
            if not repos:
                print("API não retornou mais itens. Encerrando a coleta.")
                break

            all_repos.extend(repos)

        except requests.RequestException as e:
            print(f"ERRO: A requisição HTTP falhou: {e}")
            return None

        # Pausa para não sobrecarregar a API
        print(f"INFO: Página {page_num} coletada com sucesso. Aguardando 2 segundos...")
        time.sleep(2)

    print(f"\nColeta finalizada. Total de {len(all_repos)} repositórios obtidos.")
    return all_repos


def process_data(repositories):
    """
    Processa a lista de repositórios para calcular métricas e limpar os dados.
    Esta função foi adaptada para o formato de dados da API REST.
    """
    print("Processando dados coletados...")
    processed_list = []
    now = datetime.now(timezone.utc)
    for repo in repositories:
        if not repo:
            continue

        # MUDANÇA: Os nomes das chaves são diferentes na API REST
        created_at_str = repo.get("created_at")
        pushed_at_str = repo.get("pushed_at")

        age_days = (
            (now - datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))).days
            if created_at_str
            else 0
        )
        last_update_days = (
            (now - datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))).days
            if pushed_at_str
            else 0
        )

        processed_repo = {
            "nome_repositorio": repo.get("full_name"),
            "estrelas": repo.get("stargazers_count"),
            "linguagem_primaria": repo.get(
                "language", "N/A"
            ),  # Chave 'language' é mais simples
            "idade_dias": age_days,
            "dias_desde_ultimo_push": last_update_days,
            # ATENÇÃO: Contagens de PRs, Issues e Releases não estão disponíveis neste endpoint.
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
        print("\nNenhum repositório foi coletado. O script será encerrado.")
