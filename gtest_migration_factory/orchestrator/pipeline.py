import os
import sys
from ..parser.git_helper import get_modified_files
from ..parser.cxx_standard_detector import detect_cxx_standard
from ..parser.cpp_parser import parse_header
from ..generator.mock_generator import generate_mock_header, generate_test_fixture

def run_pipeline(project_root, output_dir, file_path=None, cxx_standard=None, 
                 keep_class_name=False, verbose=False, process_all=False, 
                 exclude_patterns=None, mock_prefix="Mock", mock_suffix="", 
                 no_override=False, dry_run=False, clang_format=False,
                 custom_includes=None, namespace_filter=None,
                 compile_commands=None, verify_compile=False):
    """
    Orchestrates the parser and generator steps with advanced options.
    """
    project_root = os.path.abspath(project_root)
    output_dir = os.path.abspath(output_dir)
    
    header_exts = (".h", ".hpp", ".hh", ".h++")
    
    # 0. Handle compile_commands.json if provided
    extra_search_paths = set()
    if compile_commands and os.path.exists(compile_commands):
        if verbose:
            print(f"[Orchestrator] Parsing compile_commands.json at: {compile_commands}")
        import json
        try:
            with open(compile_commands, "r", encoding="utf-8", errors="ignore") as f:
                commands = json.load(f)
            for cmd in commands:
                args = cmd.get("arguments", [])
                if not args and "command" in cmd:
                    args = cmd["command"].split()
                for idx, arg in enumerate(args):
                    if arg.startswith("-I"):
                        val = arg[2:].strip() or (args[idx+1].strip() if idx+1 < len(args) else "")
                        if val:
                            extra_search_paths.add(val)
                    elif arg == "-isystem" and idx+1 < len(args):
                        extra_search_paths.add(args[idx+1].strip())
            if verbose and extra_search_paths:
                print(f"[Orchestrator] Extra include search paths from compile_commands: {list(extra_search_paths)}")
        except Exception as e:
            print(f"[Warning] Failed to parse compile_commands.json: {e}", file=sys.stderr)

    # Parse exclude list
    exclude_list = []
    if exclude_patterns:
        exclude_list = [p.strip() for p in exclude_patterns.split(",") if p.strip()]
        if verbose:
            print(f"[Orchestrator] Exclude patterns: {exclude_list}")

    def is_excluded(path):
        normalized_path = os.path.abspath(path).replace("\\", "/").lower()
        for p in exclude_list:
            if p.lower() in normalized_path:
                return True
        return False

    # 1. C++ Standard Detection
    if not cxx_standard:
        detected_std = detect_cxx_standard(project_root)
        if verbose:
            print(f"[Orchestrator] Auto-detected C++ standard: C++{detected_std}")
        cxx_standard = detected_std
    else:
        if verbose:
            print(f"[Orchestrator] Using user-specified C++ standard: C++{cxx_standard}")

    # 2. Target File Identification
    target_files = []
    if file_path:
        # Explicit file mode (ignores diff and exclude)
        abs_file = os.path.abspath(file_path)
        if os.path.exists(abs_file):
            target_files.append(abs_file)
        else:
            print(f"[Error] Specified file does not exist: {file_path}", file=sys.stderr)
            return {"status": "error", "error": "file_not_found"}
    elif process_all:
        # Process all files recursively
        if verbose:
            print(f"[Orchestrator] Scanning project root recursively for all C++ headers...")
        for root, _, files in os.walk(project_root):
            for file in files:
                if file.lower().endswith(header_exts):
                    abs_path = os.path.abspath(os.path.join(root, file))
                    if not is_excluded(abs_path):
                        target_files.append(abs_path)
        if verbose:
            print(f"[Orchestrator] Found {len(target_files)} headers recursively (excluding matches).")
    else:
        # Detect changed files using Git
        if verbose:
            print(f"[Orchestrator] Scanning for changed C++ headers via Git status...")
        changed = get_modified_files(project_root)
        for f in changed:
            if f.lower().endswith(header_exts) and not is_excluded(f):
                target_files.append(f)
        if verbose:
            print(f"[Orchestrator] Found {len(target_files)} modified C++ headers (excluding matches).")

    if not target_files:
        if verbose:
            print("[Orchestrator] No C++ header files to process.")
        return {"status": "success", "generated_files": [], "msg": "No target files found."}

    # 3. Create Output Directory
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)

    generated_files = []
    
    # 4. Process each C++ header
    for header in target_files:
        basename = os.path.basename(header)
        if verbose:
            print(f"[Orchestrator] Parsing: {basename}...")

        try:
            ast = parse_header(header)
        except Exception as e:
            print(f"[Error] Failed to parse {basename}: {e}", file=sys.stderr)
            continue

        if not ast.classes and not ast.free_functions:
            if verbose:
                print(f"[Orchestrator] No classes, structs, or free functions found in {basename}.")
            continue

        # Check if the namespace filter filters out everything in the file
        if namespace_filter:
            ns_filter_norm = namespace_filter.strip(":")
            active_classes = [c for c in ast.classes if c.namespace.strip(":") == ns_filter_norm]
            active_funcs = [f for f in ast.free_functions if f.namespace.strip(":") == ns_filter_norm]
            if not active_classes and not active_funcs:
                if verbose:
                    print(f"[Orchestrator] Namespace filter '{namespace_filter}' filtered out all symbols in {basename}.")
                continue

        # A. Generate a single unified mock header for the entire file AST
        from ..generator.mock_generator import generate_mock_header_from_ast
        mock_hdr_content = generate_mock_header_from_ast(
            ast, 
            basename, 
            keep_class_name=keep_class_name,
            mock_prefix=mock_prefix,
            mock_suffix=mock_suffix,
            no_override=no_override,
            custom_includes=custom_includes,
            namespace_filter=namespace_filter
        )
        
        # Save the mock header file (same filename, inside the output directory)
        mock_hdr_path = os.path.join(output_dir, basename)
        if not dry_run:
            with open(mock_hdr_path, "w", encoding="utf-8") as f:
                f.write(mock_hdr_content)
            if verbose:
                print(f"    -> Generated Mock Header: {mock_hdr_path}")
        else:
            if verbose:
                print(f"    -> [Dry Run] Would generate Mock Header: {mock_hdr_path}")
        generated_files.append(mock_hdr_path)

        # B. Generate test fixtures for each class defined in the header
        for cpp_class in ast.classes:
            # Respect namespace filter for test fixtures
            if namespace_filter and cpp_class.namespace.strip(":") != namespace_filter.strip(":"):
                continue

            if verbose:
                print(f"  - Found class: {cpp_class.name} in namespace '{cpp_class.namespace}'")

            name_without_ext = os.path.splitext(basename)[0]
            # If multiple classes exist, append class name to fixture filename
            if len(ast.classes) > 1:
                fixture_name = f"test_{name_without_ext}_{cpp_class.name}.cpp"
            else:
                fixture_name = f"test_{name_without_ext}.cpp"
                
            fixture_path = os.path.join(output_dir, fixture_name)
            
            header_no_ext = os.path.splitext(header)[0]
            cpp_file_path = None
            for cpp_ext in (".cpp", ".cc", ".cxx", ".c++"):
                cand = header_no_ext + cpp_ext
                if os.path.exists(cand):
                    cpp_file_path = cand
                    break

            fixture_content = generate_test_fixture(
                cpp_class, 
                mock_hdr_path, 
                basename, 
                keep_class_name=keep_class_name,
                cpp_file_path=cpp_file_path
            )

            if not dry_run:
                with open(fixture_path, "w", encoding="utf-8") as f:
                    f.write(fixture_content)
                if verbose:
                    print(f"    -> Generated Test Fixture: {fixture_path}")
            else:
                if verbose:
                    print(f"    -> [Dry Run] Would generate Test Fixture: {fixture_path}")

            generated_files.append(fixture_path)

    # 5. Optional Clang-Format Post-processing
    if clang_format and not dry_run and generated_files:
        if verbose:
            print("[Orchestrator] Running clang-format on generated files...")
        import subprocess
        for path in generated_files:
            try:
                # Run clang-format command
                subprocess.run(["clang-format", "-i", path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if verbose:
                    print(f"  - Formatted: {os.path.basename(path)}")
            except (subprocess.SubprocessError, FileNotFoundError):
                print(f"[Warning] Could not format {os.path.basename(path)}: clang-format tool not found on PATH.", file=sys.stderr)
                break  # don't spam if tool is missing

    # 6. Generate GeneratedMocks.cmake (if not dry_run)
    if not dry_run and generated_files:
        cmake_file = os.path.join(output_dir, "GeneratedMocks.cmake")
        test_cpp_files = [f for f in generated_files if os.path.basename(f).startswith("test_") and f.endswith(".cpp")]
        
        cmake_lines = []
        cmake_lines.append("# Auto-generated list of mock test source files. Do not edit manually.")
        cmake_lines.append("set(GENERATED_MOCKS_SOURCES")
        for f in test_cpp_files:
            rel_name = os.path.basename(f)
            cmake_lines.append(f"    ${{CMAKE_CURRENT_LIST_DIR}}/{rel_name}")
        cmake_lines.append(")")
        
        try:
            with open(cmake_file, "w", encoding="utf-8") as cf:
                cf.write("\n".join(cmake_lines) + "\n")
            generated_files.append(cmake_file)
            if verbose:
                print(f"[Orchestrator] Generated CMake Integration helper: {cmake_file}")
        except Exception as e:
            print(f"[Warning] Failed to write GeneratedMocks.cmake: {e}", file=sys.stderr)

    # 7. Optional compiler verification check
    if verify_compile and not dry_run and generated_files:
        if verbose:
            print("[Orchestrator] Running syntax compilation check on generated mock headers...")
        import subprocess
        compiler = None
        for c in ("g++", "clang++", "cl"):
            try:
                subprocess.run([c, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                compiler = c
                break
            except FileNotFoundError:
                continue
                
        if compiler:
            if verbose:
                print(f"[Orchestrator] Using compiler: {compiler} for verification")
            headers_to_check = [f for f in generated_files if not os.path.basename(f).startswith("test_") and f.endswith(header_exts)]
            for hdr in headers_to_check:
                try:
                    cmd = [compiler, "-fsyntax-only", "-std=c++17", f"-I{project_root}", f"-I{output_dir}", hdr]
                    if compiler == "cl":
                        cmd = ["cl", "/Zs", f"/I{project_root}", f"/I{output_dir}", hdr]
                    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                    if result.returncode == 0:
                        if verbose:
                            print(f"  - Syntax OK: {os.path.basename(hdr)}")
                    else:
                        print(f"[Warning] Syntax errors in generated mock {os.path.basename(hdr)}:\n{result.stderr}", file=sys.stderr)
                except Exception as e:
                    print(f"[Warning] Verification compile failed for {os.path.basename(hdr)}: {e}", file=sys.stderr)
        else:
            if verbose:
                print("[Orchestrator] No compiler (g++, clang++, cl) found on PATH. Skipping syntax verification.")

    return {
        "status": "success",
        "cxx_standard": cxx_standard,
        "processed_headers": target_files,
        "generated_files": generated_files
    }
