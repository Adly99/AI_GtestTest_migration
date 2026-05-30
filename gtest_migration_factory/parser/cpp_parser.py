import os
import re
from .lexer import tokenize, T_PREPROCESSOR, T_KEYWORD, T_IDENTIFIER, T_PUNCTUATION, T_OPERATOR, T_STRING

class Method:
    """Represents a C++ class member function."""
    def __init__(self, name, return_type, params, is_const=False, is_pure_virtual=False, 
                 is_override=False, is_static=False, is_constexpr=False, is_noexcept=False,
                 preprocessor_guards=None):
        self.name = name
        self.return_type = return_type
        self.params = params  # List of dicts: {"type": str, "name": str, "default": str/None}
        self.is_const = is_const
        self.is_pure_virtual = is_pure_virtual
        self.is_override = is_override
        self.is_static = is_static
        self.is_constexpr = is_constexpr
        self.is_noexcept = is_noexcept
        self.preprocessor_guards = preprocessor_guards if preprocessor_guards is not None else []

    def __repr__(self):
        return (f"Method({self.return_type} {self.name}({self.params}) "
                f"const={self.is_const} pure={self.is_pure_virtual} static={self.is_static} constexpr={self.is_constexpr} noexcept={self.is_noexcept})")

class FreeFunction:
    """Represents a C++ free function declared within a namespace."""
    def __init__(self, name, return_type, params, namespace, is_constexpr=False, body_text=None,
                 preprocessor_guards=None):
        self.name = name
        self.return_type = return_type
        self.params = params  # List of dicts: {"type": str, "name": str, "default": str/None}
        self.namespace = namespace
        self.is_constexpr = is_constexpr
        self.body_text = body_text  # Sliced raw body text for constexpr/inline preservation
        self.preprocessor_guards = preprocessor_guards if preprocessor_guards is not None else []

    def __repr__(self):
        return f"FreeFunction({self.return_type} {self.name}({self.params}) constexpr={self.is_constexpr})"

class Class:
    """Represents a C++ class or struct definition."""
    def __init__(self, name, namespace, is_struct=False, template_decl=None, preprocessor_guards=None):
        self.name = name
        self.namespace = namespace
        self.is_struct = is_struct
        self.template_decl = template_decl
        self.bases = []
        self.methods = []                # Public instance methods to mock
        self.static_methods = []         # Public static methods to mock via Singleton
        self.lifecycle_methods = []      # Constructors, destructors, operators (raw text)
        self.public_declarations = []     # Enums, typedefs, member variables (raw text)
        self.preprocessor_guards = preprocessor_guards if preprocessor_guards is not None else []
        self.start_line = 1

    def __repr__(self):
        return f"Class({self.namespace}::{self.name}, bases={self.bases}, methods={len(self.methods)}, static={len(self.static_methods)})"

class CppHeaderAST:
    """Root AST node representing a C++ header file."""
    def __init__(self):
        self.include_guard = None        # Name of original include guard
        self.includes = []               # List of raw include directives
        self.classes = []                # List of Class objects
        self.free_functions = []         # List of FreeFunction objects
        self.namespace_declarations = [] # List of dicts: {"namespace": str, "text": str, "preprocessor_guards": list}

def read_source_range(file_path, start_line, end_line):
    """
    Slices and returns raw lines from the original C++ file.
    Note: start_line and end_line are 1-indexed (inclusive).
    """
    if not os.path.exists(file_path):
        return ""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if start_line <= len(lines) and end_line <= len(lines):
            return "".join(lines[start_line - 1:end_line]).strip()
    except Exception:
        pass
    return ""

