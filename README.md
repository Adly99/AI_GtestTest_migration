# GTest Unit Test Migration Factory

A portable, zero-dependency C++ code parsing, test scenario analysis, and GoogleTest/GoogleMock code generation factory built in pure Python. It automatically scans codebase directories, detects modified files using Git, identifies project C++ standard configurations from build systems, parses C++ class declarations, extracts execution branch scenarios from C++ source files, and generates modern C++ GoogleMock headers and GoogleTest fixture templates.

This tool is designed to work in two ways:
1. **Interactive Desktop GUI Mode**: A polished, dark-themed Tkinter interface for local development, configuration, and real-time execution logging.
2. **Automated CLI Mode**: A scriptable command-line interface perfect for custom dev scripts, pre-commit hooks, or build pipelines (e.g., CI/CD or Git Submodule integration).

---

## Key Features

1. **Zero-Dependency AST C++ Parser (Step 0)**: Built entirely in Python. Does not require LLVM/Clang program binaries or DLLs, enabling it to run instantly on any machine with Python installed.
2. **Flexible Target Header Selection (Step 1)**:
   * **Git Change Detection**: Inspects local repository changes via git status to selectively compile mocks for only changed or added header files.
   * **All Headers Recursively (`--all`)**: Scans the entire project tree to migrate the entire codebase.
   * **Specific File**: Process a single C++ header file directly.
3. **Header-Replacement Mocking (Step 2)**:
   * Saves mock header files with the **exact same filename** as original headers, allowing you to swap production dependencies with mock stubs during test compilation using include path order.
   * Class naming flexibility: can generate mocks inheriting from interfaces or type stubs replacing the class definition directly (keeping the identical class name).
4. **Heuristic Scenario Analysis (Step 3 - bbrainy gtest)**:
   * Deep-analyzes C++ method implementation bodies using brace-matching algorithms.
   * Scans for specific branching conditions such as null pointer checks, numeric bounds (negative/zero constraints), and empty string checks.
   * Synthesizes tailored TestScenarios categorized into Positive, Negative, and Edge Case scenarios.
5. **GTest & GMock Synthesis (Step 4 - unit test converter)**:
   * Translates scenario metadata into complete C++ GoogleTest cases structured around the Arrange-Act-Assert pattern.
   * Generates readable assertions utilizing modern Matchers like `EXPECT_THAT(actual, Eq(expected))`.
6. **Orchestrator Self-Healing Feedback Loop**:
   * Auto-detects compiler toolchains (`g++`, `clang++`, `cl`).
   * Validates generated mock files via syntax-only compile checks.
   * Corrects compilation errors automatically (e.g. toggles `no_override` if an override mismatch occurs, or recursively locates missing C++ types in other headers and injects them into custom includes).
7. **C++ Standard Auto-Detection**: Automatically searches target project root files (like `CMakeLists.txt`) for compilation markers such as `CMAKE_CXX_STANDARD` or `cxx_std_*` to identify the C++ version (11, 14, 17, 20).
8. **Advanced Customization**:
   * **Custom Mock Naming**: Configure mock prefixes and suffixes (e.g., `MockIDatabase` or `IDatabaseStub`).
   * **No Override Toggle**: Expose option to omit `override` specifiers on generated mocks.
   * **Namespace Filter**: Limit mocking/testing to classes belonging to a specific namespace (e.g., `sdk::db`).
   * **Custom Includes**: Prepend additional header files to generated mocks.
9. **Quality of Life Features**:
   * **Clang-Format Integration**: Automatically runs `clang-format -i` on generated files if `clang-format` is available on the user's system.
   * **Dry Run Mode**: Scans, detects, and parses headers but bypasses writing to disk, listing all target paths and projected mock locations.

---

## C++ Mock Generation Workflow Rules

The generator conforms strictly to standard unit testing design paradigms:

### A. Static Class Methods
Static methods cannot be virtual or directly mocked using `MOCK_METHOD`. The generator wraps static methods by creating a companion singleton mock class (e.g., `ClassNameMock`) and delegating the static calls to it:
```cpp
// Original Code
class Calculator {
public:
    static int Add(int a, int b);
};

// Generated Mock Header
class CalculatorMock {
public:
    static CalculatorMock& getInstance(void) {
        static CalculatorMock instance;
        return instance;
    }
    MOCK_METHOD(int, Add, (int a, int b));
private:
    CalculatorMock(void) = default;
    ~CalculatorMock(void) = default;
};

class MockCalculator : public Calculator {
public:
    static int Add(int a, int b) {
        return CalculatorMock::getInstance().Add(a, b);
    }
};
```

