import os

def get_template_params(template_decl):
    if not template_decl:
        return ""
    start = template_decl.find("<")
    end = template_decl.rfind(">")
    if start == -1 or end == -1:
        return ""
    content = template_decl[start+1:end]
    params = []
    depth = 0
    curr = []
    for char in content:
        if char == "<":
            depth += 1
            curr.append(char)
        elif char == ">":
            depth -= 1
            curr.append(char)
        elif char == "," and depth == 0:
            params.append("".join(curr).strip())
            curr = []
        else:
            curr.append(char)
    if curr:
        params.append("".join(curr).strip())
        
    param_names = []
    for p in params:
        p = p.split("=")[0].strip()
        parts = p.split()
        if parts:
            param_names.append(parts[-1].strip("*&"))
    return ", ".join(param_names)

def wrap_lines_with_guards(lines_list, guards):
    if not guards:
        return lines_list
    wrapped = []
    for g in guards:
        wrapped.append(g)
    for line in lines_list:
        wrapped.append(line)
    for g in reversed(guards):
        if g.startswith("#ifdef"):
            cond = g[6:].strip()
            wrapped.append(f"#endif // {cond}")
        elif g.startswith("#ifndef"):
            cond = g[7:].strip()
            wrapped.append(f"#endif // !{cond}")
        elif g.startswith("#if"):
            cond = g[3:].strip()
            wrapped.append(f"#endif // {cond}")
        else:
            wrapped.append("#endif")
    return wrapped

