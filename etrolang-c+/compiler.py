import sys
import os
import tempfile
import subprocess
import shutil

# Fixed langlib.h - only declarations
LANGLIB_H = """
#ifndef LANGLIB_H
#define LANGLIB_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_VARS 100

typedef struct {
    char name[32];
    int value;
} Variable;

extern Variable vars[MAX_VARS];
extern int var_count;

int get_var(const char *name);
void set_var(const char *name, int value);
int input_val(void);
void print_val(int val);

#endif
"""

# Fixed langlib.c - implementations
LANGLIB_C = """
#include "langlib.h"

Variable vars[MAX_VARS];
int var_count = 0;

int get_var(const char *name) {
    for (int i = 0; i < var_count; i++) {
        if (strcmp(vars[i].name, name) == 0) return vars[i].value;
    }
    fprintf(stderr, "Undefined variable: %s\\n", name);
    exit(1);
}

void set_var(const char *name, int value) {
    for (int i = 0; i < var_count; i++) {
        if (strcmp(vars[i].name, name) == 0) {
            vars[i].value = value;
            return;
        }
    }
    if (var_count >= MAX_VARS) {
        fprintf(stderr, "Too many variables.\\n");
        exit(1);
    }
    strncpy(vars[var_count].name, name, 31);
    vars[var_count].name[31] = '\\0';
    vars[var_count].value = value;
    var_count++;
}

int input_val(void) {
    int val;
    if (scanf("%d", &val) != 1) {
        fprintf(stderr, "Failed to read input.\\n");
        exit(1);
    }
    return val;
}

void print_val(int val) {
    printf("%d\\n", val);
}
"""

# Helper to escape string literals in C code
def c_str_escape(s):
    return s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')

# Compile code from our esolang code to C source (prog.c)
def compile_to_c(source_lines):
    lines = []
    lines.append('#include "langlib.h"')
    lines.append('')
    lines.append('int main() {')
    lines.append('    // Initialize variables if needed')
    # We parse a minimalistic language with commands:
    # VAR <name>
    # SET <name> <value>
    # INPUT <name>
    # PRINT <name or value>
    # MATH <name> = <expr> (expr is simple: var or val [+ - * /] var or val)
    # IF <name or val> <op> <name or val>
    # ELSE
    # ENDIF
    # (No loops implemented for simplicity here)

    indent = '    '
    in_if = False
    if_stack = []

    for raw_line in source_lines:
        line = raw_line.strip()
        if not line or line.startswith('#'):
            continue

        tokens = line.split()

        cmd = tokens[0].upper()
        if cmd == "VAR":
            # Declare variable, in this simple approach variables are managed in langlib, no need C var decl
            varname = tokens[1]
            lines.append(f'{indent}// Declare var {varname} (managed in langlib)')
        elif cmd == "SET":
            varname = tokens[1]
            value = ' '.join(tokens[2:])
            lines.append(f'{indent}set_var("{varname}", {value});')
        elif cmd == "INPUT":
            varname = tokens[1]
            lines.append(f'{indent}set_var("{varname}", input_val());')
        elif cmd == "PRINT":
            # PRINT either variable or immediate int
            arg = ' '.join(tokens[1:])
            if arg.isdigit() or (arg.startswith('-') and arg[1:].isdigit()):
                lines.append(f'{indent}print_val({arg});')
            else:
                lines.append(f'{indent}print_val(get_var("{arg}"));')
        elif cmd == "MATH":
            # e.g. MATH y = y + x
            # parse into set_var("y", get_var("y") + get_var("x"));
            # supports only single operator and two operands for now
            rest = line[len("MATH"):].strip()
            # Parse like: y = y + x
            try:
                varname, expr = rest.split('=', 1)
                varname = varname.strip()
                expr = expr.strip()
                # Parse expr into parts
                for op in ['+', '-', '*', '/']:
                    if op in expr:
                        left, right = expr.split(op)
                        left = left.strip()
                        right = right.strip()
                        def to_c_val(v):
                            if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
                                return v
                            else:
                                return f'get_var("{v}")'
                        c_left = to_c_val(left)
                        c_right = to_c_val(right)
                        lines.append(f'{indent}set_var("{varname}", {c_left} {op} {c_right});')
                        break
                else:
                    # No operator, single value or var
                    val = expr
                    if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                        lines.append(f'{indent}set_var("{varname}", {val});')
                    else:
                        lines.append(f'{indent}set_var("{varname}", get_var("{val}"));')
            except Exception as e:
                lines.append(f'{indent}// Failed to parse MATH: {line} // {e}')
        elif cmd == "IF":
            # IF y > 10
            # Only support >, <, ==, !=, >=, <=
            try:
                varname = tokens[1]
                op = tokens[2]
                value = tokens[3]
                def to_c_val(v):
                    if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
                        return v
                    else:
                        return f'get_var("{v}")'
                c_var = to_c_val(varname)
                c_val = to_c_val(value)
                lines.append(f'{indent}if ({c_var} {op} {c_val})' + ' {')
                indent += '    '
                in_if = True
                if_stack.append('if')
            except Exception as e:
                lines.append(f'{indent}// Failed to parse IF: {line} // {e}')
        elif cmd == "ELSE":
            if in_if and if_stack and if_stack[-1] == 'if':
                indent = indent[:-4]
                lines.append(f'{indent}}} else {{')
                indent += '    '
            else:
                lines.append(f'{indent}// ELSE without IF')
        elif cmd == "ENDIF":
            if in_if and if_stack:
                indent = indent[:-4]
                lines.append(f'{indent}}}')
                if_stack.pop()
                if not if_stack:
                    in_if = False
            else:
                lines.append(f'{indent}// ENDIF without IF')
        else:
            lines.append(f'{indent}// Unknown command: {line}')

    lines.append('    return 0;')
    lines.append('}')
    return '\n'.join(lines)