### B. Free Functions in Namespaces
Similar to static methods, namespace-level free functions are mocked using a namespace-level companion singleton class named after the header file (e.g., `FilenameMock`), while keeping `constexpr` functions untouched:
```cpp
// Original Code
namespace math {
    int Multiply(int a, int b);
    constexpr int Subtract(int a, int b) { return a - b; }
}

// Generated Mock Header
namespace math {
    class MathOpsMock {
    public:
        static MathOpsMock& getInstance(void) {
            static MathOpsMock instance;
            return instance;
        }
        MOCK_METHOD(int, Multiply, (int a, int b));
    };

    inline int Multiply(int a, int b) {
        return MathOpsMock::getInstance().Multiply(a, b);
    }

    constexpr int Subtract(int a, int b) { return a - b; } // Preserved verbatim
}
```

### C. Default Parameters
GoogleMock does not support default arguments in `MOCK_METHOD`. The generator produces a mock for the full signature and creates non-virtual overloaded wrapper functions to resolve omitted parameters:
```cpp
// Original Code
virtual void Configure(int rate, bool enable = true, std::string mode = "fast") = 0;

// Generated Mock Header
MOCK_METHOD(void, Configure, (int rate, bool enable, std::string mode), (override));

void Configure(int rate, bool enable) {
    Configure(rate, enable, "fast");
}
void Configure(int rate) {
    Configure(rate, true, "fast");
}
```

### D. Private/Protected Stripping & Public Member Preservation
All private and protected fields/methods are completely stripped in the generated mocks. However, ancillary public declarations like nested enums, typedefs, using-directives, and public member variables are fully preserved:
```cpp
// Original Code
class Client {
public:
    enum class State { CONNECTED, DISCONNECTED };
    using ClientId = std::uint64_t;
    ClientId id;
private:
    void SendHeartbeat();
};

// Generated Mock Header
class MockClient : public Client {
public:
    enum class State { CONNECTED, DISCONNECTED };
    using ClientId = std::uint64_t;
    ClientId id;
};
```

---

## Directory Structure

```
gtest_migration_factory/
│
├── parser/
│   ├── git_helper.py             # Git status parsing for changed C++ headers
│   ├── cxx_standard_detector.py  # CMakeLists.txt scanner for C++ versions
│   ├── lexer.py                  # Comments-stripper & lexical tokenizer
│   ├── cpp_parser.py             # Scope and AST method extractor
│   └── bbrainy_gtest.py          # Heuristic implementation scan & scenario extractor
│
├── generator/
│   ├── mock_generator.py         # GoogleMock & GTest fixture C++ code generator
│   └── unit_test_converter.py    # Translates scenarios to GTest (Arrange/Act/Assert)
│
├── orchestrator/
│   └── pipeline.py               # Coordinates parser, generator, and feedback loop
│
├── gui.py                        # Tkinter dark-themed desktop app
└── cli.py                        # Command Line parser and launcher wrapper
```

---

## How to Run Everything

Ensure Python 3.10+ is installed on your system.

### 1. Running in Desktop GUI Mode

To launch the graphical desktop interface, run the module without any arguments or with the `--gui` flag:

```bash
# Option A: Run without arguments (launches GUI by default)
python -m gtest_migration_factory

# Option B: Run with the GUI flag
python -m gtest_migration_factory --gui
```

#### GUI Controls & Panels:
* **Configuration & Paths**:
  * **Project Root**: Select the target C++ repository path.
  * **Output Directory**: Define where generated mocks and test fixture `.cpp` files will be saved.
  * **Specific Header (Opt)**: Browse for a single specific file, or clear to run in a broader target mode.
* **Target Options**:
  * **Target Mode**: Radio buttons to choose between:
    * *Git Change Detection*: Process only headers modified/added in Git (default).
    * *Process All recursively (`--all`)*: Scan and migrate all C++ headers recursively.
    * *Specific File*: Direct targeted processing of the chosen header file.
* **Advanced Features Section**:
  * **Exclude Path Patterns**: Comma-separated strings (e.g. `build,tests,3rdparty`) to skip folders.
  * **Mock Prefix / Suffix**: Customize the output class name prefixes and suffixes.
  * **Custom Includes**: Inject additional include directives (comma-separated, e.g. `utils/test_helper.h`).
  * **Namespace Filter**: Match and mock only classes within a specific namespace scope.
* **Action Toggles**:
  * **C++ Standard**: dropdown to override CMake detection.
  * **Keep exact Class Name**: generate swap-link stubs.
  * **Omit Override**: skips `override` keywords in generated methods.
  * **Enable Clang-Format**: format generated code using system's `clang-format`.
  * **Dry Run**: Preview process without writing files to disk.
  * **Verbose Logs**: Enable logging statements in the text console.

---

### 2. Running in CLI (Script) Mode

To run in command-line mode, specify the required `--output-dir` parameter:

```bash
python -m gtest_migration_factory --output-dir <path_to_save_mocks> [options]
```

#### CLI Options:
* `-h, --help`: Show help description and exit.
* `--project-root`: Path to target C++ codebase (default: `.`).
* `--output-dir` (Required): Folder to save output stubs and test fixtures.
* `--file`: Run on a single file instead of Git diff.
* `--all`: Process all C++ header files recursively.
* `--exclude`: Comma-separated list of directories/substrings to exclude (e.g. `build,tests`).
* `--cxx-standard`: Override detected version (choices: `11`, `14`, `17`, `20`).
* `--keep-class-name`: Preserve class name (swap stub).
* `--mock-prefix`: Mock class name prefix (default: `"Mock"`).
* `--mock-suffix`: Mock class name suffix (default: `""`).
* `--no-override`: Omit `override` specifier from mock method declarations.
* `--dry-run`: Run validation and parser processes but skip writing output files to disk.
* `--clang-format`: Auto-format output files using local `clang-format` tool.
* `--custom-include`: Comma-separated list of custom headers to include.
* `--namespace-filter`: Limit mock generation to classes in a specific namespace.
* `--compile-commands`: Path to `compile_commands.json` database to load include directories from.
* `--verify-compile`: Run compiler syntax check on generated mocks (requires g++, clang++, or cl in PATH).
* `--verbose`: Print extra logging information.

#### Build & Verification Features:
* **CMake Integration Helper (`GeneratedMocks.cmake`)**: Upon successful generation, the tool automatically generates a `GeneratedMocks.cmake` helper listing all generated test fixture sources inside the output directory under `GENERATED_MOCKS_SOURCES`.
* **Compile Commands Parsing**: Specify `--compile-commands` to parse search paths from your build configuration.
* **Automated Syntax Checks**: Turn on `--verify-compile` to automatically compile-verify syntax of generated headers with available compiler toolchains (`g++`, `clang++`, `cl`).

#### Examples:
* **Recursive project scan with directory exclusions**:
  ```bash
  python -m gtest_migration_factory --project-root ./my_project --output-dir ./my_project/tests/mocks --all --exclude "build,external,tests"
  ```
* **Namespace filtering and custom prefix**:
  ```bash
  python -m gtest_migration_factory --output-dir ./stubs --all --namespace-filter "sdk::db" --mock-prefix "Stub"
  ```
* **Dry Run mode check**:
  ```bash
  python -m gtest_migration_factory --output-dir ./mocks --all --dry-run --verbose
  ```
* **Format generated files with clang-format**:
  ```bash
  python -m gtest_migration_factory --output-dir ./mocks --file ./include/IDevice.h --clang-format
  ```

---

### 3. Running Unit Tests

To run the factory's own test suite and verify parsing, standard detection, and generation:

```bash
python -m unittest discover -s tests
```

---

## Integration in C++ Projects

To integrate this tool as a submodule across multiple C++ repositories:

1. Add this repository as a Git Submodule pointing to the `master_integration` branch:
   ```bash
   git submodule add -b master_integration https://github.com/Adly99/AI_GtestTest_migration.git external/gtest_migration_factory
   ```
2. Build a python script wrapper or Makefile target in your main C++ project that calls `python -m gtest_migration_factory` before running CMake.

### Automated Compilation swapping via CMake
If you generate mocks with the same header names using the `--keep-class-name` flag, you can dynamically override production classes in unit tests by configuring your `CMakeLists.txt` include directories order:

```cmake
# CMakeLists.txt test target
add_executable(my_unit_tests
    test_main.cpp
    # Include test fixtures generated by the factory
    generated_mocks/test_IDatabase.cpp
)

target_include_directories(my_unit_tests PRIVATE
    # 1. Place the generated mocks folder FIRST to intercept headers
    generated_mocks
    
    # 2. Place standard include folders next
    include
)

target_link_libraries(my_unit_tests PRIVATE
    GTest::gtest
    GTest::gmock
    GTest::gmock_main
)
```
Whenever `test_main.cpp` compiles inside `my_unit_tests`, `#include "IDatabase.h"` resolves to the mock stub header in `generated_mocks` instead of the original header inside `include`.

---

## Branching & Contribution Policy

* **Default Branch**: The default development branch is **`master_integration`**.
* **Development Flow**:
  1. For any new feature, fix, or enhancement, always create a **new branch** off of `master_integration`:
     ```bash
     git checkout master_integration
     git pull origin master_integration
     git checkout -b feature/my-new-feature
     ```
  2. Implement changes, verify with unit tests (`python -m unittest discover tests`), and commit the updates to your branch.
  3. Push the feature branch to GitHub and create a **Pull Request (PR)** against the `master_integration` branch.
  4. After reviews and checks pass, merge the PR into `master_integration`.