def consume_statement_tokens(tokens, start_pos):
    """
    Groups tokens matching a single C++ statement or block (ends with ';' or matching '}').
    Handles parenthesis and brace matching.
    
    Returns (statement_tokens, next_position).
    """
    pos = start_pos
    token_count = len(tokens)
    statement_tokens = []
    
    paren_depth = 0
    brace_depth = 0
    
    while pos < token_count:
        t = tokens[pos]
        statement_tokens.append(t)
        pos += 1
        
        if t.value == "(":
            paren_depth += 1
        elif t.value == ")":
            paren_depth -= 1
        elif t.value == "{":
            brace_depth += 1
        elif t.value == "}":
            brace_depth -= 1
            
        if brace_depth == 0 and paren_depth == 0:
            if t.value == ";":
                break
            if t.value == "}" and len(statement_tokens) > 1:
                # Ended at brace block close (like an inline function or enum definition)
                # Check for a trailing semicolon and consume it as part of this statement
                if pos < token_count and tokens[pos].value == ";":
                    statement_tokens.append(tokens[pos])
                    pos += 1
                break
                
    return statement_tokens, pos

def parse_header(file_path):
    """
    Parses a C++ header file and returns an enhanced CppHeaderAST.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        source_code = f.read()

    # 1. Regex metadata extraction (Include Guards and Include directives)
    ast = CppHeaderAST()
    
    match_ifndef = re.search(r'#ifndef\s+([a-zA-Z0-9_]+)', source_code)
    if match_ifndef:
        ast.include_guard = match_ifndef.group(1)

    # Find raw include lines (e.g. #include "LogProxy.h" or #include <vector>)
    raw_includes = re.findall(r'#include\s*(?:<[^>]+>|"[^"]+")', source_code)
    ast.includes = [inc.strip() for inc in raw_includes]

    # 2. Lexical Tokenization
    tokens = tokenize(source_code)
    pos = 0
    token_count = len(tokens)

    def get_guards():
        if not ast.include_guard:
            return list(preprocessor_stack)
        pattern = r'\b' + re.escape(ast.include_guard) + r'\b'
        return [g for g in preprocessor_stack if not re.search(pattern, g)]

    def peek(n=0):
        if pos + n < token_count:
            return tokens[pos + n]
        return None

    def consume():
        nonlocal pos
        t = peek()
        pos += 1
        return t

    # Scope tracking stacks
    namespace_stack = []
    scope_stack = []  # Stack of dicts: {"type": "namespace"/"class", "name": str, "brace_level": int}
    preprocessor_stack = []
    brace_level = 0
    
    current_class = None
    active_access = "private"  # "private", "public", "protected"
    last_template_decl = None

    while pos < token_count:
        t = peek()
        
        # Track preprocessor conditional blocks
        if t.type == T_PREPROCESSOR:
            val = t.value.strip()
            if not val.startswith("#include"):
                if val.startswith(("#if", "#ifdef", "#ifndef")):
                    preprocessor_stack.append(val)
                elif val.startswith("#elif"):
                    if preprocessor_stack:
                        preprocessor_stack.pop()
                    preprocessor_stack.append(val)
                elif val.startswith("#else"):
                    if preprocessor_stack:
                        preprocessor_stack.pop()
                    preprocessor_stack.append("#else")
                elif val.startswith("#endif"):
                    if preprocessor_stack:
                        preprocessor_stack.pop()
            consume()
            continue

        # Track template declarations preceding classes/structs
        if t.type == T_KEYWORD and t.value == "template":
            template_tokens = [t]
            consume()
            lt_depth = 0
            while pos < token_count:
                curr = peek()
                template_tokens.append(curr)
                consume()
                if curr.value == "<":
                    lt_depth += 1
                elif curr.value == ">":
                    lt_depth -= 1
                    if lt_depth == 0:
                        break
            last_template_decl = " ".join([tk.value for tk in template_tokens])
            last_template_decl = last_template_decl.replace(" < ", "<").replace(" >", ">").replace("< ", "<").replace(" , ", ", ").replace(" :: ", "::")
            continue

        # Brace tracking to handle namespace/class nesting
        if t.value == "{":
            brace_level += 1
            consume()
            continue

        if t.value == "}":
            if scope_stack and scope_stack[-1]["brace_level"] == brace_level:
                exited_scope = scope_stack.pop()
                if exited_scope["type"] == "namespace":
                    namespace_stack.pop()
                elif exited_scope["type"] == "class":
                    current_class = None
                    for scope in reversed(scope_stack):
                        if scope["type"] == "class":
                            current_class = scope.get("class_obj")
                            break
            brace_level -= 1
            consume()
            continue

        # Namespace parsing
        if t.type == T_KEYWORD and t.value == "namespace":
            consume()
            ns_name_parts = []
            while peek() and (peek().type == T_IDENTIFIER or peek().value == "::"):
                ns_name_parts.append(peek().value)
                consume()
            ns_name = "".join(ns_name_parts)
            
            if peek() and peek().value == ";":
                consume()
                continue
                
            namespace_stack.append(ns_name)
            scope_stack.append({
                "type": "namespace",
                "name": ns_name,
                "brace_level": brace_level + 1
            })
            continue

        # Class/Struct parsing
        if t.type == T_KEYWORD and t.value in ("class", "struct"):
            # Skip enum class / enum struct declarations
            if pos > 0 and tokens[pos - 1].value == "enum":
                consume()
                continue
                
            # A class/struct declaration MUST be followed by ';', ':', or '{' after the name (and macros)
            scan_pos = pos + 1
            # Skip export macros and name
            while scan_pos < token_count and tokens[scan_pos].type == T_IDENTIFIER:
                scan_pos += 1
            if scan_pos < token_count and tokens[scan_pos].value not in (";", ":", "{"):
                # Just a type reference (e.g. 'struct PVISParamCFG&'), not a declaration!
                consume()
                continue

            is_struct = (t.value == "struct")
            consume()
            
            # Skip export macros like MY_API
            while peek() and peek().type == T_IDENTIFIER and peek().value.isupper():
                consume()

            if not peek() or peek().type != T_IDENTIFIER:
                consume()
                continue

            class_name = peek().value
            consume()

            if peek() and peek().value == ";":
                consume()
                continue

            ns_prefix = "::".join(namespace_stack)
            new_class = Class(class_name, ns_prefix, is_struct, 
                              template_decl=last_template_decl, 
                              preprocessor_guards=get_guards())
            last_template_decl = None
            new_class.start_line = t.line
            ast.classes.append(new_class)
            current_class = new_class
            
            active_access = "public" if is_struct else "private"

            # Parse inheritance base classes
            if peek() and peek().value == ":":
                consume()
                while peek() and peek().value != "{":
                    if peek().value in ("public", "protected", "private", "virtual"):
                        consume()
                        continue
                    if peek().type == T_IDENTIFIER or peek().value == "::":
                        base_parts = []
                        while peek() and (peek().type == T_IDENTIFIER or peek().value == "::" or peek().value in ("<", ">", ",")):
                            base_parts.append(peek().value)
                            consume()
                        new_class.bases.append("".join(base_parts))
                    else:
                        consume()

            scope_stack.append({
                "type": "class",
                "name": class_name,
                "brace_level": brace_level + 1,
                "class_obj": new_class
            })
            continue

        # Parse elements within active classes or free functions within namespaces
        if current_class:
            # Check for access control labels (public:, private:, protected:)
            if t.type in (T_KEYWORD, T_IDENTIFIER) and t.value in ("public", "private", "protected"):
                if peek(1) and peek(1).value == ":":
                    active_access = t.value
                    consume()  # Consume keyword
                    consume()  # Consume ':'
                    continue

            # Process statements in public sections of classes
            if active_access == "public":
                # Consume a single full C++ statement
                statement_tokens, next_pos = consume_statement_tokens(tokens, pos)
                if statement_tokens:
                    pos = next_pos
                    
                    # Check if it contains a parameter list signature (has a parenthesis)
                    has_paren = any(tk.value == "(" for tk in statement_tokens)
                    
                    if has_paren:
                        # Parse function signature metadata
                        method_obj = parse_method_signature(statement_tokens, current_class.name, preprocessor_guards=get_guards())
                        if method_obj:
                            if method_obj.is_static:
                                current_class.static_methods.append(method_obj)
                            else:
                                current_class.methods.append(method_obj)
                        else:
                            # It is a lifecycle method (Constructor, Destructor, Operator)
                            # Slice it directly from source file to preserve exact signature
                            start_l = statement_tokens[0].line
                            end_l = statement_tokens[-1].line
                            raw_text = read_source_range(file_path, start_l, end_l)
                            if raw_text:
                                current_class.lifecycle_methods.append(raw_text)
                    else:
                        # Semicolon declarations, typedefs, enums, using, friend declarations, or public members
                        is_special_decl = any(tk.value in ("typedef", "enum", "using", "friend") for tk in statement_tokens)
                        start_l = statement_tokens[0].line
                        end_l = statement_tokens[-1].line
                        raw_text = read_source_range(file_path, start_l, end_l)
                        if raw_text and raw_text.strip() != ";":
                            current_class.public_declarations.append({
                                "is_special": is_special_decl,
                                "text": raw_text
                            })
                continue
        elif namespace_stack:
            # Parse free functions or namespace-level using-directives, typedefs
            if t.type in (T_KEYWORD, T_IDENTIFIER) or t.value == "~":
                statement_tokens, next_pos = consume_statement_tokens(tokens, pos)
                if statement_tokens:
                    has_paren = any(tk.value == "(" for tk in statement_tokens)
                    is_special = statement_tokens[0].value in ("using", "typedef")
                    
                    if has_paren and not is_special:
                        pos = next_pos
                        ns_name = "::".join(namespace_stack)
                        func_obj = parse_free_function(statement_tokens, ns_name, file_path, preprocessor_guards=get_guards())
                        if func_obj:
                            ast.free_functions.append(func_obj)
                        continue
                    
                    if is_special:
                        pos = next_pos
                        start_l = statement_tokens[0].line
                        end_l = statement_tokens[-1].line
                        raw_text = read_source_range(file_path, start_l, end_l)
                        if raw_text:
                            ast.namespace_declarations.append({
                                "namespace": "::".join(namespace_stack),
                                "text": raw_text,
                                "preprocessor_guards": get_guards()
                            })
                        continue
                        
        # Fallback consumer
        consume()

    return ast

def parse_method_signature(tokens, class_name, preprocessor_guards=None):
    """
    Parses a class member method signature.
    Returns None if signature represents a constructor, destructor, or operator overload.
    """
    open_paren_idx = -1
    close_paren_idx = -1
    paren_depth = 0

    for i, t in enumerate(tokens):
        if t.value == "(":
            if paren_depth == 0:
                open_paren_idx = i
            paren_depth += 1
        elif t.value == ")":
            paren_depth -= 1
            if paren_depth == 0:
                close_paren_idx = i
                break

    if open_paren_idx == -1 or close_paren_idx == -1:
        return None

    pre_paren = tokens[:open_paren_idx]
    
    # Analyze qualifiers before function name
    is_virtual = False
    is_static = False
    is_constexpr = False
    clean_pre = []
    for t in pre_paren:
        if t.value == "virtual":
            is_virtual = True
        elif t.value == "static":
            is_static = True
        elif t.value == "constexpr":
            is_constexpr = True
        else:
            clean_pre.append(t)

    if not clean_pre:
        return None

    method_name = clean_pre[-1].value
    
    # Skip constructors, destructors, and operators
    if method_name == class_name or method_name == f"~{class_name}" or any(t.value == "operator" for t in clean_pre):
        return None

    return_type_parts = [t.value for t in clean_pre[:-1]]
    return_type = " ".join(return_type_parts).replace(" :: ", "::").replace(" *", "*").replace(" &", "&")

    if is_virtual and not return_type:
        return_type = "int"

    # Parse parameter list
    param_tokens = tokens[open_paren_idx + 1:close_paren_idx]
    params = []
    
    current_param_tokens = []
    template_depth = 0
    paren_depth = 0
    
    for pt in param_tokens:
        if pt.value == "<":
            template_depth += 1
            current_param_tokens.append(pt)
        elif pt.value == ">":
            template_depth -= 1
            current_param_tokens.append(pt)
        elif pt.value == "(":
            paren_depth += 1
            current_param_tokens.append(pt)
        elif pt.value == ")":
            paren_depth -= 1
            current_param_tokens.append(pt)
        elif pt.value == "," and template_depth == 0 and paren_depth == 0:
            p = parse_single_parameter(current_param_tokens)
            if p:
                params.append(p)
            current_param_tokens = []
        else:
            current_param_tokens.append(pt)
            
    if current_param_tokens:
        p = parse_single_parameter(current_param_tokens)
        if p:
            params.append(p)

    # Parse post-parameter qualifiers (const, override, noexcept, pure virtual)
    post_paren = tokens[close_paren_idx + 1:]
    is_const = False
    is_override = False
    is_noexcept = False
    is_pure_virtual = False

    for idx, t in enumerate(post_paren):
        if t.value == "const":
            is_const = True
        elif t.value == "override":
            is_override = True
        elif t.value == "noexcept":
            is_noexcept = True
        elif t.value == "0" and idx > 0 and post_paren[idx - 1].value == "=":
            is_pure_virtual = True

    return Method(
        name=method_name,
        return_type=return_type if return_type else "void",
        params=params,
        is_const=is_const,
        is_pure_virtual=is_pure_virtual,
        is_override=is_override,
        is_static=is_static,
        is_constexpr=is_constexpr,
        is_noexcept=is_noexcept,
        preprocessor_guards=preprocessor_guards
    )

def parse_free_function(tokens, namespace, file_path, preprocessor_guards=None):
    """
    Parses a C++ free function signature declared inside a namespace.
    """
    open_paren_idx = -1
    close_paren_idx = -1
    paren_depth = 0

    for i, t in enumerate(tokens):
        if t.value == "(":
            if paren_depth == 0:
                open_paren_idx = i
            paren_depth += 1
        elif t.value == ")":
            paren_depth -= 1
            if paren_depth == 0:
                close_paren_idx = i
                break

    if open_paren_idx == -1 or close_paren_idx == -1:
        return None

    pre_paren = tokens[:open_paren_idx]
    is_constexpr = False
    is_inline = False
    clean_pre = []
    
    for t in pre_paren:
        if t.value == "constexpr":
            is_constexpr = True
        elif t.value == "inline":
            is_inline = True
        else:
            clean_pre.append(t)

    if not clean_pre:
        return None

    func_name = clean_pre[-1].value
    return_type_parts = [t.value for t in clean_pre[:-1]]
    return_type = " ".join(return_type_parts).replace(" :: ", "::").replace(" *", "*").replace(" &", "&")

    # Parse parameter list
    param_tokens = tokens[open_paren_idx + 1:close_paren_idx]
    params = []
    
    current_param_tokens = []
    template_depth = 0
    paren_depth = 0
    
    for pt in param_tokens:
        if pt.value == "<":
            template_depth += 1
            current_param_tokens.append(pt)
        elif pt.value == ">":
            template_depth -= 1
            current_param_tokens.append(pt)
        elif pt.value == "(":
            paren_depth += 1
            current_param_tokens.append(pt)
        elif pt.value == ")":
            paren_depth -= 1
            current_param_tokens.append(pt)
        elif pt.value == "," and template_depth == 0 and paren_depth == 0:
            p = parse_single_parameter(current_param_tokens)
            if p:
                params.append(p)
            current_param_tokens = []
        else:
            current_param_tokens.append(pt)
            
    if current_param_tokens:
        p = parse_single_parameter(current_param_tokens)
        if p:
            params.append(p)

    # Capture the inline/constexpr function body text if present
    body_text = None
    if tokens[-1].value == "}":
        # Scan backward or forward to find body start
        brace_open_idx = -1
        for idx, t in enumerate(tokens):
            if t.value == "{":
                brace_open_idx = idx
                break
        if brace_open_idx != -1:
            start_l = tokens[0].line
            end_l = tokens[-1].line
            body_text = read_source_range(file_path, start_l, end_l)

    return FreeFunction(
        name=func_name,
        return_type=return_type if return_type else "void",
        params=params,
        namespace=namespace,
        is_constexpr=is_constexpr,
        body_text=body_text,
        preprocessor_guards=preprocessor_guards
    )

def clean_type_spacing(param_type):
    # Order matters: replace paren/pointer constructs first before collapsing asterisks
    param_type = param_type.replace(" ( * )", "(*)").replace("(* )", "(*)").replace("( * )", "(*)").replace("( *", "(*")
    param_type = param_type.replace(" ( & )", "(&)").replace("(& )", "(&)").replace("( & )", "(&)").replace("( &", "(&")
    param_type = param_type.replace(" :: ", "::").replace(":: ", "::").replace(" ::", "::")
    param_type = param_type.replace(" *", "*").replace(" &", "&")
    param_type = param_type.replace(" ( ", "(").replace(" (", "(").replace("( ", "(")
    param_type = param_type.replace(" ) ", ")").replace(" )", ")").replace(") ", ")")
    param_type = param_type.replace(" < ", "<").replace("< ", "<").replace(" <", "<")
    param_type = param_type.replace(" > ", ">").replace("> ", ">").replace(" >", ">")
    param_type = param_type.replace(" , ", ", ").replace(" ,", ", ").replace(", ", ", ")
    return param_type.strip()

def parse_single_parameter(tokens):
    """
    Parses a single function parameter token list.
    Supports default values, nested templates formatting, and C-style function pointer arguments.
    Returns: {"type": str, "name": str, "default": str/None}
    """
    if not tokens:
        return None
        
    # Extract default parameter value if '=' is present
    default_val = None
    eq_idx = -1
    for idx, t in enumerate(tokens):
        if t.value == "=":
            eq_idx = idx
            break
            
    if eq_idx != -1:
        default_tokens = tokens[eq_idx + 1:]
        default_val = " ".join([t.value for t in default_tokens]).strip()
        default_val = default_val.replace(" :: ", "::").replace(" *", "*").replace(" &", "&")
        tokens = tokens[:eq_idx]

    if not tokens:
        return None

    # Function pointer parameter detection: e.g. void (*callback)(int, double)
    # Check for '(' followed by '*' (or '&') and an identifier (the parameter name) and ')'
    # and check if it is followed by '('
    fp_star_idx = -1
    for i in range(len(tokens) - 4):
        if tokens[i].value == "(" and tokens[i+1].value in ("*", "&") and tokens[i+2].type == T_IDENTIFIER and tokens[i+3].value == ")":
            if i + 4 < len(tokens) and tokens[i+4].value == "(":
                fp_star_idx = i
                break
                
    if fp_star_idx != -1:
        param_name = tokens[fp_star_idx + 2].value
        # Reconstruct type parts by omitting only the name token at fp_star_idx + 2
        type_parts = [t.value for t in tokens[:fp_star_idx + 2]] + [t.value for t in tokens[fp_star_idx + 3:]]
        param_type = " ".join(type_parts)
        param_type = clean_type_spacing(param_type)
        return {
            "type": param_type,
            "name": param_name,
            "default": default_val
        }

    # Standard parameter check
    last_tok = tokens[-1]
    if last_tok.type == T_IDENTIFIER and last_tok.value not in ("const", "volatile"):
        param_name = last_tok.value
        type_parts = [t.value for t in tokens[:-1]]
    else:
        param_name = ""
        type_parts = [t.value for t in tokens]

    param_type = " ".join(type_parts)
    param_type = clean_type_spacing(param_type)

    return {
        "type": param_type, 
        "name": param_name, 
        "default": default_val
    }
