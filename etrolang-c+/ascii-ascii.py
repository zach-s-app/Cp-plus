#!/usr/bin/env python3

import sys

def ascii_to_text():
    # Read ASCII codes from stdin or from a file if provided
    if len(sys.argv) > 1:
        with open(sys.argv[1], 'r') as f:
            codes = f.read().split()
    else:
        codes = sys.stdin.read().split()
    
    # Convert codes to characters and join
    try:
        chars = [chr(int(code)) for code in codes]
        print(''.join(chars))
    except ValueError:
        print("Error: Input contains non-integer values.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    ascii_to_text()

