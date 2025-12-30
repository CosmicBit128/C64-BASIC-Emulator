#include <unordered_set>
#include <unordered_map>
#include <iostream>
#include <variant>
#include <random>
#include <string>
#include <vector>
#include <regex>
#include <cctype>
#include <math.h>

enum class TokenType {
    NUMBER, STRING, BITWISE, NAME, OP, KEYWORD,
    FUNC, LPAREN, RPAREN, COMMA, SKIP, UNKNOWN
};

using TokenValue = std::variant <
    float,
    std::string
>;

struct TokenRule {
    TokenType type;
    std::regex pattern;
};

struct Token {
    TokenType type;
    TokenValue value;
    Token(TokenType type, TokenValue value) : type(type), value(value) {};
};

struct ForElement {
    std::string var;
    float end;
    float step;
    int index;
    ForElement(std::string var, float end, float step, int index) : var(var), end(end), step(step), index(index) {}
};

struct ProgramLine {
    int lineno;
    std::string line;
    ProgramLine(int lineno, std::string line) : lineno(lineno), line(line) {}
};



// -----------------------
// Helper functions
// -----------------------
float as_number(const TokenValue& v) {
    if (std::holds_alternative<float>(v))
    return std::get<float>(v);
    return 0.0;
}
std::string as_string(const TokenValue& v) {
    if (std::holds_alternative<std::string>(v))
        return std::get<std::string>(v);
    if (std::holds_alternative<float>(v))
        return std::to_string(std::get<float>(v));
    return "";
}

bool is_string_var(const std::string& name) {
    return !name.empty() && name.back() == '$';
}

void strip(std::string& s) {
    auto start = s.find_first_not_of(" \t\n\r\f\v");
    auto end   = s.find_last_not_of(" \t\n\r\f\v");

    if (start == std::string::npos) {
        s.clear(); // string was all whitespace
    } else {
        s = s.substr(start, end - start + 1);
    }
}

// -----------------------
// Lexer / tokenization
// -----------------------
std::vector<TokenRule> rules = {
    {TokenType::NUMBER,  std::regex(R"(\d+(\.\d*)?)")},
    {TokenType::STRING,  std::regex(R"(\"([^"]*)\")")},
    {TokenType::BITWISE, std::regex(R"(\b(AND|OR|NOT)\b)")},
    {TokenType::NAME,    std::regex(R"([A-Za-z][A-Za-z0-9\$]*)")},
    {TokenType::OP,      std::regex(R"(<=|>=|<>|[+\-*/\^=<>:;])")},
    {TokenType::LPAREN,  std::regex(R"(\()")},
    {TokenType::RPAREN,  std::regex(R"(\))")},
    {TokenType::COMMA,   std::regex(R"(,)")},
    {TokenType::SKIP,    std::regex(R"([ \t]+)")},
    {TokenType::UNKNOWN, std::regex(R"(.)")}
};

// Only for debugging
std::map<TokenType, std::string> token_translation = {
    {TokenType::NUMBER,  "Number"},
    {TokenType::STRING,  "String"},
    {TokenType::BITWISE, "Bitwise"},
    {TokenType::NAME,    "Name"},
    {TokenType::OP,      "Operator"},
    {TokenType::KEYWORD, "Keyword"},
    {TokenType::FUNC,    "Function"},
    {TokenType::LPAREN,  "Left Parentheses"},
    {TokenType::RPAREN,  "Right Parentheses"},
    {TokenType::COMMA,   "Comma"},
    {TokenType::SKIP,    "Skip"},
    {TokenType::UNKNOWN, "Unknown"}
};


