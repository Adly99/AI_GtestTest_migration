import unittest
import tempfile
import os
from gtest_migration_factory.parser.lexer import tokenize, strip_comments
from gtest_migration_factory.parser.cxx_standard_detector import detect_cxx_standard
from gtest_migration_factory.parser.cpp_parser import parse_header

class TestLexer(unittest.TestCase):
    def test_strip_comments(self):
        code = """
        // This is a line comment
        int a = 10; /* This is a
        block comment */
        """
        clean = strip_comments(code)
        self.assertNotIn("comment", clean)
        self.assertIn("int a = 10;", clean)

    def test_tokenize(self):
        code = "class Database { public: virtual void save() = 0; };"
        tokens = tokenize(code)
        values = [t.value for t in tokens]
        self.assertIn("class", values)
        self.assertIn("Database", values)
        self.assertIn("public", values)
        self.assertIn("virtual", values)

class TestCxxStandardDetector(unittest.TestCase):
    def test_detect_cxx_standard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmake_content = """
            cmake_minimum_required(VERSION 3.12)
            set(CMAKE_CXX_STANDARD 14)
            """
            with open(os.path.join(tmpdir, "CMakeLists.txt"), "w", encoding="utf-8") as f:
                f.write(cmake_content)
                
            std = detect_cxx_standard(tmpdir)
            self.assertEqual(std, "14")

