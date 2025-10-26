import re
import sys
import math
import random as rand
try:
    import readline
except ImportError:
    pass


# -----------------------
# Lexer / tokenization
# -----------------------
TOKEN_SPEC = [
    ('NUMBER',   r'\d+(\.\d*)?'),               # integer or decimal
    ('STRING',   r'"([^"]*)"'),                 # "string"
    ('NAME',     r'[A-Za-z][A-Za-z0-9\$]*'),    # variable or keyword
    ('OP',       r'<=|>=|<>|[+\-*/\^=<>:;]'),   # operators, punctuation
    ('LPAREN',   r'\('),
    ('RPAREN',   r'\)'),
    ('SKIP',     r'[ \t]+'),
    ('COMMA',    r','),
    ('UNKNOWN',  r'.'),
]
TOK_RE = re.compile('|'.join(f'(?P<{name}>{pattern})' for name, pattern in TOKEN_SPEC))

KEYWORDS = {'PRINT','LET','INPUT','GOTO','IF','THEN','FOR','TO','STEP','NEXT',
            'GOSUB','RETURN','REM','END','STOP','DATA','READ','RESTORE','LIST','RUN','NEW'}

FUNCS = { # Name, Number of args
    'ABS': 1,
    'ATN': 1,
    'COS': 1,
    'EXP': 1,
    'INT': 1,
    'LOG': 1,
    'SGN': 1,
    'SIN': 1,
    'SQR': 1,
    'TAN': 1,
    'RND': 1,
    'PEEK': 1,
    'POS': 0,
    'SPC': 1,
    'TAB': 1,
    'ASC': 1,
    'LEN': 1,
    'VAL': 1,
    'CHR$': 1,
    'STR$': 1,
    'LEFT$': 2,
    'MID$': 3,
    'RIGHT$':2
}

def tokenize(s):
    """Convert a line of BASIC code into a list of tokens."""
    tokens = []
    pos = 0
    while pos < len(s):
        m = TOK_RE.match(s, pos)
        if not m:
            break
        kind = m.lastgroup
        txt = m.group(0)
        pos = m.end()
        
        if kind == 'SKIP':
            continue
        if kind == 'NUMBER':
            n = float(txt)
            if n.is_integer():
                n = int(n)
            tokens.append(('NUMBER', n))
        elif kind == 'STRING':
            tokens.append(('STRING', m.groups()[3]))
        elif kind == 'NAME':
            up = txt.upper()
            if up in KEYWORDS:
                tokens.append((up, up))
            elif up in FUNCS.keys():
                tokens.append(('FUNC', up))
            else:
                tokens.append(('NAME', up))
        elif kind in ('OP','LPAREN','RPAREN','COMMA'):
            tokens.append((kind, txt))
        else:
            tokens.append(('UNKNOWN', txt))
    return tokens


# -----------------------
# Expression parser: Shunting-Yard -> RPN
# -----------------------
PREC = {'^': 4, '*': 3, '/': 3, '+': 2, '-': 2,
        '=': 1, '<': 1, '>': 1, '<=':1, '>=':1, '<>':1}

RIGHT_ASSOC = {'^'}

def to_rpn(tokens):
    """Convert token list to RPN using shunting-yard algorithm."""
    out = []
    stack = []
    
    for t in tokens:
        typ, val = t
        if typ in ('NUMBER','STRING','NAME'):
            out.append(t)
        elif typ == 'FUNC':
            stack.append(t)  # function will be handled as operator with args
        elif typ == 'LPAREN':
            stack.append(t)
        elif typ == 'RPAREN':
            while stack and stack[-1][0] != 'LPAREN':
                out.append(stack.pop())
            if not stack:
                raise SyntaxError("Mismatched parentheses")
            stack.pop()  # remove LPAREN
            # If a function is on top, pop it to output
            if stack and stack[-1][0] == 'FUNC':
                out.append(stack.pop())
        elif typ == 'OP':
            while stack and stack[-1][0] == 'OP':
                o2 = stack[-1][1]
                if (PREC.get(o2,0) > PREC.get(val,0)) or (PREC.get(o2,0) == PREC.get(val,0) and val not in RIGHT_ASSOC):
                    out.append(stack.pop())
                else:
                    break
            stack.append(t)
        elif typ == 'COMMA':
            stack.append(t)
        else:
            raise RuntimeError(f"Unknown token type: {typ}")
    
    while stack:
        if stack[-1][0] in ('LPAREN','RPAREN'):
            raise SyntaxError("Mismatched parentheses")
        out.append(stack.pop())
    
    return out