std::unordered_set<std::string> KEYWORDS = {
    "PRINT","LET","INPUT","GOTO","IF","THEN","FOR","TO","STEP","NEXT",
    "GOSUB","RETURN","REM","END","STOP","DATA","READ","RESTORE","LIST","RUN","NEW"
};
std::unordered_map<std::string, int> FUNCS = {
    {"ABS",1}, {"ATN",1}, {"COS",1}, {"EXP",1}, {"INT",1},
    {"LOG",1}, {"SGN",1}, {"SIN",1}, {"SQR",1}, {"TAN",1},
    {"RND",1}, {"PEEK",1}, {"POS",0}, {"SPC",1}, {"TAB",1},
    {"ASC",1}, {"LEN",1}, {"VAL",1}, {"CHR$",1}, {"STR$",1},
    {"LEFT$",2}, {"MID$",3}, {"RIGHT$",2}
};

std::vector<Token> tokenize(std::string s) {
    std::vector<Token> tokens;
    int pos = 0;
    while (pos < s.length()) {

        bool matched = false;
        TokenType kind;
        std::string txt;
        for (auto& rule : rules) {
            std::smatch m;
            if (std::regex_search(s.cbegin() + pos, s.cend(), m, rule.pattern,
                  std::regex_constants::match_continuous)) {
                matched = true;

                kind = rule.type;
                txt = m[1];

                pos += m.length();
                break;
            }
        }
        if (!matched) {
            throw std::runtime_error("Tokenizer stuck");
        }
        if (kind == TokenType::SKIP) {
            continue;
        } else if (kind == TokenType::NUMBER) {
            float n = atof(txt.c_str());
            tokens.push_back(Token(kind, n));
        } else if (kind == TokenType::STRING) {
            tokens.push_back(Token(kind, txt));
        } else if (kind == TokenType::BITWISE) {
            tokens.push_back(Token(kind, txt));
        } else if (kind == TokenType::NAME) {
            std::string up = txt;
            transform(up.begin(), up.end(), up.begin(),
              ::toupper);
            if (KEYWORDS.find(up) != KEYWORDS.end()) {
                tokens.push_back(Token(TokenType::KEYWORD, up));
            } else if (FUNCS.find(up) != FUNCS.end()) {
                tokens.push_back(Token(TokenType::FUNC, up));
            } else {
                tokens.push_back(Token(TokenType::NAME, up));
            }
        } else if (kind == TokenType::OP || kind == TokenType::LPAREN || kind == TokenType::RPAREN || kind == TokenType::COMMA) {
            tokens.push_back(Token(kind, txt));
        } else {
            tokens.push_back(Token(TokenType::UNKNOWN, txt));
        }
    }

    return tokens;
}


// -----------------------
// Expression parser: Shunting-Yard -> RPN
// -----------------------

std::unordered_map<std::string, int> PREC = {
    {"^", 5}, {"*", 4}, {"/", 4}, {"+", 3}, {"-", 3},
    {"AND", 2}, {"OR", 2}, {"NOT", 2},
    {"=", 1}, {"<", 1}, {">", 1}, {"<=", 1}, {">=", 1}, {"<>", 1}
};
std::unordered_set<std::string> RIGHT_ASSOC = {"^"};

