import unittest
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

if __name__ == "__main__":
    unittest.main()
