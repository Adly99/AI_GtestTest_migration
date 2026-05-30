import os
import shutil

# Paths
image_src = r"C:\Users\abdoa\OneDrive\Documents\Random_Projects\AI_GtestTest_migration\C:\Users\abdoa\.gemini\antigravity\brain\8cb33407-6cf1-4452-9bd4-3c79930b2d7b\workflow_illustration_1780158900752.png"
if not os.path.exists(image_src):
    # Fallback to absolute path direct resolution if concatenation was slightly different
    image_src = r"C:\Users\abdoa\.gemini\antigravity\brain\8cb33407-6cf1-4452-9bd4-3c79930b2d7b\workflow_illustration_1780158900752.png"

workspace_dir = r"c:\Users\abdoa\OneDrive\Documents\Random_Projects\AI_GtestTest_migration"
image_dest = os.path.join(workspace_dir, "workflow_illustration.png")
doc_dest = os.path.join(workspace_dir, "AI_Unit_Test_Migration_Factory_Workflow.html")

# Copy the image
if os.path.exists(image_src):
    shutil.copy(image_src, image_dest)
    print(f"Copied image to: {image_dest}")
else:
    print(f"Error: Source image not found at {image_src}")

# Document HTML template
html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AI Unit Test Migration Factory Workflow</title>
    <style>
        body {
            font-family: "Segoe UI", Arial, sans-serif;
            line-height: 1.6;
            color: #333333;
            max-width: 900px;
            margin: 0 auto;
            padding: 40px 20px;
            background-color: #ffffff;
        }
        h1 {
            color: #1b365d;
            border-bottom: 2px solid #1b365d;
            padding-bottom: 10px;
            font-size: 28px;
        }
        h2 {
            color: #2c5282;
            margin-top: 30px;
            font-size: 20px;
            border-left: 4px solid #2c5282;
            padding-left: 10px;
        }
        h3 {
            color: #4a5568;
            font-size: 16px;
            margin-top: 20px;
        }
        p {
            margin: 10px 0;
            text-align: justify;
        }
        ul {
            margin: 10px 0 20px 20px;
        }
        li {
            margin-bottom: 8px;
        }
        .highlight {
            font-weight: bold;
            color: #2b6cb0;
        }
        .diagram-container {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background-color: #f7fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        .diagram-container img {
            max-width: 100%;
            height: auto;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
            border-radius: 4px;
        }
        .card {
            background-color: #ebf8ff;
            border-left: 4px solid #3182ce;
            padding: 15px;
            margin: 20px 0;
            border-radius: 0 4px 4px 0;
        }
        .card-title {
            font-weight: bold;
            color: #2b6cb0;
            margin-bottom: 5px;
        }
        .table-container {
            margin: 20px 0;
            border: 1px solid #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        th {
            background-color: #f7fafc;
            color: #4a5568;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f8fafc;
        }
    </style>
