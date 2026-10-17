"""python -m app  ->  sobe a tela do fechamento em 127.0.0.1 e abre o navegador."""
import sys

from .servidor import main

if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    main(abrir_navegador="--sem-navegador" not in sys.argv)