def eval_rpn(rpn, env):
    """Evaluate an RPN expression with given environment."""
    st = []
    for typ, val in rpn:
        if typ == 'NUMBER' or typ == 'STRING':
            st.append(val)
        elif typ == 'NAME':
            st.append(env.get(val, 0.0 if not (val.endswith('$') or val in ['SPC']) else ""))
        elif typ == 'FUNC':
            # Very simple single-arg function evaluation
            arg = [st.pop() for _ in range(FUNCS[val])]
            arg.reverse()
            st.append(eval_func(val, *arg))
        elif typ == 'OP':
            if val == '-' and len(st)<=2:
                st.append(-st.pop())
                continue
            b, a = st.pop(), st.pop()
            if val == '+': st.append(a+b)
            elif val == '-': st.append(a-b)
            elif val == '*': st.append(a*b)
            elif val == '/': st.append(a/b)
            elif val == '^': st.append(a**b)
            elif val == '=': st.append(1.0 if a==b else 0.0)
            elif val == '<': st.append(1.0 if a<b else 0.0)
            elif val == '>': st.append(1.0 if a>b else 0.0)
            elif val == '<=': st.append(1.0 if a<=b else 0.0)
            elif val == '>=': st.append(1.0 if a>=b else 0.0)
            elif val == '<>': st.append(1.0 if a!=b else 0.0)
            else: raise RuntimeError(f"Unknown operator: {val}")
        elif typ == 'COMMA':
            pass
    return st[-1] if st else 0.0


def eval_func(name, *args):
    """Evaluate a BASIC function."""
    name = name.upper()
    try:
        if name == 'ABS': return abs(args[0])
        if name == 'ATN': return math.atan(args[0])
        if name == 'COS': return math.cos(args[0])
        if name == 'EXP': return math.exp(args[0])
        if name == 'INT': return int(args[0])
        if name == 'LOG': return math.log(args[0])
        if name == 'SGN': return args[0]/abs(args[0]) if args[0]!=0 else 0
        if name == 'SIN': return math.sin(args[0])
        if name == 'SQR': return args[0]**2
        if name == 'TAN': return math.tan(args[0])
        if name == 'RND': return rand.random()
        if name == 'SPC': return ' '*int(args[0])
        if name == 'CHR$': return chr(int(args[0]))
        if name == 'STR$': return str(args[0])
        if name == 'ASC': return ord(args[0])
        if name == 'LEN': return len(args[0])
        if name == 'VAL': return float(args[0])
        if name == 'LEFT$': return args[0][:args[1]]
        if name == 'RIGHT$': return args[0][-args[1]:]
        if name == 'MID$': return args[0][args[1]:args[1]+args[2]]
    except Exception:
        return 0