</head>
<body>

    <h1>AI Unit Test Migration Factory Workflow</h1>
    <p>This document presents the formal structural workflow of the <strong>AI Unit Test Migration Factory</strong>, detailing every trigger mechanism, specialist agent, execution harness, verification gate, and compliance KPI. This document can be directly opened and edited in Microsoft Word or Google Docs.</p>

    <div class="diagram-container">
        <h3 style="margin-top: 0; color: #2d3748;">Figure 1: End-to-End Workflow Architecture Diagram</h3>
        <img src="workflow_illustration.png" alt="AI Unit Test Migration Factory Workflow Diagram" />
    </div>

    <h2>Phase 1: Source Trigger & Orchestration</h2>
    
    <h3>Step 0. Source Change (Trigger)</h3>
    <p><span class="highlight">Role:</span> The entry gate for the workflow.</p>
    <p><span class="highlight">Details:</span> Detects when a C++ source file or header is modified or added in the workspace. It parses Abstract Syntax Trees (ASTs) or local dependencies to map target headers, find external linkages, and automatically identify the required scope of testing (e.g. which classes, methods, or functions need to be verified or mocked).</p>

    <h3>Step 1. AI Orchestrator (Central Dispatcher)</h3>
    <p><span class="highlight">Role:</span> The brain of the factory.</p>
    <p><span class="highlight">Details:</span> Enforces orchestration rules, routes specific code modification sub-tasks to dedicated specialist agents, and tracks generated headers, compilation flags, test assets, and reports. It acts as the gatekeeper, blocking human review loops if syntax verification checks fail or if test metrics indicate critical flaws.</p>

    <h2>Phase 2: Generate & Prepare</h2>

    <h3>Step 2. Mocks Agent</h3>
    <p><span class="highlight">Role:</span> Automates dependency isolation.</p>
    <p><span class="highlight">Details:</span> Generates mock classes using GoogleMock (MOCK_METHOD macros) to stub out dependency layers. It creates corresponding GTest test fixtures, constructor harnesses, and setup/teardown boilerplate code, and automatically generates or updates the C++ build targets (such as CMake files) to ensure correct linkage.</p>

    <h3>Step 3. bbrainy gtest</h3>
    <p><span class="highlight">Role:</span> Requirements and scenario analyzer.</p>
    <p><span class="highlight">Details:</span> Analyzes C++ implementation sources (.cpp files) and design specifications. It parses method bodies to extract branch paths and construct positive paths, negative paths, and edge-case candidates (e.g., pointer null checks, boundary checks, and empty strings).</p>

    <h3>Step 4. Unit Test Converter</h3>
    <p><span class="highlight">Role:</span> Test synthesizer.</p>
    <p><span class="highlight">Details:</span> Formulates the concrete GoogleTest code blocks matching the candidate scenarios. It organizes the test structure into Arrange, Act, and Assert comments, and uses modern, descriptive EXPECT_THAT matchers (e.g., testing Eq or ElementsAre) to yield precise logs during failures.</p>

    <div class="card">
        <div class="card-title">GoogleTest Best Practice Note</div>
        <p>Utilizing EXPECT_THAT matchers (such as Eq, Ne, ElementsAre, or Contains) rather than basic EXPECT_EQ assertions prevents implicit type conversions and yields descriptive failure diagnostics showing both the expected format and the actual returned value.</p>
    </div>

    <h2>Phase 3: Execute & Evidence</h2>

    <h3>Step 5. Build & Run Binary</h3>
    <p><span class="highlight">Role:</span> Validation engine.</p>
    <p><span class="highlight">Details:</span> Triggers available system compilers (Clang, GCC, MSVC) to compile the generated test suite, executes the compiled mock binary, and captures exit codes, standard streams, assertion states, and duration metrics.</p>

    <h3>Step 6. Excel Evidence</h3>
    <p><span class="highlight">Role:</span> Compliance and reporting.</p>
    <p><span class="highlight">Details:</span> Translates binary execution output logs into a highly structured, clean Excel spreadsheet mapping test statuses to design requirements for audit traceability.</p>

    <h3>Step 7. Human Review Gate</h3>
    <p><span class="highlight">Role:</span> Developer sign-off.</p>
    <p><span class="highlight">Details:</span> A senior engineer reviews the generated test package, compiler logs, and excel evidence. If approved, the package is merged; if rejected, it triggers feedback loops to regenerate mocks or tests.</p>

    <h2>Phase 4: Quality Review Board (Multi-Agent AI Review)</h2>
    <p>Prior to human gate approval, a board of specialized reviewer agents challenges the generated code to check for vulnerabilities, anti-patterns, and coverage gaps:</p>

    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Review Agent</th>
                    <th>Purpose</th>
                    <th>Detailed Review Tasks</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td class="highlight">Coverage Agent</td>
                    <td>Requirements Coverage</td>
                    <td>Verifies that tests test functional specifications, going beyond basic line/branch metrics.</td>
                </tr>
                <tr>
                    <td class="highlight">Efficiency Agent</td>
                    <td>Performance & ROI</td>
                    <td>Evaluates run-time execution speeds, deletes duplicate tests, and checks test maintenance ROI.</td>
                </tr>
                <tr>
                    <td class="highlight">Quality Agent</td>
                    <td>Mock Correctness</td>
                    <td>Checks mock expectation setups (ON_CALL, EXPECT_CALL cardinality, WillOnce, Return) and boundary limits.</td>
                </tr>
                <tr>
                    <td class="highlight">Risk Agent</td>
                    <td>Flakiness & Fragility</td>
                    <td>Analyzes race conditions, timing dependencies, hardcoded local paths, and unhandled exception branches.</td>
                </tr>
            </tbody>
        </table>
    </div>

    <h2>Workflow Outputs & KPIs</h2>
    <ul>
        <li><strong>CI-Ready Test Package:</strong> Complete set of compile-ready C++ source test files and build configuration files.</li>
        <li><strong>Evidence Spreadsheet:</strong> Detailed traceability matrix showing test coverage mapped to requirements and execution results.</li>
        <li><strong>Test Efficiency Score:</strong> Speed, low flakiness, and high value of assertions.</li>
        <li><strong>Success KPIs:</strong> Time reduction, absolute pass/fail verification evidence, regulatory readiness, and developer acceptance rate.</li>
    </ul>

</body>
</html>
"""

with open(doc_dest, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Generated Word-compatible document at: {doc_dest}")
