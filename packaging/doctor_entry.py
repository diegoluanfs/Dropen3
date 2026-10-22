"""Command line entry point for the frozen Dropen3 Doctor executable."""
from dropen3.__main__ import main
import sys

if __name__ == "__main__":
    raise SystemExit(main(["doctor", *sys.argv[1:]]))
