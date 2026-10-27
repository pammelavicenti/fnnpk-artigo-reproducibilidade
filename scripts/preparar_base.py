from pathlib import Path
from collections import Counter
import csv
import hashlib
import os
import shutil

RAIZ = Path(__file__).resolve().parent.parent
ORIGEM = Path(os.environ.get("FNNPK_ORIGEM", RAIZ / "FNNPK"))
DESTINO = Path(
    os.environ.get("FNNPK_PREPARACAO", RAIZ / "FNNPK_preparacao")
)

CLASSES = {
    "-K": "def_k",
    "-N": "def_n",
    "-P": "def_p",
    "FN": "fn",
}

EXTENSOES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def calcular_hash(arquivo):
    resumo = hashlib.sha256()

    with arquivo.open("rb") as entrada:
        for bloco in iter(lambda: entrada.read(1024 * 1024), b""):
            resumo.update(bloco)

    return resumo.hexdigest()


def salvar_csv(caminho, registros, campos):
    with caminho.open("w", newline="", encoding="utf-8-sig") as saida:
        escritor = csv.DictWriter(saida, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(registros)


def main():
    # Conferir todas as pastas antes de criar a saída.
    for pasta in CLASSES:
        if not (ORIGEM / pasta).is_dir():
            raise FileNotFoundError(
                f"Pasta não encontrada: {ORIGEM / pasta}"
            )

    if DESTINO.exists():
        raise FileExistsError(
            f"A pasta de saída já existe:\n{DESTINO}\n"
            "Use outro nome para DESTINO para preservar a execução anterior."
        )

    arquivos = []

    for pasta, classe in CLASSES.items():
        candidatos = sorted(
            arquivo
            for arquivo in (ORIGEM / pasta).rglob("*")
            if arquivo.is_file()
            and arquivo.suffix.lower() in EXTENSOES
        )

        if not candidatos:
            raise ValueError(f"Nenhuma imagem encontrada em {pasta}")

        for arquivo in candidatos:
            arquivos.append((classe, arquivo, calcular_hash(arquivo)))

    # Identificar também cópias com rótulos conflitantes.
    encontrados = {}
    mantidos = []
    duplicados = []

    for classe, arquivo, resumo in arquivos:
        if resumo in encontrados:
            classe_anterior, arquivo_anterior = encontrados[resumo]

            if classe != classe_anterior:
                raise ValueError(
                    "Imagem idêntica encontrada em classes diferentes:\n"
                    f"{arquivo_anterior}\n{arquivo}\n"
                    "Confira os rótulos antes de continuar."
                )

            duplicados.append({
                "classe": classe,
                "arquivo_duplicado": str(arquivo),
                "arquivo_mantido": str(arquivo_anterior),
                "sha256": resumo,
            })
        else:
            encontrados[resumo] = (classe, arquivo)
            mantidos.append((classe, arquivo, resumo))

    DESTINO.mkdir()
    registros = []

    for numero, (classe, arquivo, resumo) in enumerate(mantidos, start=1):
        pasta_saida = DESTINO / "imagens_sem_copias_exatas" / classe
        pasta_saida.mkdir(parents=True, exist_ok=True)

        nome = f"{classe}_{numero:04d}{arquivo.suffix.lower()}"
        novo_arquivo = pasta_saida / nome

        shutil.copy2(arquivo, novo_arquivo)

        registros.append({
            "classe": classe,
            "arquivo_original": str(arquivo),
            "arquivo_copiado": str(novo_arquivo.relative_to(DESTINO)),
            "sha256": resumo,
        })

    salvar_csv(
        DESTINO / "manifesto.csv",
        registros,
        ["classe", "arquivo_original", "arquivo_copiado", "sha256"],
    )

    salvar_csv(
        DESTINO / "copias_identicas.csv",
        duplicados,
        ["classe", "arquivo_duplicado", "arquivo_mantido", "sha256"],
    )

    contagem = Counter(classe for classe, _, _ in mantidos)

    print("\nPreparação concluída.")
    print(f"Imagens recebidas: {len(arquivos)}")
    print(f"Cópias idênticas excluídas da nova pasta: {len(duplicados)}")
    print(f"Arquivos mantidos: {len(mantidos)}")

    for classe in CLASSES.values():
        print(f"  {classe}: {contagem[classe]}")

    print(f"\nSaída: {DESTINO}")
    print("A pasta original foi preservada.")
    print("Ainda não foi feita a divisão em treino, validação e teste.")


if __name__ == "__main__":
    main()
