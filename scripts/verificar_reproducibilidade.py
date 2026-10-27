"""Executa as verificações reproduzíveis que não exigem dataset, GPU ou Redis.

O comando usa somente a biblioteca padrão do Python, grava saídas reconstruídas
em diretórios temporários e nunca sobrescreve os resultados históricos.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


RAIZ = Path(__file__).resolve().parent.parent
AGENTE = RAIZ / "FNNPK_preparacao" / "agente_visao_v1"
COMPARACAO = RAIZ / "FNNPK_preparacao" / "comparacao_politicas"


class FalhaVerificacao(RuntimeError):
    """Indica que uma etapa verificável não produziu o resultado esperado."""


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def executar(comando: list[str], diretorio: Path) -> subprocess.CompletedProcess[str]:
    ambiente = os.environ.copy()
    ambiente["PYTHONIOENCODING"] = "utf-8"
    resultado = subprocess.run(
        comando,
        cwd=diretorio,
        env=ambiente,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if resultado.returncode:
        detalhes = "\n".join(
            parte.strip() for parte in (resultado.stdout, resultado.stderr) if parte.strip()
        )
        raise FalhaVerificacao(
            f"Comando falhou com código {resultado.returncode}: "
            f"{' '.join(comando)}\n{detalhes}"
        )
    return resultado


def verificar_testes_agente() -> str:
    resultado = executar(
        [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            str(AGENTE),
            "-p",
            "test_*.py",
            "-v",
        ],
        RAIZ,
    )
    texto = resultado.stdout + resultado.stderr
    if "Ran 12 tests" not in texto or "OK" not in texto:
        raise FalhaVerificacao("A suíte do agente terminou sem o resumo esperado de 12 testes.")
    return "12 testes funcionais do agente aprovados"


def ler_jsonl(caminho: Path) -> list[dict]:
    return [
        json.loads(linha)
        for linha in caminho.read_text(encoding="utf-8-sig").splitlines()
        if linha.strip()
    ]


def normalizar_resultado_agente(item: dict) -> dict:
    normalizado = dict(item)
    normalizado.pop("processado_em", None)
    return normalizado


def verificar_simulacao_agente() -> str:
    entrada = AGENTE / "cenarios_demo.jsonl"
    referencia = AGENTE / "resultados_demo.jsonl"
    hashes_antes = {entrada: sha256(entrada), referencia: sha256(referencia)}

    with tempfile.TemporaryDirectory(prefix="fnnpk_simulacao_") as temporario:
        temporario = Path(temporario)
        saida = temporario / "resultados.jsonl"
        executar(
            [
                sys.executable,
                str(AGENTE / "agente_visao.py"),
                "--banco",
                str(temporario / "agente.sqlite"),
                "simular",
                "--entrada",
                str(entrada),
                "--saida",
                str(saida),
            ],
            RAIZ,
        )
        obtido = [normalizar_resultado_agente(x) for x in ler_jsonl(saida)]
        esperado = [normalizar_resultado_agente(x) for x in ler_jsonl(referencia)]
        if len(obtido) != 7:
            raise FalhaVerificacao(
                f"A simulação deveria produzir 7 resultados; produziu {len(obtido)}."
            )
        if obtido != esperado:
            raise FalhaVerificacao(
                "A simulação funcional difere de resultados_demo.jsonl."
            )

    if hashes_antes != {caminho: sha256(caminho) for caminho in hashes_antes}:
        raise FalhaVerificacao("A simulação modificou um artefato histórico.")
    return "7 decisões reproduzidas em SQLite temporário e idênticas à referência"


def verificar_comparacao_politicas() -> str:
    entrada = COMPARACAO / "entrada_cenario.jsonl"
    referencia = COMPARACAO / "comparacao_resultados.json"
    hashes_antes = {entrada: sha256(entrada), referencia: sha256(referencia)}

    with tempfile.TemporaryDirectory(prefix="fnnpk_verificacao_") as temporario:
        temporario = Path(temporario)
        saidas = [temporario / "comparacao_1.json", temporario / "comparacao_2.json"]
        for saida in saidas:
            executar(
                [
                    sys.executable,
                    "comparar_politicas.py",
                    "--entrada",
                    str(entrada),
                    "--saida",
                    str(saida),
                ],
                COMPARACAO,
            )

        if saidas[0].read_bytes() != saidas[1].read_bytes():
            raise FalhaVerificacao("A comparação de políticas não foi determinística.")

        obtido = json.loads(saidas[0].read_text(encoding="utf-8"))
        esperado = json.loads(referencia.read_text(encoding="utf-8"))
        hash_historico = esperado.pop("sha256_entrada", None)
        hash_reconstruido = obtido.pop("sha256_entrada", None)
        if obtido != esperado:
            raise FalhaVerificacao(
                "A comparação reconstruída difere de comparacao_resultados.json."
            )
        if hash_reconstruido != sha256(entrada):
            raise FalhaVerificacao("O hash da entrada registrado na saída está incorreto.")
        if obtido.get("numero_observacoes") != 5:
            raise FalhaVerificacao("A comparação não processou as cinco observações registradas.")
        if obtido.get("decisoes_reproduzidas_conferidas") is not True:
            raise FalhaVerificacao("As decisões reconstruídas não foram marcadas como conferidas.")

    hashes_depois = {caminho: sha256(caminho) for caminho in hashes_antes}
    if hashes_antes != hashes_depois:
        raise FalhaVerificacao("Um artefato histórico foi modificado durante a verificação.")
    observacao_hash = ""
    if hash_historico != hash_reconstruido:
        observacao_hash = (
            "; ATENÇÃO: o hash histórico da entrada não corresponde à cópia "
            "sanitizada publicada, mas todas as decisões e demais campos coincidem"
        )
    return (
        "comparação simulada reproduzida duas vezes e decisões idênticas à referência"
        f"{observacao_hash}"
    )


def verificar_arquivos_estruturados() -> str:
    quantidades = {"JSON": 0, "JSONL": 0, "CSV": 0, "NPZ": 0}

    for caminho in sorted(RAIZ.rglob("*.json")):
        json.loads(caminho.read_text(encoding="utf-8-sig"))
        quantidades["JSON"] += 1

    for caminho in sorted(RAIZ.rglob("*.jsonl")):
        for numero, linha in enumerate(
            caminho.read_text(encoding="utf-8-sig").splitlines(), 1
        ):
            if linha.strip():
                try:
                    json.loads(linha)
                except json.JSONDecodeError as erro:
                    raise FalhaVerificacao(f"JSONL inválido em {caminho}:{numero}: {erro}") from erro
        quantidades["JSONL"] += 1

    for caminho in sorted(RAIZ.rglob("*.csv")):
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
            leitor = csv.reader(arquivo)
            if next(leitor, None) is None:
                raise FalhaVerificacao(f"CSV vazio: {caminho.relative_to(RAIZ)}")
            for _ in leitor:
                pass
        quantidades["CSV"] += 1

    for caminho in sorted(RAIZ.rglob("*.npz")):
        try:
            with zipfile.ZipFile(caminho) as arquivo:
                if not arquivo.namelist() or arquivo.testzip() is not None:
                    raise FalhaVerificacao(f"NPZ inválido: {caminho.relative_to(RAIZ)}")
        except zipfile.BadZipFile as erro:
            raise FalhaVerificacao(f"NPZ inválido: {caminho.relative_to(RAIZ)}") from erro
        quantidades["NPZ"] += 1

    resumo = ", ".join(f"{total} {tipo}" for tipo, total in quantidades.items())
    return f"arquivos estruturados legíveis ({resumo})"


def main() -> int:
    etapas = [
        ("Testes do agente", verificar_testes_agente),
        ("Simulação funcional", verificar_simulacao_agente),
        ("Comparação de políticas", verificar_comparacao_politicas),
        ("Integridade estrutural", verificar_arquivos_estruturados),
    ]
    print("Verificação básica de reprodutibilidade FNNPK")
    print("Não requer dataset, modelos treinados, GPU ou servidor Redis.\n")
    try:
        for nome, funcao in etapas:
            print(f"[EXECUTANDO] {nome}")
            detalhe = funcao()
            print(f"[APROVADO] {nome}: {detalhe}")
    except (FalhaVerificacao, OSError, ValueError, json.JSONDecodeError) as erro:
        print(f"[FALHOU] {nome}: {erro}", file=sys.stderr)
        return 1
    print("\n[APROVADO] Todas as verificações básicas foram concluídas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
