#!/bin/bash

# Optional: compiled binary to debug
BINARY_FILE="$1"

# Create debug.js
cat > debug.js <<'EOF'
const { spawnSync } = require('child_process');
const fs = require('fs');

// Check input
if (process.argv.length < 3) {
    console.log('Usage: node debug.js <binary_file>');
    process.exit(1);
}

const binaryPath = process.argv[2];

// Run Java hex dumper
const java = spawnSync('java', ['DebugTool', binaryPath], { encoding: 'utf-8' });

if (java.error) {
    console.error('Error running DebugTool:', java.error);
    process.exit(1);
}

console.log('--- HEX Dump with RGB ---');
console.log(java.stdout);

// Silly RGB interpretation
const hexBytes = java.stdout.trim().split(/\s+/);
hexBytes.forEach((byte, i) => {
    if (i % 3 === 0) process.stdout.write('\nRGB: ');
    process.stdout.write(`${byte} `);
});
console.log('\n--- Analysis ---');
// You can expand this with actual logic parser later
console.log('This binary likely includes I/O, arithmetic, and variables.');
EOF

# Create DebugTool.java
cat > DebugTool.java <<'EOF'
import java.io.FileInputStream;
import java.io.IOException;

public class DebugTool {
    public static void main(String[] args) throws IOException {
        if (args.length < 1) {
            System.out.println("Usage: java DebugTool <binary_file>");
            return;
        }

        FileInputStream in = new FileInputStream(args[0]);
        int b;
        while ((b = in.read()) != -1) {
            System.out.printf("%02X ", b);
        }
        in.close();
    }
}
EOF

# Compile DebugTool.java
javac DebugTool.java

echo "Debug tools written and compiled."

# Run if a binary was provided
if [ -n "$BINARY_FILE" ]; then
    echo "Running debug tools on $BINARY_FILE..."
    node debug.js "$BINARY_FILE"
fi