# Write a file helper
def write_file(path, content):
    with open(path, 'w') as f:
        f.write(content)

def main():
    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} <source.code> [-nd] [-debug] [-norun]')
        sys.exit(1)

    source_path = sys.argv[1]
    flags = sys.argv[2:]

    no_delete = '-nd' in flags
    debug = '-debug' in flags
    norun = '-norun' in flags

    # Read source code lines
    with open(source_path, 'r') as f:
        source_lines = f.readlines()

    # Generate C code
    prog_c_code = compile_to_c(source_lines)

    # Determine output paths
    base_dir = os.path.dirname(os.path.abspath(source_path))
    base_name = os.path.splitext(os.path.basename(source_path))[0]
    prog_c_path = os.path.join(base_dir, 'prog.c')
    langlib_h_path = os.path.join(base_dir, 'langlib.h')
    langlib_c_path = os.path.join(base_dir, 'langlib.c')
    binary_path = os.path.join(base_dir, f'{base_name}_binary')

    # Write files
    write_file(prog_c_path, prog_c_code)
    write_file(langlib_h_path, LANGLIB_H)
    write_file(langlib_c_path, LANGLIB_C)

    # Compile command
    compile_cmd = ['gcc', '-O2', prog_c_path, langlib_c_path, '-o', binary_path]

    print('Compiling with:', ' '.join(compile_cmd))
    proc = subprocess.run(compile_cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print('Compilation failed.')
        print(proc.stderr)
        if not no_delete:
            # Remove generated files if failure
            for p in [prog_c_path, langlib_h_path, langlib_c_path]:
                if os.path.exists(p):
                    os.remove(p)
        sys.exit(1)
    else:
        print('Compilation succeeded.')

    # Optional: generate debug tools (just placeholders here)
    if debug:
        debug_js_path = os.path.join(base_dir, 'debug.js')
        debug_java_path = os.path.join(base_dir, 'DebugTool.java')
        write_file(debug_js_path, '// Debug JS tool placeholder\nconsole.log("Debug tool JS");\n')
        write_file(debug_java_path, '// Debug Java tool placeholder\npublic class DebugTool {\n public static void main(String[] args) { System.out.println("Debug tool Java"); }\n}\n')
        print('Debug tools generated.')

    if norun:
        print('Skipping running the binary due to -norun flag.')
        return

    # Run binary
    print('Running', binary_path, ':\n')
    try:
        subprocess.run([binary_path])
    except KeyboardInterrupt:
        print('\nExecution interrupted by user.')

    # Cleanup
    if not no_delete:
        for p in [prog_c_path, langlib_h_path, langlib_c_path, binary_path]:
            if os.path.exists(p):
                os.remove(p)

if __name__ == "__main__":
    main()