std::vector<Token> to_rpn(std::vector<Token> tokens) {
    std::vector<Token> out, stack;
    for (Token& t : tokens) {
        TokenType typ = t.type;
        TokenValue val = t.value;
        if (typ == TokenType::NUMBER || typ == TokenType::STRING || typ == TokenType::NAME || typ == TokenType::KEYWORD) {
            out.push_back(t);
        } else if (typ == TokenType::FUNC) {
            stack.push_back(t); // function will be handled as operator with args
        } else if (typ == TokenType::LPAREN) {
            stack.push_back(t);
        } else if (typ == TokenType::RPAREN) {
            while (!stack.empty() && stack.back().type != TokenType::LPAREN) {
                out.push_back(stack.back());
                stack.pop_back();
            }
            if (stack.empty()) {
                throw std::runtime_error("Mismatched parentheses");
            }
            stack.pop_back(); // remove LPAREN
            // If a function is on top, pop it to output
            if (!stack.empty() && stack.back().type != TokenType::FUNC) {
                out.push_back(stack.back());
                stack.pop_back();
            }
        } else if (typ == TokenType::OP) {
            while (!stack.empty() && stack.back().type != TokenType::OP) {
                TokenValue o2 = stack.back().value;
                int at_o2 = PREC.at(std::get<std::string>(o2));
                int at_val = PREC.at(std::get<std::string>(val));
                if (at_o2 > at_val && (at_o2 == at_val && RIGHT_ASSOC.find(std::get<std::string>(val)) == RIGHT_ASSOC.end())) {
                    out.push_back(stack.back());
                    stack.pop_back();
                } else break;
            }
            stack.push_back(t);
        } else if (typ == TokenType::BITWISE) {
            if (!stack.empty() && stack.back().type != TokenType::BITWISE) {
                out.push_back(stack.back());
                stack.pop_back();
            }
            stack.push_back(t);
        } else if (typ == TokenType::COMMA) {
            stack.push_back(t);
        } else {
            throw std::runtime_error("Unknown token type");
        }
    }

    while (!stack.empty()) {
        if (stack.back().type == TokenType::LPAREN || stack.back().type == TokenType::RPAREN) {
            throw std::runtime_error("Mismatched parentheses");
        }
        out.push_back(stack.back());
        stack.pop_back();
    }

    return out;
}



TokenValue eval_func(std::string name, std::vector<TokenValue> args) {
    std::string up = name;
    transform(up.begin(), up.end(), up.begin(),
    ::toupper);
    
    TokenValue v;
    try {
        if (name == "ABS") v = std::abs(as_number(args[0]));
        else if (name == "ATN") v = std::atan(as_number(args[0]));
        else if (name == "COS") v = std::cos(as_number(args[0]));
        else if (name == "EXP") v = std::exp(as_number(args[0]));
        else if (name == "INT") v = std::floor(as_number(args[0]));
        else if (name == "LOG") v = std::log(as_number(args[0]));
        else if (name == "SGN") v = as_number(args[0])==0 ? 0 : as_number(args[0]) / std::abs(as_number(args[0]));
        else if (name == "SIN") v = std::sin(as_number(args[0]));
        else if (name == "SQR") v = std::sqrt(as_number(args[0]));
        else if (name == "TAN") v = std::tan(as_number(args[0]));
        else if (name == "RND") {
            std::random_device rd;  
            std::mt19937 gen(rd()); // Mersenne Twister generator
            std::uniform_real_distribution<float> dist(0.0f, 1.0f);
            v = dist(gen);
        }
        else if (name == "SPC") v = std::string((int)as_number(args[0]), ' ');
        else if (name == "CHR$") v = (float)static_cast<char>((int)as_number(args[0]));
        else if (name == "STR$") v = as_string(args[0]);
        else if (name == "ASC") v = std::string(1, static_cast<char>(as_number(args[0])));
        else if (name == "LEN") v = (float)as_string(args[0]).length();
        else if (name == "VAL") v = as_number(args[0]);
        else if (name == "LEFT$") v = as_string(args[0]).substr(0, as_number(args[1]));
        else if (name == "RIGHT$") v = as_string(args[0]).substr((int)as_string(args[0]).length()-as_number(args[1]), as_number(args[1]));
        else if (name == "MID$") v = as_string(args[0]).substr(as_number(args[1]), as_number(args[2]));
    } catch (...) {
        throw std::runtime_error("Error at parsing function");
    }
    return v;
}

