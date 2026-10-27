from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np

# Resultados do modelo C.
# Linhas: classes reais. Colunas: classes preditas.
matriz = np.array([
    [8, 0, 1, 1],
    [0, 8, 0, 1],
    [0, 0, 9, 1],
    [0, 0, 0, 2],
])

classes = ["def_k", "def_n", "def_p", "fn"]
saida = Path(__file__).resolve().parent

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 12,
    "pdf.fonttype": 42,
})

fig, ax = plt.subplots(figsize=(6.4, 5.4))

imagem = ax.imshow(
    matriz,
    cmap="Blues",
    vmin=0,
    vmax=10,
    interpolation="nearest",
)

ax.set_xticks(range(len(classes)), labels=classes)
ax.set_yticks(range(len(classes)), labels=classes)

ax.set_xlabel("Classe predita", labelpad=10)
ax.set_ylabel("Classe real", labelpad=10)

# Divisões entre as células.
ax.set_xticks(np.arange(-0.5, 4, 1), minor=True)
ax.set_yticks(np.arange(-0.5, 4, 1), minor=True)
ax.grid(which="minor", color="white", linewidth=1.5)
ax.tick_params(which="minor", bottom=False, left=False)

# Contagens em cada célula.
for linha in range(4):
    for coluna in range(4):
        valor = matriz[linha, coluna]
        ax.text(
            coluna,
            linha,
            str(valor),
            ha="center",
            va="center",
            fontsize=15,
            color="white" if valor >= 6 else "black",
        )

barra = fig.colorbar(imagem, ax=ax, fraction=0.046, pad=0.04)
barra.set_label("Número de imagens")
barra.set_ticks(range(0, 11, 2))

fig.tight_layout()

for extensao in ("png", "pdf"):
    arquivo = saida / f"fig_matriz_confusao_modelo_c.{extensao}"
    fig.savefig(
        arquivo,
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
    )
    print(f"Figura salva em: {arquivo}")

plt.close(fig)