class TestCppParser(unittest.TestCase):
    def test_parse_header_class_and_methods(self):
        header_code = """
        #ifndef MY_GUARD_H
        #define MY_GUARD_H
        #include <string>
        namespace utils {
            class IFormatter {
            public:
                virtual ~IFormatter() = default;
                virtual std::string Format(int val, const std::string& prefix) const = 0;
            };
        }
        #endif
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(ast.include_guard, "MY_GUARD_H")
            self.assertTrue(any("<string>" in inc for inc in ast.includes))
            self.assertEqual(len(ast.classes), 1)
            
            c = ast.classes[0]
            self.assertEqual(c.name, "IFormatter")
            self.assertEqual(c.namespace, "utils")
            self.assertEqual(len(c.methods), 1)
            
            m = c.methods[0]
            self.assertEqual(m.name, "Format")
            self.assertEqual(m.return_type, "std::string")
            self.assertTrue(m.is_const)
            self.assertTrue(m.is_pure_virtual)
            self.assertEqual(len(m.params), 2)
            self.assertEqual(m.params[0]["type"], "int")
            self.assertEqual(m.params[0]["name"], "val")
            self.assertEqual(m.params[1]["type"], "const std::string&")
            self.assertEqual(m.params[1]["name"], "prefix")
        finally:
            os.remove(tmp_path)

    def test_parse_header_advanced_scenarios(self):
        header_code = """
        #pragma once
        #include "LogProxy.h"
        namespace ptph {
            class ptpHandler {
            public:
                ptpHandler() = default;
                virtual ~ptpHandler() = default;
                
                static bool GetCurrentSynchronizedTime(uint64_t* current_time);
                virtual void AraTsyncInit();
                
                enum class State { OK, ERROR };
            };
            
            // Free functions inside namespace
            inline void GetPvisCfgData(struct PVISParamCFG& pvis_rbc_data);
            constexpr std::uint32_t GetSize() { return 10; }
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(len(ast.classes), 1)
            
            c = ast.classes[0]
            self.assertEqual(c.name, "ptpHandler")
            self.assertEqual(len(c.methods), 1)  # AraTsyncInit
            self.assertEqual(len(c.static_methods), 1)  # GetCurrentSynchronizedTime
            self.assertEqual(len(c.lifecycle_methods), 2)  # constructor, destructor
            self.assertEqual(len(c.public_declarations), 1)  # enum State
            
            # Verify static methods
            s_m = c.static_methods[0]
            self.assertEqual(s_m.name, "GetCurrentSynchronizedTime")
            self.assertTrue(s_m.is_static)
            
            # Verify free functions
            self.assertEqual(len(ast.free_functions), 2)
            
            f1 = ast.free_functions[0]
            self.assertEqual(f1.name, "GetPvisCfgData")
            self.assertEqual(f1.namespace, "ptph")
            self.assertFalse(f1.is_constexpr)
            
            f2 = ast.free_functions[1]
            self.assertEqual(f2.name, "GetSize")
            self.assertTrue(f2.is_constexpr)
            self.assertIn("return 10;", f2.body_text)
        finally:
            os.remove(tmp_path)

    def test_parse_default_arguments(self):
        header_code = """
        class Device {
        public:
            void Configure(int speed = 9600, const char* parity = "none");
        };
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            c = ast.classes[0]
            m = c.methods[0]
            self.assertEqual(len(m.params), 2)
            self.assertEqual(m.params[0]["type"], "int")
            self.assertEqual(m.params[0]["name"], "speed")
            self.assertEqual(m.params[0]["default"], "9600")
            
            self.assertEqual(m.params[1]["type"], "const char*")
            self.assertEqual(m.params[1]["name"], "parity")
            self.assertEqual(m.params[1]["default"], '"none"')
        finally:
            os.remove(tmp_path)

    def test_parse_template_class(self):
        header_code = """
        template <typename T, int N = 10>
        class Array {
        public:
            virtual T& Get(int index) = 0;
        };
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(len(ast.classes), 1)
            c = ast.classes[0]
            self.assertEqual(c.name, "Array")
            self.assertEqual(c.template_decl, "template<typename T, int N = 10>")
        finally:
            os.remove(tmp_path)

    def test_parse_noexcept_specifier(self):
        header_code = """
        class Processor {
        public:
            virtual void Run() noexcept = 0;
            virtual void Stop() = 0;
        };
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            c = ast.classes[0]
            m1 = c.methods[0]
            m2 = c.methods[1]
            self.assertEqual(m1.name, "Run")
            self.assertTrue(m1.is_noexcept)
            self.assertEqual(m2.name, "Stop")
            self.assertFalse(m2.is_noexcept)
        finally:
            os.remove(tmp_path)

    def test_parse_function_pointer_parameter(self):
        header_code = """
        class CallbackManager {
        public:
            virtual void Register(int (*callback)(double, int) = nullptr, void* user_data = nullptr) = 0;
        };
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            c = ast.classes[0]
            m = c.methods[0]
            self.assertEqual(len(m.params), 2)
            self.assertEqual(m.params[0]["type"], "int(*)(double, int)")
            self.assertEqual(m.params[0]["name"], "callback")
            self.assertEqual(m.params[0]["default"], "nullptr")
            self.assertEqual(m.params[1]["type"], "void*")
            self.assertEqual(m.params[1]["name"], "user_data")
            self.assertEqual(m.params[1]["default"], "nullptr")
        finally:
            os.remove(tmp_path)

    def test_parse_nested_class(self):
        header_code = """
        class Outer {
        public:
            struct Inner {
                int value;
            };
            virtual void Process(Inner in) = 0;
        };
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            # Both Outer and Inner classes should be parsed
            self.assertEqual(len(ast.classes), 2)
            c_outer = ast.classes[0]
            c_inner = ast.classes[1]
            self.assertEqual(c_outer.name, "Outer")
            self.assertEqual(c_inner.name, "Inner")
            
            # The Outer class should contain Process method (and not be cut off)
            self.assertEqual(len(c_outer.methods), 1)
            self.assertEqual(c_outer.methods[0].name, "Process")
        finally:
            os.remove(tmp_path)

    def test_parse_preprocessor_guards(self):
        header_code = """
        #ifdef ENABLE_FEATURE_A
        class FeatureClass {
        public:
            #if defined(DEBUG_MODE)
            virtual void DebugLog() = 0;
            #endif
            virtual void Run() = 0;
        };
        #endif
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(len(ast.classes), 1)
            c = ast.classes[0]
            self.assertEqual(c.name, "FeatureClass")
            self.assertEqual(c.preprocessor_guards, ["#ifdef ENABLE_FEATURE_A"])
            
            self.assertEqual(len(c.methods), 2)
            m_debug = c.methods[0]
            m_run = c.methods[1]
            self.assertEqual(m_debug.name, "DebugLog")
            self.assertEqual(m_debug.preprocessor_guards, ["#ifdef ENABLE_FEATURE_A", "#if defined(DEBUG_MODE)"])
            self.assertEqual(m_run.name, "Run")
            self.assertEqual(m_run.preprocessor_guards, ["#ifdef ENABLE_FEATURE_A"])
        finally:
            os.remove(tmp_path)

    def test_parse_namespace_declarations(self):
        header_code = """
        namespace sdk {
            using DeviceId = uint32_t;
            typedef char* BufferPtr;
        }
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(len(ast.namespace_declarations), 2)
            decl1 = ast.namespace_declarations[0]
            decl2 = ast.namespace_declarations[1]
            self.assertEqual(decl1["namespace"], "sdk")
            self.assertIn("using DeviceId = uint32_t", decl1["text"])
            self.assertEqual(decl2["namespace"], "sdk")
            self.assertIn("typedef char* BufferPtr", decl2["text"])
        finally:
            os.remove(tmp_path)

    def test_parse_preprocessor_guards_excludes_include_guards(self):
        header_code = """
        #ifndef CONTROLLER_H
        #define CONTROLLER_H
        
        #ifdef ENABLE_CONTROLLER
        class Controller {
        public:
            virtual void Initialize() = 0;
        };
        #endif
        
        #endif
        """
        with tempfile.NamedTemporaryFile(suffix=".h", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(header_code)
            tmp_path = tmp.name

        try:
            ast = parse_header(tmp_path)
            self.assertEqual(ast.include_guard, "CONTROLLER_H")
            self.assertEqual(len(ast.classes), 1)
            c = ast.classes[0]
            # Should filter out "#ifndef CONTROLLER_H", keeping only "#ifdef ENABLE_CONTROLLER"
            self.assertEqual(c.preprocessor_guards, ["#ifdef ENABLE_CONTROLLER"])
            self.assertEqual(len(c.methods), 1)
            m = c.methods[0]
            self.assertEqual(m.preprocessor_guards, ["#ifdef ENABLE_CONTROLLER"])
        finally:
            os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