TokenValue eval_rpn(
    const std::vector<Token>& rpn,
    std::unordered_map<std::string, TokenValue>& env
) {
    std::vector<TokenValue> st;

    for (const Token& t : rpn) {
        const TokenType typ = t.type;
        const TokenValue& val = t.value;

        if (typ == TokenType::NUMBER || typ == TokenType::STRING) {
            st.push_back(val);
        }
        else if (typ == TokenType::NAME) {
            const std::string& name = std::get<std::string>(val);
            if (env.find(name) != env.end()) {
                st.push_back(env[name]);
            } else {
                if (is_string_var(name) || name == "SPC")
                    st.push_back(std::string{});
                else {
                    TokenValue v0 = (float)0.0;
                    st.push_back(v0);
                }
            }
        }
        else if (typ == TokenType::FUNC) {
            const std::string& fname = std::get<std::string>(val);
            int argc = FUNCS.at(fname);

            std::vector<TokenValue> args(argc);
            for (int i = argc - 1; i >= 0; --i) {
                args[i] = st.back();
                st.pop_back();
            }

            // placeholder — you’ll implement this
            st.push_back(eval_func(fname, args));
        }
        else if (typ == TokenType::OP) {
            const std::string& op = std::get<std::string>(val);

            if (op == "-" && st.size() == 1) {
                float a = as_number(st.back());
                st.pop_back();
                st.push_back(-a);
                continue;
            }

            float b = as_number(st.back()); st.pop_back();
            float a = as_number(st.back()); st.pop_back();

            float result;
            if      (op == "+")  result = a + b;
            else if (op == "-")  result = a - b;
            else if (op == "*")  result = a * b;
            else if (op == "/")  result = a / b;
            else if (op == "^")  result = std::pow(a, b);
            else if (op == "=")  result = a == b ? 1.0 : 0.0;
            else if (op == "<")  result = a <  b ? 1.0 : 0.0;
            else if (op == ">")  result = a >  b ? 1.0 : 0.0;
            else if (op == "<=") result = a <= b ? 1.0 : 0.0;
            else if (op == ">=") result = a >= b ? 1.0 : 0.0;
            else if (op == "<>") result = a != b ? 1.0 : 0.0;
            else
                throw std::runtime_error("Unknown operator: " + op);
            TokenValue v = (float) result;
            st.push_back(v);
        }
        else if (typ == TokenType::BITWISE) {
            const std::string& op = std::get<std::string>(val);

            if (op == "NOT") {
                TokenValue a = as_number(st.back());
                st.pop_back();
                st.push_back(TokenValue((float)(!as_number(a) ? 1.0 : 0.0)));
            } else {
                float b = as_number(st.back()); st.pop_back();
                float a = as_number(st.back()); st.pop_back();

                bool result;
                if      (op == "AND") result = a && b;
                else if (op == "OR")  result = a || b;
                else
                    throw std::runtime_error("Unknown bitwise op: " + op);
                TokenValue v = (float)(result ? 1.0 : 0.0);
                st.push_back(v);
            }
        }
        else if (typ == TokenType::COMMA) {
            // ignored in RPN evaluation
        }
        else {
            throw std::runtime_error("Unknown token type in eval");
        }
    }

    return st.empty() ? TokenValue{(float)0.0} : st.back();
}


// -----------------------
// Program storage and interpreter
// -----------------------
class BasicInterpreter {
private:
    std::vector<ProgramLine> program;
    std::unordered_map<std::string, TokenValue> vars;
    std::vector<ForElement> for_stack;
    std::vector<int> gosub_stack;
    int pc = 0;
    bool running = false;

    void exec_stmt_line(int lineno, std::string line, bool immediate = false) {
        std::vector<std::string> parts;
        std::string cur;
        bool in_str = false;

        for (const char& ch : line) {
            if (ch == '"') {
                in_str = !in_str;
                cur += ch;
            } else if (ch == ':' && !in_str) {
                strip(cur);
                parts.push_back(cur);
                cur = "";
            } else {
                cur += ch;
            }
        }
        strip(cur);
        if (!cur.empty()) parts.push_back(cur);
        for (const auto& stmt : parts) {
            if (immediate) {
                exec_stmt(stmt, -1);
            } else {
                exec_stmt(stmt, lineno);
            }
        }
    }

