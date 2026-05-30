import re

# Token types enum-like strings
T_PREPROCESSOR = "PREPROCESSOR"
T_KEYWORD = "KEYWORD"
T_IDENTIFIER = "IDENTIFIER"
T_PUNCTUATION = "PUNCTUATION"
T_OPERATOR = "OPERATOR"
T_STRING = "STRING"
T_NUMBER = "NUMBER"
T_UNKNOWN = "UNKNOWN"

KEYWORDS = {
    "class", "struct", "namespace", "public", "private", "protected",
    "virtual", "const", "override", "explicit", "static", "inline",
    "using", "template", "typename", "void", "int", "double", "float", 
    "char", "bool", "std"
}

# Regex definitions
RE_PREPROCESSOR = r'#[a-zA-Z_][a-zA-Z0-9_]*.*'
RE_IDENTIFIER = r'[a-zA-Z_][a-zA-Z0-9_]*'
RE_STRING = r'"(?:[^"\\]|\\.)*"'
RE_NUMBER = r'\b\d+(?:\.\d+)?\b'
RE_OPERATOR_DOUBLE = r'::|&&|==|!=|<=|>=|->'
RE_PUNCTUATION = r'[{}(),;=<>\*&:]'

def strip_comments(source_code):
    """Strips C++ single-line and multi-line comments from code."""
    # Strip block comments
    pattern_block = re.compile(r'/\*.*?\*/', re.DOTALL)
    source_clean = pattern_block.sub('', source_code)
    # Strip line comments
    pattern_line = re.compile(r'//.*')
    source_clean = pattern_line.sub('', source_clean)
    return source_clean

class Token:
    def __init__(self, type_, value, line):
        self.type = type_
        self.value = value
        self.line = line

    def __repr__(self):
        return f"Token({self.type}, '{self.value}', line={self.line})"

def tokenize(source_code):
    """
    Tokenizes clean C++ source code into a list of Token objects.
    """
    clean_code = strip_comments(source_code)
    tokens = []
    
    # Compile regex rules
    rules = [
        (T_PREPROCESSOR, RE_PREPROCESSOR),
        (T_STRING, RE_STRING),
        (T_NUMBER, RE_NUMBER),
        (T_OPERATOR, RE_OPERATOR_DOUBLE),
        (T_PUNCTUATION, RE_PUNCTUATION),
        (T_IDENTIFIER, RE_IDENTIFIER),
    ]
    
    # Combined regex
    regex_parts = [f"(?P<{name}>{pattern})" for name, pattern in rules]
    combined_regex = re.compile("|".join(regex_parts))
    
    # Split source code into lines to track line numbers
    lines = clean_code.splitlines()
    
    for line_idx, line in enumerate(lines, 1):
        pos = 0
        while pos < len(line):
            # Skip whitespace
            match_space = re.match(r'\s+', line[pos:])
            if match_space:
                pos += match_space.end()
                continue
                
            match = combined_regex.match(line, pos)
            if match:
                group_name = match.lastgroup
                val = match.group(group_name)
                
                # Check if identifier is actually a keyword
                if group_name == T_IDENTIFIER and val in KEYWORDS:
                    tokens.append(Token(T_KEYWORD, val, line_idx))
                else:
                    tokens.append(Token(group_name, val, line_idx))
                
                pos += match.end() - pos
            else:
                # If character is unknown, record it and advance by 1
                val = line[pos]
                tokens.append(Token(T_UNKNOWN, val, line_idx))
                pos += 1
                
    return tokens
