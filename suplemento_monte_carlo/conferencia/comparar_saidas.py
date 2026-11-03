"""Compara uma cópia executada com os resultados fornecidos, sem tolerância numérica."""
import argparse
import difflib
import json
from pathlib import Path


def texto(path):
    data = path.read_bytes()
    return data.decode('utf-16' if data.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')


def comparar(base, copia):
    falhas = 0
    for original in sorted((base / 'resultados_originais').iterdir()):
        if original.suffix not in ('.json', '.csv'):
            continue
        gerado = copia / 'scripts' / original.name
        if not gerado.exists():
            print(f'AUSENTE: {original.name}')
            falhas += 1
            continue
        if original.suffix == '.json':
            a, b = json.loads(texto(original)), json.loads(texto(gerado))
            for campo in ('gerado_em', 'node'):
                a.pop(campo, None)
                b.pop(campo, None)
            igual = a == b
            if not igual:
                print(''.join(difflib.unified_diff(
                    json.dumps(a, ensure_ascii=False, indent=2).splitlines(True),
                    json.dumps(b, ensure_ascii=False, indent=2).splitlines(True),
                    fromfile='original', tofile='gerado')))
        else:
            igual = original.read_bytes() == gerado.read_bytes()
        print(f'{"IGUAL" if igual else "DIFERENTE"}: {original.name}')
        falhas += not igual
    return int(bool(falhas))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('copia', type=Path, help='raiz da cópia temporária já executada')
    args = parser.parse_args()
    raise SystemExit(comparar(Path(__file__).resolve().parents[1], args.copia.resolve()))
