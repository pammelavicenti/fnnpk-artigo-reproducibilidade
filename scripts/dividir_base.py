from pathlib import Path
from collections import defaultdict, Counter
import csv
import hashlib
import os
import random
import shutil

BASE = Path(
    os.environ.get(
        "FNNPK_PREPARACAO",
        Path(__file__).resolve().parent.parent / "FNNPK_preparacao",
    )
)
DESTINO = BASE / "divisao_agrupada"
SEMENTE = 123

# Agrupamentos provisórios definidos pela inspeção visual.
GRUPOS_VISUAIS = {
    "def_k": [
        ["k_20.png", "k_21.png", "k_22.png", "k_23.png", "k_24.png"],
    ],
    "def_n": [
        ["n_18.png", "n_19.png", "n_20.png"],
        ["n_37.png", "n_38.png", "n_39.png"],
        ["n_46.png", "n_47.png", "n_48.png", "n_49.png"],
    ],
    "def_p": [
        ["p60.png", "p61.png", "p62.png", "p63.png", "p64.png"],
        ["p65.png", "p66.png", "p67.png", "p68.png"],
    ],
    "fn": [],
}


def nome_original(caminho):
    # Funciona também se o manifesto contiver barras do Windows.
    return caminho.replace("\\", "/").rsplit("/", 1)[-1]


def selecionar_grupos(grupos, alvo, rng):
    """Seleciona grupos inteiros cuja soma fica próxima do alvo."""
    ordem = sorted(grupos)
    rng.shuffle(ordem)

    possibilidades = {0: ()}
    for grupo_id in ordem:
        tamanho = len(grupos[grupo_id])
        for total, escolhidos in list(possibilidades.items()):
            novo_total = total + tamanho
            if novo_total not in possibilidades:
                possibilidades[novo_total] = escolhidos + (grupo_id,)

    tamanho_total = sum(len(itens) for itens in grupos.values())

    # Reserva pelo menos um grupo para a próxima partição.
    candidatos = [
        total for total in possibilidades
        if 0 < total < tamanho_total
    ]
    if not candidatos:
        raise ValueError("Não há grupos suficientes para separar os conjuntos.")

    melhor_total = min(
        candidatos,
        key=lambda total: (abs(total - alvo), total),
    )
    return set(possibilidades[melhor_total])


manifesto = BASE / "manifesto.csv"
if not manifesto.is_file():
    raise FileNotFoundError(f"Manifesto não encontrado: {manifesto}")

if DESTINO.exists():
    raise FileExistsError(
        f"A pasta já existe: {DESTINO}\n"
        "Nenhum arquivo foi sobrescrito."
    )

with manifesto.open(encoding="utf-8-sig", newline="") as arquivo:
    registros = list(csv.DictReader(arquivo))

por_classe = defaultdict(list)
hashes = set()

# Confere os arquivos antes de criar qualquer saída.
for registro in registros:
    classe = registro["classe"]
    if classe not in GRUPOS_VISUAIS:
        raise ValueError(f"Classe inesperada: {classe}")

    origem = BASE / registro["arquivo_copiado"]
    if not origem.is_file():
        raise FileNotFoundError(origem)

    sha256 = hashlib.sha256(origem.read_bytes()).hexdigest()
    if sha256 != registro["sha256"]:
        raise ValueError(f"Arquivo alterado após a preparação: {origem}")
    if sha256 in hashes:
        raise ValueError(f"Cópia idêntica encontrada: {origem}")

    hashes.add(sha256)
    registro["nome_original"] = nome_original(registro["arquivo_original"])
    por_classe[classe].append(registro)

rng = random.Random(SEMENTE)
resultado = []

for classe in sorted(por_classe):
    itens = por_classe[classe]
    nomes_disponiveis = {item["nome_original"] for item in itens}
    mapa_visual = {}

    for numero, nomes in enumerate(GRUPOS_VISUAIS[classe], start=1):
        grupo_id = f"{classe}_visual_{numero:02d}"
        for nome in nomes:
            if nome not in nomes_disponiveis:
                raise ValueError(f"Imagem do grupo não encontrada: {classe}/{nome}")
            if nome in mapa_visual:
                raise ValueError(f"Imagem em dois grupos: {classe}/{nome}")
            mapa_visual[nome] = grupo_id

    grupos = defaultdict(list)
    for item in itens:
        nome = item["nome_original"]
        grupo_id = mapa_visual.get(nome, f"{classe}_individual_{nome}")
        item["grupo_id"] = grupo_id
        item["criterio_grupo"] = (
            "semelhanca_visual_provisoria"
            if nome in mapa_visual
            else "sem_agrupamento_identificado"
        )
        grupos[grupo_id].append(item)

    # Aproximadamente 70% treino, 15% validação e 15% teste.
    # Os grupos são indivisíveis; por isso as proporções podem variar.
    alvo = max(1, round(len(itens) * 0.15))
    grupos_teste = selecionar_grupos(grupos, alvo, rng)
    restantes = {
        chave: valor for chave, valor in grupos.items()
        if chave not in grupos_teste
    }
    grupos_validacao = selecionar_grupos(restantes, alvo, rng)

    for grupo_id, membros in grupos.items():
        if grupo_id in grupos_teste:
            particao = "test"
        elif grupo_id in grupos_validacao:
            particao = "val"
        else:
            particao = "train"

        for item in membros:
            item["particao"] = particao
            resultado.append(item)

# Confere se algum grupo aparece em mais de uma partição.
particoes_por_grupo = defaultdict(set)
for item in resultado:
    particoes_por_grupo[item["grupo_id"]].add(item["particao"])

if any(len(particoes) != 1 for particoes in particoes_por_grupo.values()):
    raise RuntimeError("Um grupo foi distribuído entre partições.")

DESTINO.mkdir()
linhas_manifesto = []

for item in resultado:
    origem = BASE / item["arquivo_copiado"]
    relativo = Path(item["particao"]) / item["classe"] / origem.name
    destino = DESTINO / relativo
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origem, destino)

    linhas_manifesto.append({
        "classe": item["classe"],
        "arquivo_original": item["arquivo_original"],
        "arquivo_preparado": item["arquivo_copiado"],
        "grupo_id": item["grupo_id"],
        "criterio_grupo": item["criterio_grupo"],
        "particao": item["particao"],
        "arquivo_divisao": relativo.as_posix(),
        "sha256": item["sha256"],
        "semente_divisao": SEMENTE,
    })

with (DESTINO / "manifesto_divisao.csv").open(
    "w", encoding="utf-8-sig", newline=""
) as arquivo:
    escritor = csv.DictWriter(
        arquivo, fieldnames=list(linhas_manifesto[0])
    )
    escritor.writeheader()
    escritor.writerows(linhas_manifesto)

contagens = Counter(
    (item["classe"], item["particao"]) for item in resultado
)

print(f"\nDivisão concluída. Semente: {SEMENTE}")
print(f"{'Classe':<12} {'Treino':>7} {'Validação':>10} {'Teste':>7}")
for classe in sorted(por_classe):
    print(
        f"{classe:<12}"
        f"{contagens[classe, 'train']:>7}"
        f"{contagens[classe, 'val']:>10}"
        f"{contagens[classe, 'test']:>7}"
    )

print(f"\nTotal: {len(resultado)} imagens originais.")
print(f"Saída: {DESTINO}")
print("Grupos registrados sem sobreposição entre partições.")
print("Nenhuma imagem aumentada foi criada.")
