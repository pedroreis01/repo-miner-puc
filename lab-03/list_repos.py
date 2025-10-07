import pandas as pd

# Caminho para o seu arquivo CSV foi atualizado aqui
file_path = (
    "C:/Users/Pedro/Desktop/Lab/repo-miner-puc/lab-03/result/github_prs_dataset.csv"
)

try:
    # Lê o arquivo CSV para um DataFrame do pandas
    df = pd.read_csv(file_path)

    # 1. Seleciona a coluna 'repository'
    # 2. Usa o método .unique() para obter apenas os nomes sem repetição
    # 3. Converte o resultado para uma lista Python
    unique_repositories = df["repository"].unique().tolist()

    print(f"Repositórios únicos encontrados em '{file_path}':")
    print("-" * 40)  # Adiciona uma linha para separar

    # Itera sobre a lista de repositórios únicos e imprime cada um
    for repo in unique_repositories:
        print(repo)

except FileNotFoundError:
    print(f"ERRO: O arquivo não foi encontrado no caminho especificado: '{file_path}'")
    print("Verifique se o script está sendo executado da pasta correta.")
except KeyError:
    print(f"ERRO: A coluna 'repository' não foi encontrada no arquivo CSV.")
    print("Verifique se o cabeçalho do seu CSV está correto.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
