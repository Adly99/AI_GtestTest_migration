import unittest
import unittest.mock
import tempfile
import os
import shutil
from gtest_migration_factory.orchestrator.pipeline import run_pipeline

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.tmp_dir, "project")
        self.output_dir = os.path.join(self.tmp_dir, "output")
        os.makedirs(self.project_root)
        os.makedirs(self.output_dir)

        # Create a sample header inside project root
        self.header_path = os.path.join(self.project_root, "IService.h")
        self.header_content = """
        #pragma once
        namespace app {
            class IService {
            public:
                virtual ~IService() = default;
                virtual int RunTask(double ratio) = 0;
            };
        }
        """
        with open(self.header_path, "w", encoding="utf-8") as f:
            f.write(self.header_content)

        # Create CMakeLists.txt
        with open(os.path.join(self.project_root, "CMakeLists.txt"), "w", encoding="utf-8") as f:
            f.write("set(CMAKE_CXX_STANDARD 17)")

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_run_pipeline_success(self):
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=self.header_path,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["cxx_standard"], "17")
        
        # Check generated files
        gen_files = result["generated_files"]
        self.assertEqual(len(gen_files), 3)
        
        mock_hdr = os.path.join(self.output_dir, "IService.h")
        fixture_cpp = os.path.join(self.output_dir, "test_IService.cpp")
        cmake_file = os.path.join(self.output_dir, "GeneratedMocks.cmake")
        
        self.assertIn(mock_hdr, gen_files)
        self.assertIn(fixture_cpp, gen_files)
        self.assertIn(cmake_file, gen_files)
        
        # Verify mock header content
        with open(mock_hdr, "r", encoding="utf-8") as f:
            mock_content = f.read()
        self.assertIn("class MockIService : public IService", mock_content)
        self.assertIn("MOCK_METHOD(int, RunTask, (double ratio), (override));", mock_content)

        # Verify test fixture content
        with open(fixture_cpp, "r", encoding="utf-8") as f:
            fixture_content = f.read()
        self.assertIn("class IServiceTest : public ::testing::Test", fixture_content)

    def test_run_pipeline_all_and_exclude(self):
        # Create additional folders and header files
        subdir_ok = os.path.join(self.project_root, "src")
        subdir_skip = os.path.join(self.project_root, "build")
        os.makedirs(subdir_ok, exist_ok=True)
        os.makedirs(subdir_skip, exist_ok=True)
        
        header_ok = os.path.join(subdir_ok, "Engine.h")
        header_skip = os.path.join(subdir_skip, "Config.h")
        
        with open(header_ok, "w") as f:
            f.write("class Engine { public: virtual void Start() = 0; };")
        with open(header_skip, "w") as f:
            f.write("class Config { public: virtual void Load() = 0; };")
            
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            process_all=True,
            exclude_patterns="build",
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        
        # Output should have IService.h (from setUp) and Engine.h, but NOT Config.h
        gen_basenames = [os.path.basename(f) for f in result["generated_files"]]
        self.assertIn("IService.h", gen_basenames)
        self.assertIn("Engine.h", gen_basenames)
        self.assertNotIn("Config.h", gen_basenames)

    def test_run_pipeline_dry_run(self):
        # Create output directory path that does NOT exist
        fresh_output_dir = os.path.join(self.tmp_dir, "fresh_output_no_write")
        
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=fresh_output_dir,
            file_path=self.header_path,
            dry_run=True,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        # Under dry-run, output directory should NOT be created on disk
        self.assertFalse(os.path.exists(fresh_output_dir))
        # The list of files that would be generated is still populated in the returned result
        self.assertTrue(len(result["generated_files"]) > 0)

    @unittest.mock.patch("subprocess.run")
    def test_pipeline_self_healing_feedback_loop_override(self, mock_run):
        # Configure mock_run to:
        # 1. Return g++ version successfully (compiler detection)
        # 2. Return compilation failure with "marked 'override' but does not override" on first check
        # 3. Return compilation success on the second check (after self-healing)
        
        mock_version = unittest.mock.MagicMock()
        mock_version.returncode = 0
        
        mock_fail = unittest.mock.MagicMock()
        mock_fail.returncode = 1
        mock_fail.stderr = "error: 'Deposit' marked 'override' but does not override"
        
        mock_success = unittest.mock.MagicMock()
        mock_success.returncode = 0
        
        mock_run.side_effect = [mock_version, mock_fail, mock_success]
        
        header_path = os.path.join(self.project_root, "Account.h")
        header_content = "class Account { public: virtual bool Deposit(double amount) = 0; };"
        with open(header_path, "w", encoding="utf-8") as f:
            f.write(header_content)
            
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=header_path,
            verify_compile=True,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        
        # Verify that mock_run was called 3 times (version check, check 1 (fail), check 2 (success))
        self.assertEqual(mock_run.call_count, 3)

    def test_run_pipeline_with_cpp_source(self):
        # Create a header file and corresponding implementation file in the project
        header_path = os.path.join(self.project_root, "Account.h")
        cpp_path = os.path.join(self.project_root, "Account.cpp")
        
        header_content = """
        class Account {
        public:
            virtual bool Deposit(double amount) = 0;
        };
        """
        cpp_content = """
        #include "Account.h"
        bool Account::Deposit(double amount) {
            if (amount <= 0) {
                return false;
            }
            return true;
        }
        """
        
        with open(header_path, "w", encoding="utf-8") as f:
            f.write(header_content)
        with open(cpp_path, "w", encoding="utf-8") as f:
            f.write(cpp_content)
            
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=header_path,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        fixture_file = os.path.join(self.output_dir, "test_Account.cpp")
        self.assertTrue(os.path.exists(fixture_file))
        
        with open(fixture_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Assert that concrete test scenarios were generated instead of placeholders
        self.assertIn("TEST_F(AccountTest, Deposit_Success_DefaultBehavior)", content)
        self.assertIn("TEST_F(AccountTest, Deposit_EdgeCase_amountZeroOrLess)", content)

    def test_run_pipeline_preserve_structure(self):
        # Create a header file in a subdirectory of project root
        subdir = os.path.join(self.project_root, "src", "core")
        os.makedirs(subdir, exist_ok=True)
        header_path = os.path.join(subdir, "Worker.h")
        with open(header_path, "w", encoding="utf-8") as f:
            f.write("class Worker { public: virtual void DoWork() = 0; };")
            
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=header_path,
            preserve_structure=True,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        
        # Verify that directories are mirrored: output/src/core/Worker.h and output/src/core/test_Worker.cpp
        expected_mock_path = os.path.join(self.output_dir, "src", "core", "Worker.h")
        expected_fixture_path = os.path.join(self.output_dir, "src", "core", "test_Worker.cpp")
        
        self.assertTrue(os.path.exists(expected_mock_path))
        self.assertTrue(os.path.exists(expected_fixture_path))
        
        # Verify GeneratedMocks.cmake has relative paths
        cmake_file = os.path.join(self.output_dir, "GeneratedMocks.cmake")
        self.assertTrue(os.path.exists(cmake_file))
        with open(cmake_file, "r", encoding="utf-8") as f:
            cmake_content = f.read()
        self.assertIn("${CMAKE_CURRENT_LIST_DIR}/src/core/test_Worker.cpp", cmake_content.replace("\\", "/"))

    @unittest.mock.patch("subprocess.run")
    def test_custom_compiler_path(self, mock_run):
        # Setup mock compiler behavior
        mock_res = unittest.mock.MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res
        
        custom_compiler = os.path.join(self.tmp_dir, "my_special_compiler")
        
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=self.header_path,
            verify_compile=True,
            custom_compiler_path=custom_compiler,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        # Check that the mock run was called with the custom compiler
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], custom_compiler)

    @unittest.mock.patch("subprocess.run")
    def test_custom_clang_format_path(self, mock_run):
        mock_res = unittest.mock.MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res
        custom_clang_fmt = os.path.join(self.tmp_dir, "my_clang_format")
        
        result = run_pipeline(
            project_root=self.project_root,
            output_dir=self.output_dir,
            file_path=self.header_path,
            clang_format=True,
            custom_clang_format_path=custom_clang_fmt,
            verbose=True
        )
        
        self.assertEqual(result["status"], "success")
        # Check that subprocess.run was called with my_clang_format
        called_cmds = [call[0][0] for call in mock_run.call_args_list if call[0][0]]
        found = False
        for cmd in called_cmds:
            if cmd[0] == custom_clang_fmt:
                found = True
        self.assertTrue(found)

if __name__ == "__main__":
    unittest.main()