    void do_LIST() {
        for (const auto& line : program) {
            std::cout << line.lineno << " " << line.line << '\n';
        }
    }

    void do_RUN() {
        if (program.empty()) {
            output_callback("NO PROGRAM.");
            return;
        }
        vars.clear();
        for_stack.clear();
        pc = 0;
        running = true;

        while (running && 0 <= pc && pc < program.size()) {
            ProgramLine line = program[pc];
            int lineno = line.lineno;
            std::string rest = line.line;

            // Execute
            exec_stmt_line(lineno, rest);
            // pc_index is updated by statements (GOTO etc). If not changed, move to next
            if (running && pc < program.size() && program[pc].lineno == lineno) {
                pc++;
            }
        }
    }

    void do_PRINT(std::vector<Token> toks) {
        std::vector<std::string> out_parts;
        int i = 0;
        std::string sep = " ";
        while (i < toks.size()) {
            Token t = toks[i];
            if (t.type == TokenType::STRING) {
                out_parts.push_back(as_string(t.value));
                i++;
            } else {
                // read tokens until semicolon
                std::vector<Token> sub;
                while (i < toks.size() && !(toks[i].type == TokenType::OP && as_string(toks[i].value) == ";")) {
                    sub.push_back(toks[i]);
                    i++;
                }
                if (!sub.empty()) {
                    std::vector<Token> rpn = to_rpn(sub);
                    TokenValue v = eval_rpn(rpn, vars);
                    out_parts.push_back(as_string(v));
                }
            }
            if (i < toks.size() && toks[i].type == TokenType::OP) {
                std::string op = as_string(toks[i].value);
                if (op == ",") sep = " ";
                if (op == ";") sep = "";
                i++;
            }
        }
        std::string out_string;
        i = 0;
        for (const auto& part : out_parts) {
            out_string.append(part);
            if (i < out_parts.size()) out_string.append(sep);
            i++;
        }
        output_callback(out_string);
    }

