"""Local administrator recovery; requires master secret and private server key folder."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from services.privacy import restore_file, private_write

parser = argparse.ArgumentParser()
parser.add_argument('encrypted_file', type=Path)
parser.add_argument('output_file', type=Path, help='Explicit destination. Existing file will not be overwritten.')
args = parser.parse_args()
raw, _ = restore_file(args.encrypted_file.read_bytes())
private_write(args.output_file, raw)
print('Restored file to the specified private destination.')