# -----------------------
# Program storage and interpreter
# -----------------------
class BasicInterpreter:
    def __init__(self, output_callback):
        self.output_callback = output_callback
        self.program = {}   # lineno -> raw line string
        self.lines_sorted = []
        self.vars = {}      # variable storage (strings if name ends with $)
        self.for_stack = [] # stack of (var, end, step, return_line)
        self.gosub_stack = []
        self.data = []
        self.data_ptr = 0
        self.pc_index = 0   # index into lines_sorted
        self.running = False

    def input_line(self, line):
        line = line.rstrip()
        if not line:
            return
        m = re.match(r'^\s*(\d+)\s*(.*)$', line)
        if m:
            lineno = int(m.group(1))
            rest = m.group(2)
            if rest.strip() == '':
                # delete line
                if lineno in self.program:
                    del self.program[lineno]
            else:
                self.program[lineno] = rest
            self._refresh_lines()
        else:
            # immediate command
            cmd = line.strip().upper()
            if cmd == 'LIST':
                self.do_LIST()
            elif cmd == 'RUN':
                self.do_RUN()
            elif cmd == 'NEW':
                self.program.clear(); self._refresh_lines()
                self.output_callback("PROGRAM CLEARED.")
            else:
                # try to run as immediate statement (like PRINT "HI")
                self.execute_statement_line('0', line, immediate=True)

    def _refresh_lines(self):
        self.lines_sorted = sorted(self.program.items())
    
    def do_LIST(self):
        for n,txt in self.lines_sorted:
            self.output_callback(f"{n} {txt}")

    def do_RUN(self):
        if not self.lines_sorted:
            self.output_callback("NO PROGRAM.")
            return
        self.vars.clear()
        self.for_stack.clear()
        self.gosub_stack.clear()
        self.data_ptr = 0
        self.data = self._collect_data()
        self.pc_index = 0
        self.running = True
        #try:
        while self.running and 0 <= self.pc_index < len(self.lines_sorted):
            lineno, line = self.lines_sorted[self.pc_index]
            # execute
            self.execute_statement_line(lineno, line)
            # pc_index is updated by statements (GOTO etc). If not changed, move to next
            if self.running and self.pc_index < len(self.lines_sorted) and (self.lines_sorted[self.pc_index][0] == lineno):
                self.pc_index += 1
        # except Exception as e:
        #     self.output_callback("ERROR:", e)
        #     self.running = False

    def _collect_data(self):
        data = []
        for _,line in self.lines_sorted:
            toks = tokenize(line)
            if toks and toks[0][0] == 'DATA':
                # everything after DATA tokens split by commas and strings become data entries
                after = line.upper().split('DATA',1)[1]
                # parse tokens simply: strings and numbers separated by commas
                parts = re.findall(r'"([^"]*)"|[^,]+', after)
                for p in parts:
                    if p is None: continue
                    p = p.strip()
                    if p == '': continue
                    if p.startswith('"') and p.endswith('"'):
                        data.append(p[1:-1])
                    else:
                        try:
                            data.append(float(p))
                        except:
                            data.append(p)
        return data

    # Execute a single full line (may contain multiple statements separated by :)
    def execute_statement_line(self, lineno, line, immediate=False):
        # split statements by colon (but avoid colon in strings)
        parts = []
        cur = ''
        in_str = False
        for ch in line:
            if ch == '"':
                in_str = not in_str
                cur += ch
            elif ch == ':' and not in_str:
                parts.append(cur.strip()); cur = ''
            else:
                cur += ch
        if cur.strip(): parts.append(cur.strip())
        for stmt in parts:
            if immediate:
                self._exec_stmt(stmt, None)
            else:
                self._exec_stmt(stmt, lineno)

    def _find_line_index(self, target):
        # binary search for line index with number==target
        for i,(ln,_t) in enumerate(self.lines_sorted):
            if ln == target:
                return i
        return None

    def _exec_stmt(self, stmt, lineno):
        toks = tokenize(stmt)
        if not toks:
            return
        first = toks[0]
        if first[0] == 'REM':
            return
        if first[0] == 'PRINT':
            self._do_PRINT(toks[1:])
            return
        if first[0] == 'LET':
            # skip LET
            toks = toks[1:]
        # handle assignment: NAME = expr
        if len(toks) >= 3 and toks[0][0] == 'NAME' and toks[1][0] == 'OP' and toks[1][1] == '=':
            name = toks[0][1]
            try:
                rpn = to_rpn(toks[2:])
            except RuntimeError as e:
                self.output_callback(str(e).upper())
            val = eval_rpn(rpn, self.vars)
            if name.endswith('$'):
                # strings may be assigned from NUMBER -> convert
                if isinstance(val, float):
                    self.vars[name] = str(val)
                else:
                    self.vars[name] = val
            else:
                # numeric
                if isinstance(val, str):
                    try:
                        self.vars[name] = float(val)
                    except:
                        self.vars[name] = 0.0
                else:
                    self.vars[name] = float(val)
            return
        # INPUT
        if first[0] == 'INPUT':
            # simplified: INPUT A,B$ -> prompt and assign
            rest = stmt[len('INPUT'):].strip()
            names = [n.strip().upper() for n in rest.split(',')]
            for nm in names:
                if nm.endswith('$'):
                    v = input("? ")
                    self.vars[nm] = v
                else:
                    v = input("? ")
                    try:
                        self.vars[nm] = float(v)
                    except:
                        self.vars[nm] = 0.0
            return
        # GOTO
        if first[0] == 'GOTO':
            target = int(toks[1][1]) if toks[1][0] == 'NUMBER' else int(toks[1][1]) if toks[1][0]=='NAME' else int(toks[1][1])
            idx = self._find_line_index(target)
            if idx is None:
                raise RuntimeError(f"GOTO TO UNKNOWN line {target}")
            self.pc_index = idx
            return
        # GOSUB
        if first[0] == 'GOSUB':
            target = int(toks[1][1])
            idx = self._find_line_index(target)
            if idx is None:
                raise RuntimeError(f"GOSUB TO UNKNOWN line {target}")
            # push return index (next line)
            self.gosub_stack.append(self.pc_index + 1)
            self.pc_index = idx
            return
        # RETURN
        if first[0] == 'RETURN':
            if not self.gosub_stack:
                raise RuntimeError("RETURN WITHOUT GOSUB")
            self.pc_index = self.gosub_stack.pop()
            return
        # IF ... THEN line
        if first[0] == 'IF':
            # we expect: IF <expr> THEN <lineno>
            # find THEN token
            up = [t[0] for t in toks]
            try:
                then_idx = up.index('THEN')
            except ValueError:
                raise SyntaxError("IF WITHOUT THEN")
            expr_tokens = toks[1:then_idx]
            try:
                print(expr_tokens)
                rpn = to_rpn(expr_tokens)
                print(rpn)
            except RuntimeError as e:
                self.output_callback(str(e).upper())
            cond = eval_rpn(rpn, self.vars)
            print(cond)
            if cond != 0 and cond != '' and cond is not None:
                print("Condition is true!")
                # jump to line given after THEN (simple numeric token)
                targettok = toks[then_idx+1]
                if targettok[0] == 'NUMBER': target = int(targettok[1])
                elif targettok[0] == 'NAME': target = int(targettok[1])
                else: target = int(targettok[1])
                idx = self._find_line_index(target)
                if idx is None:
                    raise RuntimeError(f"IF THEN to unknown line {target}")
                self.pc_index = idx
            return
        # FOR var = start TO end [STEP n]
        if first[0] == 'FOR':
            # parse roughly: FOR A = 1 TO 10 STEP 2
            # tokens layout: NAME, OP('=') expr, TO, expr, optional STEP expr
            if toks[1][0] != 'NAME' or toks[2][0] != 'OP' or toks[2][1] != '=':
                raise SyntaxError("MALFORMED FOR")
            var = toks[1][1]
            # find TO
            kinds = [t[0] for t in toks]
            if 'TO' not in kinds:
                raise SyntaxError("FOR WITHOUT TO")
            to_idx = kinds.index('TO')
            try:
                rpn_start = to_rpn(toks[3:to_idx])
            except RuntimeError as e:
                self.output_callback(str(e).upper())
            start = eval_rpn(rpn_start, self.vars)
            # find STEP if present
            if 'STEP' in kinds:
                step_idx = kinds.index('STEP')
                try:
                    rpn_end = to_rpn(toks[to_idx+1:step_idx])
                    rpn_step = to_rpn(toks[step_idx+1:])
                except RuntimeError as e:
                    self.output_callback(str(e).upper())
                step = eval_rpn(rpn_step, self.vars)
            else:
                try:
                    rpn_end = to_rpn(toks[to_idx+1:])
                except RuntimeError as e:
                    self.output_callback(str(e).upper())
                step = 1.0
            end = eval_rpn(rpn_end, self.vars)
            self.vars[var] = float(start)
            # push frame: var, end, step, next-line-index (current next)
            self.for_stack.append((var, float(end), float(step), self.pc_index + 1))
            return
        # NEXT var
        if first[0] == 'NEXT':
            var = toks[1][1] if len(toks) > 1 and toks[1][0] == 'NAME' else None
            if not self.for_stack:
                raise RuntimeError("NEXT WITHOUT FOR")
            fvar, fend, fstep, ret_index = self.for_stack[-1]
            if var and var != fvar:
                raise RuntimeError("NEXT VARIABLE MISMATCH")
            # increment
            self.vars[fvar] = self.vars.get(fvar,0.0) + fstep
            # check if loop continues (handle positive/negative step)
            cont = (fstep > 0 and self.vars[fvar] <= fend) or (fstep < 0 and self.vars[fvar] >= fend)
            if cont:
                # jump back to loop body (ret_index)
                self.pc_index = ret_index
            else:
                # pop and continue after NEXT (do nothing; loop will advance)
                self.for_stack.pop()
            return
        # DATA READ RESTORE
        if first[0] == 'READ':
            # READ A,B$
            rest = stmt[len('READ'):].strip()
            names = [n.strip().upper() for n in rest.split(',')]
            for nm in names:
                if self.data_ptr >= len(self.data):
                    self.output_callback("OUT OF DATA")
                    self.vars[nm] = 0.0
                else:
                    val = self.data[self.data_ptr]; self.data_ptr += 1
                    if nm.endswith('$'):
                        self.vars[nm] = val
                    else:
                        try:
                            self.vars[nm] = float(val)
                        except:
                            self.vars[nm] = 0.0
            return
        if first[0] == 'RESTORE':
            self.data_ptr = 0
            return
        # END/STOP
        if first[0] in ('END','STOP'):
            self.running = False
            return
        # unknown/unsupported: try to evaluate as expression or PRINT
        # fallback: try PRINT expr
        if first[0] == 'NAME' or first[0] == 'NUMBER':
            # try to evaluate
            try:
                try:
                    rpn = to_rpn(toks)
                except RuntimeError as e:
                    self.output_callback(str(e).upper())
                val = eval_rpn(rpn, self.vars)
                self.output_callback(val)
            except Exception as e:
                raise
            return
        raise SyntaxError("Unknown statement: " + stmt)

    def _do_PRINT(self, toks):
        # Very basic PRINT: prints expressions and strings, supports ;
        out_parts = []
        i = 0
        sep = ' '
        while i < len(toks):
            t = toks[i]
            if t[0] == 'STRING':
                out_parts.append(t[1])
                i += 1
            else:
                # read tokens until semicolon
                sub = []
                while i < len(toks) and not (toks[i][0] == 'OP' and toks[i][1] == ';'):
                    sub.append(toks[i]); i += 1
                if sub:
                    try:
                        rpn = to_rpn(sub)
                    except RuntimeError as e:
                        self.output_callback(str(e).upper())
                        continue
                    v = eval_rpn(rpn, self.vars)
                    out_parts.append(str(v))
            if i < len(toks) and toks[i][0] == 'OP':
                op = toks[i][1]
                if op == ',':
                    sep = ' '
                elif op == ';':
                    sep = ''
                i += 1
        # join respecting sep: naive: join with sep between items
        if sep == '':
            self.output_callback(''.join(out_parts), end='')
        else:
            self.output_callback(sep.join(out_parts))

# -----------------------
# REPL
# -----------------------
def out_call(text):
    print(text)

def repl():
    bi = BasicInterpreter(out_call)
    print("Commodore 64-like BASIC in Python. Type line numbers to enter program, RUN, LIST, NEW, or immediate statements.\n")
    try:
        while True:
            try:
                s = input('] ')
            except EOFError:
                break
            bi.input_line(s)
    except KeyboardInterrupt:
        print("\nBye.")

if __name__ == '__main__':
    repl()
