import argparse
import sys
import os
from .orchestrator.pipeline import run_pipeline

def main():
    # If run with no arguments or explicitly requesting GUI, launch the Tkinter interface
    if len(sys.argv) == 1 or "--gui" in sys.argv:
        from .gui import launch_gui
        launch_gui()
        return

    parser = argparse.ArgumentParser(
        description="GTest Migration Factory: Automatically parse C++ interfaces and generate GoogleMock headers & GTest fixtures."
    )
    
    parser.add_argument(
        "--project-root",
        type=str,
        default=".",
        help="Path to the C++ project root directory (default: current directory)."
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Path to directory where mock headers and test fixtures should be saved."
    )
    
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to a specific C++ header file to process. If omitted, uses git to detect changed headers."
    )
    
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all C++ header files in the project root directory recursively (ignores Git status)."
    )
    
    parser.add_argument(
        "--exclude",
        type=str,
        default=None,
        help="Comma-separated list of path patterns/substrings to exclude (e.g. 'build,3rdparty,tests')."
    )
    
    parser.add_argument(
        "--cxx-standard",
        type=str,
        choices=["11", "14", "17", "20"],
        default=None,
        help="Target C++ standard version. If omitted, auto-detects from CMakeLists.txt."
    )
    
    parser.add_argument(
        "--keep-class-name",
        action="store_true",
        help="Preserve the exact same class name for generated mocks (useful for swap-linking stubs)."
    )
    
    parser.add_argument(
        "--mock-prefix",
        type=str,
        default="Mock",
        help="Prefix to append to the generated mock class names (default: 'Mock')."
    )
    
    parser.add_argument(
        "--mock-suffix",
        type=str,
        default="",
        help="Suffix to append to the generated mock class names (default: '')."
    )
    
    parser.add_argument(
        "--no-override",
        action="store_true",
        help="Omit 'override' specifier from mock method declarations."
    )
    
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Run validation and parser processes but skip writing output files to disk."
    )

    parser.add_argument(
        "--clang-format",
        "-F",
        action="store_true",
        help="Automatically format output files using local clang-format tool if available."
    )

    parser.add_argument(
        "--custom-include",
        type=str,
        default=None,
        help="Comma-separated list of custom headers/includes to prepend to all generated mocks."
    )

    parser.add_argument(
        "--namespace-filter",
        "-n",
        type=str,
        default=None,
        help="Limit mock generation only to classes and functions in the specified namespace."
    )

    parser.add_argument(
        "--compile-commands",
        type=str,
        default=None,
        help="Path to compile_commands.json directory or file to load include directories from."
    )

    parser.add_argument(
        "--verify-compile",
        action="store_true",
        help="Run compiler syntax check on generated mocks (requires g++, clang++, or cl in PATH)."
    )

    parser.add_argument(
        "--custom-compiler",
        type=str,
        default=None,
        help="Path to custom compiler binary (e.g. g++, clang++, cl)."
    )

    parser.add_argument(
        "--custom-clang-format",
        type=str,
        default=None,
        help="Path to custom clang-format binary."
    )

    parser.add_argument(
        "--no-preserve-structure",
        action="store_false",
        dest="preserve_structure",
        help="Disable mirroring project source relative directory layout in the output folder."
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed execution logs."
    )
    
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Launch the Graphical User Interface (GUI)."
    )

    parser.add_argument(
        "--checklist-filter",
        type=str,
        default=None,
        help="JSON string of classes and methods to generate (e.g. '{\"ClassName\":[\"method1\"]}')"
    )

    args = parser.parse_args()

    checklist_filter = None
    if args.checklist_filter:
        import json
        try:
            checklist_filter = json.loads(args.checklist_filter)
        except Exception as e:
            print(f"[Error] Failed to parse --checklist-filter: {e}", file=sys.stderr)
            sys.exit(1)

    # Validate directories
    if not os.path.isdir(args.project_root):
        print(f"[Error] Project root is not a valid directory: {args.project_root}", file=sys.stderr)
        sys.exit(1)

    print(f"=== GTest Migration Factory ===")
    print(f"Project Root: {args.project_root}")
    print(f"Output Dir:   {args.output_dir}")
    if args.file:
        print(f"Target File:  {args.file}")
    elif args.all:
        print(f"Target Mode:  All files recursively (exclude: {args.exclude})")
    else:
        print(f"Target Mode:  Changed/new headers via Git status")
    if args.dry_run:
        print(f"Execution:    DRY RUN (no files will be written)")
    if args.namespace_filter:
        print(f"Namespace Filter: {args.namespace_filter}")
    print(f"===============================")

    result = run_pipeline(
        project_root=args.project_root,
        output_dir=args.output_dir,
        file_path=args.file,
        cxx_standard=args.cxx_standard,
        keep_class_name=args.keep_class_name,
        verbose=args.verbose,
        process_all=args.all,
        exclude_patterns=args.exclude,
        mock_prefix=args.mock_prefix,
        mock_suffix=args.mock_suffix,
        no_override=args.no_override,
        dry_run=args.dry_run,
        clang_format=args.clang_format,
        custom_includes=args.custom_include,
        namespace_filter=args.namespace_filter,
        compile_commands=args.compile_commands,
        verify_compile=args.verify_compile,
        custom_compiler_path=args.custom_compiler,
        custom_clang_format_path=args.custom_clang_format,
        preserve_structure=args.preserve_structure,
        checklist_filter=checklist_filter
    )

    if result["status"] == "success":
        if args.dry_run:
            print("\nDry Run completed successfully!")
            print(f"Would process/generate {len(result['generated_files'])} files.")
        else:
            print("\nSuccess!")
            print(f"Detected C++ Standard: C++{result.get('cxx_standard', '17')}")
            print(f"Generated {len(result['generated_files'])} files:")
            for f in result["generated_files"]:
                print(f"  - {f}")
        sys.exit(0)
    else:
        print(f"\nExecution failed: {result.get('error', 'unknown error')}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
