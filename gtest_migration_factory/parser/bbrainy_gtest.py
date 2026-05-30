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
    if "string" in p_type:
        return '"test_val"'
    elif "*" in p_type:
        return "nullptr"
    elif "bool" in p_type:
        return "true"
    elif any(t in p_type for t in ("int", "double", "float", "size_t", "int32_t", "uint32_t")):
        return "10"
    return "0"

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

def analyze_method_body(method, body_text=None):
    """
    Analyzes C++ method signatures and extracted implementation bodies 
    to output specific Positive, Negative, and Edge Case scenarios.
    """
    scenarios = []
    
    # 1. Base/Positive Scenario Setup
    arrange_decls = []
    act_args = []
    
    for idx, p in enumerate(method.params):
        p_name = p.get("name") or f"arg{idx}"
        p_type = p.get("type", "")
        
        default_val = get_default_val_for_type(p_type)
        if default_val is not None:
            arrange_decls.append(f"{p_type} {p_name} = {default_val};")
            act_args.append(p_name)
        else:
            clean_type = p_type.replace("&", "").strip()
            arrange_decls.append(f"{clean_type} {p_name};")
            act_args.append(p_name)
            
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
        arrange_statements=arrange_decls,
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
                    neg_arrange = []
                    neg_args = []
                    for i, op in enumerate(method.params):
                        op_name = op.get("name") or f"arg{i}"
                        op_type = op.get("type", "")
                        if i == idx:
                            neg_arrange.append(f"{op_type} {op_name} = nullptr;")
                        else:
                            neg_arrange.append(f"{op_type} {op_name} = {get_default_val_for_type(op_type)};")
                        neg_args.append(op_name)
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify side effects of null handler"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="negative",
                        scenario_name=f"Failure_{p_name}Null",
                        arrange_statements=neg_arrange,
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
                    neg_arrange = []
                    neg_args = []
                    for i, op in enumerate(method.params):
                        op_name = op.get("name") or f"arg{i}"
                        op_type = op.get("type", "")
                        if i == idx:
                            neg_arrange.append(f"{op_type} {op_name} = 0;")
                        else:
                            neg_arrange.append(f"{op_type} {op_name} = {get_default_val_for_type(op_type)};")
                        neg_args.append(op_name)
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify edge case behavior"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="edge_case",
                        scenario_name=f"EdgeCase_{p_name}ZeroOrLess",
                        arrange_statements=neg_arrange,
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
                    neg_arrange = []
                    neg_args = []
                    for i, op in enumerate(method.params):
                        op_name = op.get("name") or f"arg{i}"
                        op_type = op.get("type", "")
                        if i == idx:
                            neg_arrange.append(f"{op_type} {op_name} = \"\";")
                        else:
                            neg_arrange.append(f"{op_type} {op_name} = {get_default_val_for_type(op_type)};")
                        neg_args.append(op_name)
                    
                    neg_act = f"{ret_type} actual = mock_instance.{method.name}({', '.join(neg_args)});" if ret_type != "void" else f"mock_instance.{method.name}({', '.join(neg_args)});"
                    neg_assert = [f"EXPECT_THAT(actual, Eq({get_type_failure_assert_value(ret_type)}));"] if ret_type != "void" else ["// Verify empty string behavior"]
                    
                    scenarios.append(TestScenario(
                        method_name=method.name,
                        scenario_type="edge_case",
                        scenario_name=f"EdgeCase_{p_name}Empty",
                        arrange_statements=neg_arrange,
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