    void exec_stmt(std::string stmt, int lineno) {
        /**
         * @param stmt   Statement
         * @param lineno Line Number
        */
        std::vector<Token> toks = tokenize(stmt);
        if (toks.empty()) return;
        Token first = toks[0];
        std::string first_v = std::get<std::string>(first.value);

        if (first_v == "REM") {
            return;
        } else if (first_v == "PRINT") {
            do_PRINT(std::vector(toks.begin()+1, toks.end()));
            return;
        }
        if (first_v == "LET") {
            // Skip LET
            toks = std::vector(toks.begin()+1, toks.end());
        } else if (toks.size() >= 3 && first.type == TokenType::NAME && toks[1].type == TokenType::OP && std::get<std::string>(toks[1].value) == "=") {
            // Assign variable
            std::vector<Token> rpn;
            try {
                rpn = to_rpn(std::vector(toks.begin()+2, toks.end()));
            } catch (std::runtime_error e) {
                std::cout << e.what() << std::endl;
            }
            TokenValue val = eval_rpn(rpn, vars);
            if (first_v[first_v.length()-1] == '$') {
                // String
                vars[first_v] = std::get<std::string>(toks[2].value);
            } else {
                // Number
                vars[first_v] = as_number(toks[2].value);
            }
            return;
        } else if (first_v == "INPUT") {
            // simplified: INPUT A,B$ -> prompt and assign
            std::string rest(stmt.begin()+5, stmt.end()); // Subtract the "INPUT" part (remove 5 chars)
            strip(rest);

            std::vector<std::string> names;
            std::stringstream ss(rest);
            std::string item;

            // Split by comma
            while (std::getline(ss, item, ',')) {
                strip(item);
                // Uppercase
                std::transform(item.begin(), item.end(), item.begin(), ::toupper);
                names.push_back(item);
            }

            for (const auto& nm : names) {
                if (nm[nm.length()-1] == '$') {
                    std::string v;
                    std::cout << "? ";
                    std::getline(std::cin, v);
                    vars[nm] = v;
                } else {
                    std::string v;
                    std::cout << "? ";
                    std::getline(std::cin, v);
                    try {
                        vars[nm] = TokenValue((float)std::stod(v.c_str()));
                    } catch (...) {
                        vars[nm] = TokenValue((float)0.0);
                    }
                }
            }
            return;
        } else if (first_v == "GOTO") {
            int goto_target = (int)as_number(toks[1].value);
            int idx = find_line_index(goto_target);
            if (idx == -1) {
                throw std::runtime_error("GOTO TO UNKNOWN line "+goto_target);
            }
            pc = idx;
            return;
        } else if (first_v == "GOSUB") {
            int goto_target = (int)as_number(toks[1].value);
            int idx = find_line_index(goto_target);
            if (idx == -1) {
                throw std::runtime_error("GOTO TO UNKNOWN line "+goto_target);
            }
            gosub_stack.push_back(pc+1);
            pc = idx;
            return;
        } else if (first_v == "RETURN") {
            if (gosub_stack.empty()) {
                throw std::runtime_error("RETURN WITHOUT GOSUB");
            }
            pc = gosub_stack[gosub_stack.size()-1];
            gosub_stack.pop_back();
            return;
        } else if (first_v == "IF") {
            // we expect: IF <expr> THEN <lineno>
            // find THEN token
            int then_idx = 0;
            for (const auto& t : toks) {
                if (t.type == TokenType::KEYWORD && std::get<std::string>(t.value) == "THEN")
                    break;
                then_idx++;
            }
            if (then_idx == toks.size()) {
                throw std::runtime_error("IF WITHOUT THEN");
            }
            // execute expression
            std::vector<Token> expr_toks(toks.begin()+1, toks.begin()+then_idx);
            std::vector<Token> rpn = to_rpn(expr_toks);
            TokenValue cond = eval_rpn(rpn, vars);
            if (as_number(cond) != (float)0.0 && as_string(cond) != "") {
                Token target_tok = toks[then_idx+1];
                int target = (int)as_number(target_tok.value);
                int idx = find_line_index(target);
                if (idx == -1) {
                    throw std::runtime_error("IF THEN to unknown line "+target);
                }
                pc = idx;
            }
            return;
        } else if (first_v == "FOR") {
            // parse roughly: FOR A = 1 TO 10 STEP 2
            // tokens layout: <NAME> <OP('=')> <expr> <TO> <expr>, [<STEP> <expr>]
            if (toks[1].type != TokenType::NAME || toks[2].type != TokenType::OP || std::get<std::string>(toks[2].value) != "=") {
                throw std::runtime_error("MALFORMED FOR");
            }
            std::string var = std::get<std::string>(toks[1].value);
            // find TO
            int to_idx = 0;
            for (const auto& t : toks) {
                if (t.type == TokenType::KEYWORD && std::get<std::string>(t.value) == "TO")
                    break;
                to_idx++;
            }
            if (to_idx == toks.size()) {
                throw std::runtime_error("FOR WITHOUT TO");
            }
            // find start
            std::vector<Token> rpn_start = to_rpn(std::vector(toks.begin()+3, toks.begin()+to_idx));
            TokenValue start = eval_rpn(rpn_start, vars);
            // find STEP if present
            bool has_step = std::any_of(toks.begin(), toks.end(), [](const auto& t) {
                if (t.type != TokenType::KEYWORD) return false;
                if (const std::string* val = std::get_if<std::string>(&t.value)) {
                    return *val == "STEP";
                }
                return false;
            });

            std::vector<Token> rpn_end;
            TokenValue step;
            if (has_step) {
                int step_idx = 0;
                for (const auto& t : toks) {
                    if (t.type == TokenType::KEYWORD && std::get<std::string>(t.value) == "TO")
                        break;
                    step_idx++;
                }
                rpn_end = to_rpn(std::vector(toks.begin()+to_idx+1, toks.end()+step_idx));
                std::vector<Token> rpn_step = to_rpn(std::vector(toks.begin()+step_idx+1, toks.end()));
                step = eval_rpn(rpn_step, vars);
            } else {
                rpn_end = to_rpn(std::vector(toks.begin()+to_idx+1, toks.end()));
            }
            TokenValue end = eval_rpn(rpn_end, vars);
            vars[var] = start;
            for_stack.push_back(ForElement(var, as_number(end), as_number(step), pc+1));
            return;
        } else if (first_v == "NEXT") {
            std::string var = toks.size() > 1 && toks[1].type == TokenType::NAME ? as_string(toks[1].value) : "";
            if (for_stack.empty()) {
                throw std::runtime_error("NEXT WITHOUT FOR");
            }
            ForElement f = for_stack[for_stack.size()-1];
            if (!var.empty() && var != f.var) {
                throw std::runtime_error("NEXT VARIABLE MISMATCH");
            }
            // Increment
            vars[f.var] = TokenValue(as_number(vars[f.var])+f.step);
            // check if loop continues (handle positive/negative step)
            bool cont = (f.step > 0 && as_number(vars[f.var]) <= f.end) || (f.step < 0 && as_number(vars[f.var]) >= f.end);
            if (cont) {
                // jump back to loop body (f.index)
                pc = f.index;
            } else {
                // pop and continue after NEXT (do nothing; loop will advance)
                for_stack.pop_back();
            }
            return;
        } else if (first_v == "END" || first_v == "STOP") {
            running = false;
            return;
        } else if (first_v == "NAME" || first_v == "NUMBER" || (first.type == TokenType::BITWISE && first_v == "NOT")) {
            std::vector<Token> rpn = to_rpn(toks);
            TokenValue val = eval_rpn(rpn, vars);
            return;
        }
        throw std::runtime_error("Unknown statement: "+stmt);
    }

