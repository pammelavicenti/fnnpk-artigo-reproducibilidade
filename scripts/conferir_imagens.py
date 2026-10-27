from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
import csv
import math
import os

BASE = Path(
    os.environ.get(
        "FNNPK_PREPARACAO",
        Path(__file__).resolve().parent.parent / "FNNPK_preparacao",
    )
)

SAIDA = BASE / "conferencia_visual"
SAIDA.mkdir(exist_ok=True)

with (BASE / "manifesto.csv").open(
    encoding="utf-8-sig", newline=""
) as arquivo:
    registros = list(csv.DictReader(arquivo))

COLUNAS = 6
LARGURA = 200
ALTURA = 225
IMAGENS_POR_PAGINA = 30

for classe in ["def_k", "def_n", "def_p", "fn"]:
    imagens = [
        registro
        for registro in registros
        if registro["classe"] == classe
    ]

    for inicio in range(0, len(imagens), IMAGENS_POR_PAGINA):
        lote = imagens[inicio:inicio + IMAGENS_POR_PAGINA]
        linhas = math.ceil(len(lote) / COLUNAS)

        painel = Image.new(
            "RGB",
            (COLUNAS * LARGURA, linhas * ALTURA),
            "white",
        )
        desenho = ImageDraw.Draw(painel)

        for indice, registro in enumerate(lote):
            caminho = BASE / registro["arquivo_copiado"]
            x = (indice % COLUNAS) * LARGURA
            y = (indice // COLUNAS) * ALTURA

            with Image.open(caminho) as imagem:
                miniatura = ImageOps.contain(
                    ImageOps.exif_transpose(imagem).convert("RGB"),
                    (190, 190),
                )
                painel.paste(miniatura, (x + 5, y + 5))

            desenho.text(
                (x + 5, y + 197),
                caminho.name,
                fill="black",
            )
            desenho.text(
                (x + 5, y + 211),
                Path(registro["arquivo_original"]).name,
                fill="black",
            )

        pagina = inicio // IMAGENS_POR_PAGINA + 1
        destino = SAIDA / f"{classe}_pagina_{pagina}.jpg"
        painel.save(destino, quality=95)

print(f"Painéis salvos em:\n{SAIDA}")
