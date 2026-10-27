#!/usr/bin/env python3
"""Recorte não generativo: piloto no treino ou processamento da divisão inteira.
Requer rembg[cpu] e Pillow em ambiente separado do TensorFlow.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
from datetime import datetime
from pathlib import Path

CLASSES = ('def_k', 'def_n', 'def_p', 'fn')
PARTICOES = ('train', 'val', 'test')
EXTENSOES = {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tif', '.tiff'}
MODELO = 'isnet-general-use'
FUNDO = (200, 200, 200)


def sha256(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for bloco in iter(lambda: f.read(1024 * 1024), b''):
            h.update(bloco)
    return h.hexdigest()


def inventario(base):
    registros = []
    hashes = {}
    for parte in PARTICOES:
        for classe in CLASSES:
            pasta = base / parte / classe
            if not pasta.is_dir():
                raise FileNotFoundError(f'Pasta esperada não encontrada: {pasta}')
            arquivos = sorted(p for p in pasta.rglob('*') if p.is_file() and p.suffix.lower() in EXTENSOES)
            if not arquivos:
                raise ValueError(f'Pasta sem imagens: {pasta}')
            for p in arquivos:
                digest = sha256(p)
                if digest in hashes and hashes[digest][0] != parte:
                    raise ValueError(f'Cópia idêntica entre partições: {p} e {hashes[digest][1]}')
                hashes[digest] = (parte, str(p))
                registros.append((parte, classe, p, digest))
    return registros


def painel(amostras, destino):
    from PIL import Image, ImageDraw, ImageOps
    largura, altura = 1000, 300
    folha = Image.new('RGB', (largura, altura * len(amostras)), 'white')
    draw = ImageDraw.Draw(folha)
    for i, (rotulo, original, recorte, mascara) in enumerate(amostras):
        y = altura * i
        draw.text((12, y + 8), rotulo, fill='black')
        for j, (nome, im) in enumerate((('Original', original), ('Fundo cinza', recorte), ('Mascara', mascara))):
            x = j * 330 + 12
            draw.text((x, y + 30), nome, fill='black')
            mini = ImageOps.contain(im.convert('RGB'), (310, 245))
            folha.paste(mini, (x + (310 - mini.width) // 2, y + 50 + (245 - mini.height) // 2))
    folha.save(destino)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument('--piloto', action='store_true', help='Duas imagens por classe, somente do treino (padrão).')
    modo.add_argument('--completo', action='store_true', help='Todas as imagens, preservando as partições.')
    parser.add_argument('--base', type=Path, default=Path(__file__).resolve().parent / 'divisao_agrupada')
    args = parser.parse_args()
    base = args.base.resolve()
    registros = inventario(base)
    if not args.completo:
        escolhidos = []
        for classe in CLASSES:
            grupo = [r for r in registros if r[0] == 'train' and r[1] == classe]
            escolhidos.extend([grupo[0], grupo[-1]] if len(grupo) > 1 else grupo)
        registros = escolhidos
    from PIL import Image, ImageChops, ImageOps
    from rembg import new_session, remove
    print('Carregando segmentador. A primeira execução baixa os pesos; requer internet.', flush=True)
    session = new_session(MODELO, providers=['CPUExecutionProvider'])
    nome_modo = 'completo' if args.completo else 'piloto'
    saida = base.parent / f'recorte_{nome_modo}_{datetime.now():%Y%m%d_%H%M%S_%f}'
    saida.mkdir(parents=True, exist_ok=False)
    versoes = {}
    for nome in ('rembg', 'Pillow', 'onnxruntime', 'numpy'):
        try:
            versoes[nome] = importlib.metadata.version(nome)
        except importlib.metadata.PackageNotFoundError:
            versoes[nome] = None
    protocolo = {'origem': str(base), 'modo': nome_modo, 'modelo_segmentacao': MODELO,
                 'fundo_rgb': FUNDO, 'versoes': versoes, 'script_sha256': sha256(Path(__file__)),
                 'particoes_preservadas': True, 'imagens_sinteticas_adicionadas': False,
                 'revisao_visual': 'pendente', 'orientacao_exif': 'aplicada',
                 'crop': False, 'redimensionamento': False, 'alpha_matting': False}
    (saida / 'protocolo.json').write_text(json.dumps(protocolo, ensure_ascii=False, indent=2), encoding='utf-8')
    campos = ['particao', 'classe', 'origem', 'sha256_original', 'rgb', 'sha256_rgb',
              'mascara', 'transparente', 'largura', 'altura', 'fracao_mascara', 'revisao']
    amostras = []
    with (saida / 'manifesto_recorte.csv').open('w', encoding='utf-8-sig', newline='') as f:
        escritor = csv.DictWriter(f, fieldnames=campos)
        escritor.writeheader()
        for i, (parte, classe, p, digest) in enumerate(registros, 1):
            with Image.open(p) as im:
                rgba = ImageOps.exif_transpose(im).convert('RGBA')
            rgb = rgba.convert('RGB')
            mask = remove(rgb, session=session, only_mask=True, alpha_matting=False,
                          post_process_mask=False).convert('L')
            if mask.size != rgb.size:
                raise ValueError(f'Máscara com dimensões inesperadas: {p}')
            mask = ImageChops.multiply(mask, rgba.getchannel('A'))
            transparencia = rgba.copy()
            transparencia.putalpha(mask)
            resultado = Image.new('RGB', rgb.size, FUNDO)
            resultado.paste(rgb, (0, 0), mask)
            relativo = p.relative_to(base / parte / classe)
            destinos = {}
            for tipo, im in (('dataset_rgb', resultado), ('mascaras', mask), ('transparentes', transparencia)):
                alvo = saida / tipo / parte / classe / relativo.parent / (relativo.name + '.png')
                alvo.parent.mkdir(parents=True, exist_ok=True)
                im.save(alvo)
                destinos[tipo] = alvo
            hist = mask.histogram()
            fracao = sum(n * k for k, n in enumerate(hist)) / (255 * mask.width * mask.height)
            alerta = 'mascara_extrema_revisar' if fracao < 0.05 or fracao > 0.95 else 'revisao_visual_pendente'
            escritor.writerow({'particao': parte, 'classe': classe, 'origem': str(p), 'sha256_original': digest,
                               'rgb': str(destinos['dataset_rgb'].relative_to(saida)),
                               'sha256_rgb': sha256(destinos['dataset_rgb']),
                               'mascara': str(destinos['mascaras'].relative_to(saida)),
                               'transparente': str(destinos['transparentes'].relative_to(saida)),
                               'largura': rgb.width, 'altura': rgb.height,
                               'fracao_mascara': round(fracao, 6), 'revisao': alerta})
            f.flush()
            if not args.completo:
                amostras.append((f'{classe} / {p.name}', rgb, resultado, mask))
            print(f'{i}/{len(registros)}: {parte}/{classe}/{p.name} — {alerta}', flush=True)
    if amostras:
        painel(amostras, saida / 'comparacao_piloto.png')
    print(f'\nSaída: {saida}')
    print('Originais preservados. Confira se o recorte mantém toda a folha e seus sintomas.')
    if not args.completo:
        print('Abra comparacao_piloto.png no Windows. Este piloto não é uma base completa para treinamento.')
    else:
        print(f'Base RGB para futuro treinamento: {saida / "dataset_rgb"}')
        print('O teste já consultado continua exploratório; o recorte não cria um teste independente.')


if __name__ == '__main__':
    main()