def generate_mock_header_from_ast(ast, original_header_name, keep_class_name=False,
                                  mock_prefix="Mock", mock_suffix="", no_override=False,
                                  custom_includes=None, namespace_filter=None):
    """
    Generates a complete Mock header file following the GTest Mock Generation Workflow.
    """
    lines = []
    
    # 1. Preserve Include Guards (Step 2)
    guard = ast.include_guard if ast.include_guard else f"MOCK_{original_header_name.replace('.', '_').upper()}"
    lines.append(f"#ifndef {guard}")
    lines.append(f"#define {guard}")
    lines.append("// Original include guard - preserved.")
    lines.append("")
    
    # 2. Inject GMock/GTest Headers (Step 2)
    lines.append('#include "gmock/gmock.h"')
    lines.append('#include "gtest/gtest.h"')
    lines.append("// GMock and GTest includes added.")
    lines.append("")
    
    # 3. Preserve Original Includes (Step 2)
    ignored_includes = ('"gmock/gmock.h"', '"gtest/gtest.h"', '<gmock/gmock.h>', '<gtest/gtest.h>')
    added_includes = False
    for inc in ast.includes:
        header_path = inc.replace("#include", "").strip()
        if header_path not in ignored_includes:
            lines.append(f"{inc} // Original include - preserved.")
            added_includes = True
            
    if added_includes:
        lines.append("")

    # Inject Custom Includes
    if custom_includes:
        if isinstance(custom_includes, str):
            custom_includes = [c.strip() for c in custom_includes.split(",") if c.strip()]
        added_custom = False
        for inc in custom_includes:
            if not (inc.startswith('"') or inc.startswith('<')):
                inc = f'"{inc}"'
            lines.append(f"#include {inc} // Custom include.")
            added_custom = True
        if added_custom:
            lines.append("")

    # Namespace filter helper
    def match_namespace(item_ns, filter_ns):
        if not filter_ns:
            return True
        return item_ns.strip(":") == filter_ns.strip(":")

    filtered_classes = ast.classes
    filtered_free_functions = ast.free_functions
    if namespace_filter:
        filtered_classes = [c for c in ast.classes if match_namespace(c.namespace, namespace_filter)]
        filtered_free_functions = [f for f in ast.free_functions if match_namespace(f.namespace, namespace_filter)]

    # Identify all namespaces represented in classes, free functions and declarations
    namespaces = set()
    for c in filtered_classes:
        namespaces.add(c.namespace)
    for f in filtered_free_functions:
        namespaces.add(f.namespace)
    for d in ast.namespace_declarations:
        if not namespace_filter or match_namespace(d["namespace"], namespace_filter):
            namespaces.add(d["namespace"])

    # Helper to sort namespaces (outermost first)
    sorted_namespaces = sorted(list(namespaces), key=lambda x: len(x.split("::")) if x else 0)

    # For simplicity and clean structure, we group generation by namespace.
    for ns in sorted_namespaces:
        ns_list = ns.split("::") if ns else []
        for n in ns_list:
            if n:
                lines.append(f"namespace {n}")
                lines.append("{")
                lines.append("// Original namespace - preserved.")
                lines.append("")

        # C. Output namespace-level declarations (aliases, using, etc.)
        ns_decls = [d for d in ast.namespace_declarations if d["namespace"] == ns]
        for decl in ns_decls:
            decl_lines = [f"// Namespace declaration - preserved.", decl["text"], ""]
            decl_lines = wrap_lines_with_guards(decl_lines, decl.get("preprocessor_guards"))
            lines.extend(decl_lines)

        # A. Handling Free Functions in a Namespace (Step 4a)
        ns_free_funcs = [f for f in filtered_free_functions if f.namespace == ns]
        if ns_free_funcs:
            # Generate Companion Mock Class name from header filename
            base_filename = os.path.splitext(original_header_name)[0]
            # Convert snake_case or hyphen-case to CamelCase Mock suffix
            companion_class_name = "".join(w.capitalize() for w in base_filename.split("_")) + "Mock"
            
            func_class_lines = []
            func_class_lines.append("// A companion mock class is generated to allow mocking of free functions.")
            func_class_lines.append("// This singleton class provides a single point of access for tests to set")
            func_class_lines.append("// expectations on function calls.")
            func_class_lines.append(f"class {companion_class_name}")
            func_class_lines.append("{")
            func_class_lines.append("public:")
            func_class_lines.append("    // Provides global access to the single instance of this mock class.")
            func_class_lines.append(f"    static {companion_class_name}& getInstance(void)")
            func_class_lines.append("    {")
            func_class_lines.append(f"        static {companion_class_name} instance;")
            func_class_lines.append("        return instance;")
            func_class_lines.append("    }")
            func_class_lines.append("")
            
            # Companion Mock reset function
            func_class_lines.append("    // Reset all mock expectations set on this singleton instance.")
            func_class_lines.append("    static void reset(void)")
            func_class_lines.append("    {")
            func_class_lines.append("        ::testing::Mock::VerifyAndClearExpectations(&getInstance());")
            func_class_lines.append("    }")
            func_class_lines.append("")
            
            # Non-constexpr free functions are converted to MOCK_METHOD in singleton
            for f in ns_free_funcs:
                if not f.is_constexpr:
                    param_decls = []
                    for p in f.params:
                        name = p.get("name")
                        param_type = p.get("type", "")
                        if name:
                            param_decls.append(f"{param_type} {name}")
                        else:
                            param_decls.append(param_type)
                    params_str = ", ".join(param_decls)
                    
                    method_decl = [f"    MOCK_METHOD({f.return_type}, {f.name}, ({params_str}));"]
                    method_decl = wrap_lines_with_guards(method_decl, f.preprocessor_guards)
                    func_class_lines.extend(method_decl)
                    
            func_class_lines.append("")
            func_class_lines.append("private:")
            func_class_lines.append(f"    {companion_class_name}(void) = default;")
            func_class_lines.append(f"    {companion_class_name}(const {companion_class_name}&) = delete;")
            func_class_lines.append(f"    {companion_class_name}& operator=(const {companion_class_name}&) = delete;")
            func_class_lines.append(f"    ~{companion_class_name}(void) = default;")
            func_class_lines.append("};")
            func_class_lines.append("")
            lines.extend(func_class_lines)
            
            # Generate wrapper delegations and preserve constexpr functions
            for f in ns_free_funcs:
                func_lines = []
                if f.is_constexpr:
                    func_lines.append("// constexpr function - preserved.")
                    func_lines.append("// This function is evaluated at compile-time and cannot be mocked.")
                    if f.body_text:
                        func_lines.append(f"{f.body_text}")
                    else:
                        param_decls = []
                        for p in f.params:
                            name = p.get("name")
                            param_type = p.get("type", "")
                            if name:
                                param_decls.append(f"{param_type} {name}")
                            else:
                                param_decls.append(param_type)
                        params_str = ", ".join(param_decls)
                        func_lines.append(f"constexpr {f.return_type} {f.name}({params_str});")
                    func_lines.append("")
                else:
                    param_decls = []
                    for p in f.params:
                        name = p.get("name")
                        param_type = p.get("type", "")
                        if name:
                            param_decls.append(f"{param_type} {name}")
                        else:
                            param_decls.append(param_type)
                    params_str = ", ".join(param_decls)
                    
                    call_args = [p.get("name", f"arg{idx}") for idx, p in enumerate(f.params)]
                    call_args_str = ", ".join(call_args)
                    
                    func_lines.append("// The implementation of each original free function is replaced to call the mock instance, making it testable.")
                    func_lines.append(f"inline {f.return_type} {f.name}({params_str}) {{")
                    if f.return_type != "void":
                        func_lines.append(f"    return {companion_class_name}::getInstance().{f.name}({call_args_str});")
                    else:
                        func_lines.append(f"    {companion_class_name}::getInstance().{f.name}({call_args_str});")
                    func_lines.append("}")
                    func_lines.append("")
                
                # Wrap each function delegation in its active preprocessor guards
                func_lines = wrap_lines_with_guards(func_lines, f.preprocessor_guards)
                lines.extend(func_lines)

        # B. Output classes in this namespace
        ns_classes = [c for c in filtered_classes if c.namespace == ns]
        for cpp_class in ns_classes:
            mock_class_name = cpp_class.name if keep_class_name else f"{mock_prefix}{cpp_class.name}{mock_suffix}"
            
            # B1. Handling Static Class Methods (Step 4) - Generate companion mock class
            if cpp_class.static_methods:
                companion_class_name = f"{cpp_class.name}Mock"
                comp_class_lines = []
                comp_class_lines.append("// A companion mock class is generated to allow mocking of static methods.")
                comp_class_lines.append(f"class {companion_class_name}")
                comp_class_lines.append("{")
                comp_class_lines.append("public:")
                comp_class_lines.append(f"    static {companion_class_name}& getInstance(void)")
                comp_class_lines.append("    {")
                comp_class_lines.append(f"        static {companion_class_name} instance;")
                comp_class_lines.append("        return instance;")
                comp_class_lines.append("    }")
                comp_class_lines.append("")
                
                # Reset helper
                comp_class_lines.append("    // Reset all mock expectations set on this singleton instance.")
                comp_class_lines.append("    static void reset(void)")
                comp_class_lines.append("    {")
                comp_class_lines.append("        ::testing::Mock::VerifyAndClearExpectations(&getInstance());")
                comp_class_lines.append("    }")
                comp_class_lines.append("")
                
                # Mocks for static methods
                for m in cpp_class.static_methods:
                    param_decls = []
                    for p in m.params:
                        name = p.get("name")
                        param_type = p.get("type", "")
                        if name:
                            param_decls.append(f"{param_type} {name}")
                        else:
                            param_decls.append(param_type)
                    params_str = ", ".join(param_decls)
                    
                    method_decl = [f"    MOCK_METHOD({m.return_type}, {m.name}, ({params_str}));"]
                    method_decl = wrap_lines_with_guards(method_decl, m.preprocessor_guards)
                    comp_class_lines.extend(method_decl)
                    
                comp_class_lines.append("")
                comp_class_lines.append("private:")
                comp_class_lines.append(f"    {companion_class_name}(void) = default;")
                comp_class_lines.append(f"    {companion_class_name}(const {companion_class_name}&) = delete;")
                comp_class_lines.append(f"    {companion_class_name}& operator=(const {companion_class_name}&) = delete;")
                comp_class_lines.append(f"    ~{companion_class_name}(void) = default;")
                comp_class_lines.append("};")
                comp_class_lines.append("")
                
                # Wrap static companion mock in class's active preprocessor guards
                comp_class_lines = wrap_lines_with_guards(comp_class_lines, cpp_class.preprocessor_guards)
                lines.extend(comp_class_lines)

            # B2. Generate target Mock Class definition (Step 3, 5, 6, 7)
            class_lines = []
            class_lines.append("// Original class definition - transformed for GMock.")
            
            # Class templates prepending
            if cpp_class.template_decl:
                class_lines.append(cpp_class.template_decl)

            bases_str = ""
            if cpp_class.bases and not keep_class_name:
                bases_str = f" : public {', '.join(cpp_class.bases)}"
            elif not keep_class_name:
                if cpp_class.template_decl:
                    t_params = get_template_params(cpp_class.template_decl)
                    bases_str = f" : public {cpp_class.name}<{t_params}>"
                else:
                    bases_str = f" : public {cpp_class.name}"
                
            class_lines.append(f"class {mock_class_name}{bases_str}")
            class_lines.append("{")
            class_lines.append("public:")
            
            # Verify virtual destructor presence
            has_virtual_dest = False
            for lf in cpp_class.lifecycle_methods:
                if "~" in lf:
                    has_virtual_dest = True
                    break
            
            # Auto-generate a virtual destructor if there are virtual methods but no destructor defined
            if not has_virtual_dest and cpp_class.methods and not keep_class_name:
                class_lines.append(f"    virtual ~{mock_class_name}() = default;")
                class_lines.append("")

            # Preserve Original lifecycle methods (Step 6)
            for lifecycle in cpp_class.lifecycle_methods:
                class_lines.append(f"    // Original lifecycle method - preserved.")
                class_lines.append(f"    {lifecycle}")
                class_lines.append("")

            # Preserve static methods by delegating to companion mock (Step 4)
            for m in cpp_class.static_methods:
                static_method_lines = []
                param_decls = []
                for p in m.params:
                    name = p.get("name")
                    param_type = p.get("type", "")
                    if name:
                        param_decls.append(f"{param_type} {name}")
                    else:
                        param_decls.append(param_type)
                params_str = ", ".join(param_decls)
                
                call_args = [p.get("name", f"arg{idx}") for idx, p in enumerate(m.params)]
                call_args_str = ", ".join(call_args)
                
                static_method_lines.append("    // Static method - preserved and delegated to the singleton mock.")
                static_method_lines.append(f"    static {m.return_type} {m.name}({params_str})")
                static_method_lines.append("    {")
                companion_class_name = f"{cpp_class.name}Mock"
                if m.return_type != "void":
                    static_method_lines.append(f"        return {companion_class_name}::getInstance().{m.name}({call_args_str});")
                else:
                    static_method_lines.append(f"        {companion_class_name}::getInstance().{m.name}({call_args_str});")
                static_method_lines.append("    }")
                static_method_lines.append("")
                
                # Wrap each static delegation in its preprocessor guards
                static_method_lines = wrap_lines_with_guards(static_method_lines, m.preprocessor_guards)
                class_lines.extend(static_method_lines)

            # Mock public instance methods (Step 5)
            for m in cpp_class.methods:
                method_lines = []
                param_decls = []
                for p in m.params:
                    name = p.get("name")
                    param_type = p.get("type", "")
                    if name:
                        param_decls.append(f"{param_type} {name}")
                    else:
                        param_decls.append(param_type)
                params_str = ", ".join(param_decls)
                
                # Qualifiers
                specifiers = []
                if m.is_const:
                    specifiers.append("const")
                if m.is_noexcept:
                    specifiers.append("noexcept")
                if (m.is_override or not keep_class_name) and not no_override:
                    specifiers.append("override")
                    
                specifiers_str = ", ".join(specifiers)
                specifier_suffix = f", ({specifiers_str})" if specifiers else ""
                
                ret_type = m.return_type
                if "," in ret_type:
                    ret_type = f"({ret_type})"
                
                # Move-only return types warnings
                is_move_only = "unique_ptr" in m.return_type or "&&" in m.return_type
                if is_move_only:
                    method_lines.append("    // Note: Returns a move-only type. Set expectations using Return(ByMove(...)) or Invoke(...).")

                method_lines.append(f"    // Mock for the full method signature.")
                method_lines.append(f"    MOCK_METHOD({ret_type}, {m.name}, ({params_str}){specifier_suffix});")
                method_lines.append("")
                
                # B3. Handling Methods with Default Arguments (Step 5a)
                wrappers = generate_default_arg_wrappers(m)
                for wrap in wrappers:
                    method_lines.append(wrap)
                    method_lines.append("")
                
                # Wrap each method in its active preprocessor guards
                method_lines = wrap_lines_with_guards(method_lines, m.preprocessor_guards)
                class_lines.extend(method_lines)

            # Preserve public member types, enums, using directives (Step 8)
            for dec in cpp_class.public_declarations:
                dec_lines = []
                if dec["is_special"]:
                    dec_lines.append("    // Original declaration - preserved.")
                else:
                    dec_lines.append("    // Public member - preserved.")
                dec_lines.append(f"    {dec['text']}")
                dec_lines.append("")
                
                # Wrap in preprocessor guards if class declarations were wrapped
                dec_lines = wrap_lines_with_guards(dec_lines, dec.get("preprocessor_guards"))
                class_lines.extend(dec_lines)

            # Remove Private/Protected Sections (Step 7)
            class_lines.append("    // Private section and all its contents removed for mock generation.")
            class_lines.append("};")
            class_lines.append("")
            
            # Wrap the entire class block in its active preprocessor guards
            class_lines = wrap_lines_with_guards(class_lines, cpp_class.preprocessor_guards)
            lines.extend(class_lines)

        # Close active namespaces
        for n in reversed(ns_list):
            if n:
                lines.append(f"}} // namespace {n}")
                lines.append("")

    lines.append(f"#endif // {guard}")
    return "\n".join(lines) + "\n"

