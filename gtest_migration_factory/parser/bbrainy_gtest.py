import os
import re

class TestScenario:
    """Represents a specific test case scenario to be converted into GTest code."""
    def __init__(self, method_name, scenario_type, scenario_name, arrange_statements, act_statement, assert_statements):
        self.method_name = method_name
        self.scenario_type = scenario_type  # "positive", "negative", "edge_case"
        self.scenario_name = scenario_name
        self.arrange_statements = arrange_statements  # List of string declarations
        self.act_statement = act_statement            # Act execution statement string
        self.assert_statements = assert_statements    # List of expectation strings (EXPECT_THAT)

def find_brace_matched_block(text, start_pos):
    """
    Counts brace depth starting from start_pos to extract a matching brace block.
    Returns (start_idx, end_idx) or (None, None).
    """
    brace_idx = text.find("{", start_pos)
    if brace_idx == -1:
        return None, None
    
    depth = 1
    pos = brace_idx + 1
    n = len(text)
    while pos < n:
        char = text[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return brace_idx, pos
        pos += 1
    return None, None

def extract_method_body(cpp_content, class_name, method_name):
    """
    Finds the definition of class_name::method_name and extracts its body content.
    """
    # Regex matching ClassName::MethodName(
    pattern = r'\b' + re.escape(class_name) + r'::' + re.escape(method_name) + r'\s*\('
    match = re.search(pattern, cpp_content)
    if not match:
        return None
    
    brace_start, brace_end = find_brace_matched_block(cpp_content, match.end())
    if brace_start is not None and brace_end is not None:
        return cpp_content[brace_start + 1:brace_end]
    return None

def get_default_val_for_type(p_type):
    # Remove const and references to check the base type
    clean = p_type.replace("const", "").replace("&", "").strip()
    if "string" in clean:
        return '"test_val"'
    elif "*" in p_type:
        return "nullptr"
    elif "bool" in clean:
        return "true"
    elif any(t in clean for t in ("int", "double", "float", "size_t", "int32_t", "uint32_t")):
        return "10"
    return None

def generate_arg_declaration(p_type, p_name, override_val=None):
    # Determine base default value
    if override_val is not None:
        default_val = override_val
    else:
        default_val = get_default_val_for_type(p_type)
        
    if default_val is not None:
        if "&" in p_type:
            clean_type = p_type.replace("&", "").strip()
            return f"{clean_type} {p_name} = {default_val};", p_name
        else:
            return f"{p_type} {p_name} = {default_val};", p_name
    else:
        if "&" in p_type:
            clean_type = p_type.replace("&", "").strip()
            return f"{clean_type}* {p_name} = nullptr;", f"*{p_name}"
        elif "*" in p_type:
            return f"{p_type} {p_name} = nullptr;", p_name
        else:
            return f"{p_type} {p_name};", p_name

def get_type_default_assert_value(ret_type):
    if "bool" in ret_type:
        return "true"
    elif "*" in ret_type:
        return "nullptr"
    elif any(t in ret_type for t in ("int", "double", "float", "size_t", "int32_t", "uint32_t")):
        return "10"
    return "0"

def get_type_failure_assert_value(ret_type):
    if "bool" in ret_type:
        return "false"
    elif "*" in ret_type:
        return "nullptr"
    elif any(t in ret_type for t in ("int", "double", "float", "size_t", "int32_t", "uint32_t")):
        return "0"
    return "0"

def guess_mock_class_name(class_type):
    clean = re.sub(r'\b(const|volatile|struct|class)\b', '', class_type).replace('*', '').replace('&', '').strip()
    parts = clean.split("::")
    parts[-1] = "Mock" + parts[-1]
    return "::".join(parts)

def detect_dependency_calls(body_text, param_name):
    if not body_text:
        return []
    ptr_pattern = r'\b' + re.escape(param_name) + r'->([a-zA-Z0-9_]+)\s*\('
    obj_pattern = r'\b' + re.escape(param_name) + r'\.([a-zA-Z0-9_]+)\s*\('
    
    calls = []
    for m in re.finditer(ptr_pattern, body_text):
        calls.append(m.group(1))
    for m in re.finditer(obj_pattern, body_text):
        calls.append(m.group(1))
    return list(set(calls))

def build_scenario_args(method, body_text, overrides=None):
    if overrides is None:
        overrides = {}
        
    arrange_decls = []
    act_args = []
    expect_calls = []
    
    for idx, p in enumerate(method.params):
        p_name = p.get("name") or f"arg{idx}"
        p_type = p.get("type", "")
        
        if idx in overrides:
            override_val = overrides[idx]
            decl, expr = generate_arg_declaration(p_type, p_name, override_val=override_val)
            if decl:
                arrange_decls.append(decl)
            act_args.append(expr)
            continue
            
        # Detect smart pointers
        smart_ptr_match = re.search(r'std::(shared|unique)_ptr\s*<\s*([^>]+)\s*>', p_type)
        if smart_ptr_match:
            ptr_kind = smart_ptr_match.group(1)
            inner_type = smart_ptr_match.group(2).strip()
            mock_class = guess_mock_class_name(inner_type)
            is_ref = "&" in p_type
            clean_ptr_type = p_type.replace("&", "").strip()
            if ptr_kind == "shared":
                arrange_decls.append(f"{clean_ptr_type} {p_name} = std::make_shared<{mock_class}>();")
                act_args.append(p_name)
            else:
                arrange_decls.append(f"{clean_ptr_type} {p_name} = std::make_unique<{mock_class}>();")
                act_args.append(f"std::move({p_name})" if not is_ref else p_name)
            continue
            
        # Check if parameter has dependency calls
        dep_methods = detect_dependency_calls(body_text, p_name)
        if dep_methods:
            clean_type = re.sub(r'\b(const|volatile|struct|class)\b', '', p_type).replace('*', '').replace('&', '').strip()
            mock_class = guess_mock_class_name(clean_type)
            mock_var_name = f"mock_{p_name}"
            arrange_decls.append(f"{mock_class} {mock_var_name};")
            
            if "*" in p_type:
                arrange_decls.append(f"{p_type} {p_name} = &{mock_var_name};")
                act_args.append(p_name)
            elif "&" in p_type:
                act_args.append(mock_var_name)
            else:
                act_args.append(mock_var_name)
                
            for dm in dep_methods:
                expect_calls.append(f"EXPECT_CALL({mock_var_name}, {dm}(::testing::_)).Times(::testing::AtLeast(1));")
        else:
            decl, expr = generate_arg_declaration(p_type, p_name)
            if decl:
                arrange_decls.append(decl)
            act_args.append(expr)
            
    return arrange_decls, act_args, expect_calls

def analyze_method_body(method, body_text=None):
    """
    Analyzes C++ method signatures and extracted implementation bodies 
    to output specific Positive, Negative, and Edge Case scenarios.
    """
    scenarios = []
    
    # 1. Base/Positive Scenario Setup
    arrange_decls, act_args, expect_calls = build_scenario_args(method, body_text)
    full_arrange = arrange_decls + expect_calls
    args_str = ", ".join(act_args)
    ret_type = method.return_type
    
    if ret_type != "void":
        act_statement = f"{ret_type} actual = mock_instance.{method.name}({args_str});"
        assert_statements = [f"EXPECT_THAT(actual, Eq({get_type_default_assert_value(ret_type)}));"]
    else:
        act_statement = f"mock_instance.{method.name}({args_str});"
        assert_statements = ["// Verify side effects / interactions"]

    scenarios.append(TestScenario(
        method_name=method.name,
        scenario_type="positive",
        scenario_name="Success_DefaultBehavior",
        arrange_statements=full_arrange,
        act_statement=act_statement,
        assert_statements=assert_statements
    ))
    
    # Heuristic Branch Checking if implementation body is provided
    if body_text:
        # A. Pointer null pointer checks
        for idx, p in enumerate(method.params):
            p_name = p.get("name") or f"arg{idx}"
            p_type = p.get("type", "")
            if "*" in p_type:
                null_pattern = r'\b' + re.escape(p_name) + r'\s*(==\s*nullptr|==\s*NULL|==\s*0|!\s*' + re.escape(p_name) + r'\b)'
                if re.search(null_pattern, body_text) or re.search(r'!\s*' + re.escape(p_name) + r'\b', body_text):
                    neg_arrange, neg_args, neg_expects = build_scenario_args(method, body_text, overrides={idx: "nullptr"})
                    full_neg_arrange = neg_arrange + neg_expects
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify side effects of null handler"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="negative",
                        scenario_name=f"Failure_{p_name}Null",
                        arrange_statements=full_neg_arrange,
                        act_statement=neg_act,
                        assert_statements=neg_assert
                    ))

        # B. Numeric Bounds checks (negative/zero bounds checks)
        for idx, p in enumerate(method.params):
            p_name = p.get("name") or f"arg{idx}"
            p_type = p.get("type", "")
            if any(t in p_type for t in ("int", "double", "float", "size_t", "int32_t", "uint32_t")):
                lt_zero = r'\b' + re.escape(p_name) + r'\s*(<\s*0|<=\s*0|==\s*0)'
                if re.search(lt_zero, body_text):
                    neg_arrange, neg_args, neg_expects = build_scenario_args(method, body_text, overrides={idx: "0"})
                    full_neg_arrange = neg_arrange + neg_expects
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify edge case behavior"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="edge_case",
                        scenario_name=f"EdgeCase_{p_name}ZeroOrLess",
                        arrange_statements=full_neg_arrange,
                        act_statement=neg_act,
                        assert_statements=neg_assert
                    ))

        # C. String empty checks
        for idx, p in enumerate(method.params):
            p_name = p.get("name") or f"arg{idx}"
            p_type = p.get("type", "")
            if "string" in p_type:
                empty_pattern = r'\b' + re.escape(p_name) + r'\s*(\.\s*empty\s*\(\s*\)|==\s*""|==\s*\'\')'
                if re.search(empty_pattern, body_text):
                    neg_arrange, neg_args, neg_expects = build_scenario_args(method, body_text, overrides={idx: '""'})
                    full_neg_arrange = neg_arrange + neg_expects
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify empty string behavior"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="edge_case",
                        scenario_name=f"EdgeCase_{p_name}Empty",
                        arrange_statements=full_neg_arrange,
                        act_statement=neg_act,
                        assert_statements=neg_assert
                    ))

    return scenarios

def analyze_cpp_file(cpp_file_path, cpp_class):
    """
    Reads a C++ source file if available and extracts test scenarios for the specified class.
    """
    if not cpp_file_path or not os.path.exists(cpp_file_path):
        # Fallback to signature-only defaults if no file path provided
        scenarios = []
        for method in cpp_class.methods:
            scenarios.extend(analyze_method_body(method))
        return scenarios
        
    try:
        with open(cpp_file_path, "r", encoding="utf-8", errors="ignore") as f:
            cpp_content = f.read()
    except Exception:
        cpp_content = ""
        
    scenarios = []
    for method in cpp_class.methods:
        body = extract_method_body(cpp_content, cpp_class.name, method.name)
        scenarios.extend(analyze_method_body(method, body))
    return scenarios