    void output_callback(std::string text) {
        std::cout << text << std::endl;
    }

    int find_line_index(int line_target) {
        int i = 0;
        for (const auto& line : program) {
            if (line.lineno == line_target) return i;
            i++;
        }
        return -1;
    }

public:
    void input_line(std::string line) {
        if (line.length() == 0)
            return;
        strip(line);
        
        std::regex pattern = std::regex(R"(^\s*(\d+)\s*(.*)$)");
        std::smatch m;

        if (std::regex_search(line, m, pattern)) {
            int lineno = stoi(m[1].str());
            std::string rest = m[2].str();
            strip(rest);
            if (rest == "") {
                // Delete line
                auto it = std::find_if(program.begin(), program.end(),
                    [lineno](const ProgramLine& line) {
                        return line.lineno == lineno;
                    });

                if (it != program.end()) {
                    program.erase(it);
                }
            } else {
                program.push_back(ProgramLine(lineno, rest));
            }
        } else { // Immediate command
            std::string cmd = line;
            strip(cmd);
            transform(cmd.begin(), cmd.end(), cmd.begin(),
            ::toupper);
            if (cmd == "LIST") {
                do_LIST();
            } else if (cmd == "RUN") {
                do_RUN();
            } else if (cmd == "NEW") {
                program.clear();
                output_callback("PROGRAM CLEARED.");
            } else {
                exec_stmt_line(0, line, true);
            }
        }
    }

};


int main() {
    BasicInterpreter inter = BasicInterpreter();

    std::cout << "Commodore 64-like BASIC in C++. Type line numbers to enter program, RUN, LIST, NEW, or immediate statements." << std::endl;
    std::string s;
    while (true) {
        std::cout << "] ";
        try {
            std::getline(std::cin, s);
        } catch (std::runtime_error) {
            break;
        }
        inter.input_line(s);
    }

    return 0;
}