def generate_default_arg_wrappers(method):
    """
    Generates non-virtual overloaded wrapper functions to resolve C++ default parameters (Step 5a).
    """
    params = method.params
    n = len(params)
    
    # Find the index of the first parameter with a default value
    first_default_idx = -1
    for idx, p in enumerate(params):
        if p.get("default") is not None:
            first_default_idx = idx
            break
            
    if first_default_idx == -1:
        return []
        
    wrappers = []
    
    # Generate wrappers by omitting default parameters one by one from the right
    # (e.g. from omitting only the last parameter down to omitting all default parameters)
    for L in range(first_default_idx, n):
        # The wrapper accepts arguments from 0 to L-1
        wrapper_params = params[:L]
        param_decls = []
        for p in wrapper_params:
            name = p.get("name")
            param_type = p.get("type", "")
            if name:
                param_decls.append(f"{param_type} {name}")
            else:
                param_decls.append(param_type)
        param_decls_str = ", ".join(param_decls)
        
        # Omitted arguments are filled with their default values
        call_args = []
        for i in range(n):
            if i < L:
                # Pass original parameter by its name (or generate arg name if unnamed)
                call_args.append(params[i].get("name", f"arg{i}"))
            else:
                # Inject parsed default value
                call_args.append(params[i].get("default"))
        call_args_str = ", ".join(call_args)
        
        const_suffix = " const" if method.is_const else ""
        
        wrapper_lines = []
        wrapper_lines.append(f"    // Overloaded wrapper to handle calls using the default argument.")
        wrapper_lines.append(f"    {method.return_type} {method.name}({param_decls_str}){const_suffix}")
        wrapper_lines.append(f"    {{")
        if method.return_type != "void":
            wrapper_lines.append(f"        return {method.name}({call_args_str});")
        else:
            wrapper_lines.append(f"        {method.name}({call_args_str});")
        wrapper_lines.append(f"    }}")
        
        wrappers.append("\n".join(wrapper_lines))
        
    return wrappers

# Keep backwards compatibility wrappers for old unit tests
def generate_mock_header(cpp_class, original_header_name, keep_class_name=False):
    """
    Deprecated. Kept for unit testing support.
    Converts a single Class object to mock header.
    """
    from ..parser.cpp_parser import CppHeaderAST
    ast = CppHeaderAST()
    ast.classes.append(cpp_class)
    return generate_mock_header_from_ast(ast, original_header_name, keep_class_name)

def generate_test_fixture(cpp_class, mock_header_path, original_header_name, keep_class_name=False, cpp_file_path=None):
    """
    Generates a standard GTest unit test fixture file string.
    """
    from ..parser.bbrainy_gtest import analyze_cpp_file
    from .unit_test_converter import convert_scenarios_to_gtest

    mock_class_name = cpp_class.name if keep_class_name else f"Mock{cpp_class.name}"
    full_original_name = cpp_class.name
    full_mock_name = mock_class_name
    
    if cpp_class.namespace:
        full_original_name = f"{cpp_class.namespace}::{cpp_class.name}"
        full_mock_name = f"{cpp_class.namespace}::{mock_class_name}"
        
    lines = []
    lines.append("#include <gtest/gtest.h>")
    lines.append("#include <gmock/gmock.h>")
    
    mock_basename = os.path.basename(mock_header_path)
    lines.append(f'#include "{mock_basename}"')
    
    # If we kept the class name, we don't need both headers since mock header replaces the original header.
    # Otherwise, include the original header to reference the interface, unless it has the same name.
    if not keep_class_name and mock_basename != original_header_name:
        lines.append(f'#include "{original_header_name}"')
        
    lines.append("")
    lines.append("using ::testing::Eq;")
    lines.append("using ::testing::Ne;")
    lines.append("using ::testing::_;")
    lines.append("using ::testing::EXPECT_THAT;")
    lines.append("")
    
    # Test Fixture Class
    fixture_name = f"{cpp_class.name}Test"
    lines.append(f"class {fixture_name} : public ::testing::Test {{")
    lines.append("protected:")
    lines.append("    void SetUp() override {")
    lines.append("        // Setup test objects and dependencies")
    lines.append("    }")
    lines.append("")
    lines.append("    void TearDown() override {")
    lines.append("        // Cleanup test resources")
    lines.append("    }")
    lines.append("};")
    lines.append("")
    
    # Generate test cases using Unit Test Converter
    scenarios = analyze_cpp_file(cpp_file_path, cpp_class)
    test_cases_str = ""
    if scenarios:
        test_cases_str = convert_scenarios_to_gtest(scenarios, cpp_class.name, full_mock_name)
    else:
        # Fallback placeholder test
        fallback_lines = []
        fallback_lines.append(f"TEST_F({fixture_name}, DefaultConstructorBehavior) {{")
        fallback_lines.append("    // Arrange")
        fallback_lines.append(f"    {full_mock_name} mock_instance;")
        fallback_lines.append("")
        fallback_lines.append("    // Act & Assert placeholders")
        fallback_lines.append("    EXPECT_TRUE(true);")
        fallback_lines.append("}")
        test_cases_str = "\n".join(fallback_lines) + "\n"
        
    lines.append(test_cases_str)
    
    return "\n".join(lines) + "\n"
