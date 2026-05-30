import unittest
from gtest_migration_factory.parser.cpp_parser import Class, Method, FreeFunction, CppHeaderAST
from gtest_migration_factory.generator.mock_generator import (
    generate_mock_header_from_ast, 
    generate_test_fixture,
    generate_mock_header
)

class TestMockGenerator(unittest.TestCase):
    def setUp(self):
        self.cpp_class = Class("IDatabase", "sdk::db")
        self.cpp_class.methods.append(
            Method("Connect", "bool", [{"type": "const std::string&", "name": "conn"}], is_pure_virtual=True)
        )
        self.cpp_class.methods.append(
            Method("ExecuteQuery", "std::string", [{"type": "const std::string&", "name": "sql"}], is_const=True, is_pure_virtual=True)
        )

    def test_generate_mock_header_default(self):
        ast = CppHeaderAST()
        ast.classes.append(self.cpp_class)
        ast.includes.append('#include "LogProxy.h"')
        
        output = generate_mock_header_from_ast(ast, "IDatabase.h")
        
        self.assertIn("#ifndef MOCK_IDATABASE_H", output)
        self.assertIn("#define MOCK_IDATABASE_H", output)
        self.assertIn('#include "gmock/gmock.h"', output)
        self.assertIn('#include "gtest/gtest.h"', output)
        self.assertIn('#include "LogProxy.h" // Original include - preserved.', output)
        self.assertIn("class MockIDatabase : public IDatabase", output)
        self.assertIn("MOCK_METHOD(bool, Connect, (const std::string& conn), (override));", output)
        self.assertIn("MOCK_METHOD(std::string, ExecuteQuery, (const std::string& sql), (const, override));", output)

    def test_generate_mock_header_keep_class_name(self):
        ast = CppHeaderAST()
        ast.classes.append(self.cpp_class)
        output = generate_mock_header_from_ast(ast, "IDatabase.h", keep_class_name=True)
        
        self.assertIn("class IDatabase", output)
        self.assertNotIn("class MockIDatabase", output)

    def test_generate_test_fixture(self):
        output = generate_test_fixture(self.cpp_class, "mocks/IDatabase.h", "IDatabase.h")
        self.assertIn("#include <gtest/gtest.h>", output)
        self.assertIn('#include "IDatabase.h"', output)
        self.assertIn("class IDatabaseTest : public ::testing::Test", output)
        self.assertIn("sdk::db::MockIDatabase mock_instance;", output)

    def test_generate_mock_header_with_static_methods(self):
        # Create a class with static methods
        calculator_class = Class("Calculator", "core")
        calculator_class.static_methods.append(
            Method("Add", "int", [{"type": "int", "name": "a"}, {"type": "int", "name": "b"}], is_static=True)
        )
        calculator_class.methods.append(
            Method("Reset", "void", [], is_const=False)
        )
        
        ast = CppHeaderAST()
        ast.classes.append(calculator_class)
        
        output = generate_mock_header_from_ast(ast, "Calculator.h")
        
        # Verify companion mock class is created
        self.assertIn("class CalculatorMock", output)
        self.assertIn("static CalculatorMock& getInstance(void)", output)
        self.assertIn("MOCK_METHOD(int, Add, (int a, int b));", output)
        
        # Verify static method delegates to companion mock class
        self.assertIn("static int Add(int a, int b)", output)
        self.assertIn("return CalculatorMock::getInstance().Add(a, b);", output)
        
        # Verify instance methods are mocked as usual
        self.assertIn("MOCK_METHOD(void, Reset, (), (override));", output)

    def test_generate_mock_header_with_free_functions(self):
        # Create free functions inside a namespace
        func1 = FreeFunction("GetPvisData", "void", [{"type": "PVISParam&", "name": "data"}], "config")
        func2 = FreeFunction("GetExtrinsicsSize", "std::uint32_t", [], "config", is_constexpr=True, body_text="constexpr std::uint32_t GetExtrinsicsSize()\n{\n    return 42;\n}")
        
        ast = CppHeaderAST()
        ast.free_functions.extend([func1, func2])
        
        output = generate_mock_header_from_ast(ast, "coding_rbc_interfaces.h")
        
        # Verify companion mock class for free functions is created (camel-cased basename)
        self.assertIn("class CodingRbcInterfacesMock", output)
        self.assertIn("static CodingRbcInterfacesMock& getInstance(void)", output)
        self.assertIn("MOCK_METHOD(void, GetPvisData, (PVISParam& data));", output)
        
        # Verify inline delegation wrapper for free functions
        self.assertIn("inline void GetPvisData(PVISParam& data) {", output)
        self.assertIn("CodingRbcInterfacesMock::getInstance().GetPvisData(data);", output)
        
        # Verify constexpr functions are preserved as-is
        self.assertIn("constexpr std::uint32_t GetExtrinsicsSize()", output)
        self.assertIn("return 42;", output)
        self.assertNotIn("MOCK_METHOD(std::uint32_t, GetExtrinsicsSize", output)

    def test_generate_mock_header_with_default_arguments(self):
        # Method with default arguments
        db_class = Class("Database", "db")
        db_class.methods.append(
            Method(
                "Query", 
                "int", 
                [
                    {"type": "const std::string&", "name": "sql"}, 
                    {"type": "int", "name": "limit", "default": "10"},
                    {"type": "bool", "name": "cache", "default": "true"}
                ],
                is_const=True
            )
        )
        
        ast = CppHeaderAST()
        ast.classes.append(db_class)
        
        output = generate_mock_header_from_ast(ast, "Database.h")
        
        # Verify MOCK_METHOD is generated with full signature
        self.assertIn("MOCK_METHOD(int, Query, (const std::string& sql, int limit, bool cache), (const, override));", output)
        
        # Verify overloaded wrappers are generated to support omitted default args
        # Wrapper 1: Omit 'cache' (limit is provided)
        self.assertIn("int Query(const std::string& sql, int limit) const", output)
        self.assertIn("return Query(sql, limit, true);", output)
        
        # Wrapper 2: Omit both 'limit' and 'cache' (only sql is provided)
        self.assertIn("int Query(const std::string& sql) const", output)
        self.assertIn("return Query(sql, 10, true);", output)

    def test_generate_mock_header_custom_prefix_suffix_and_no_override(self):
        ast = CppHeaderAST()
        ast.classes.append(self.cpp_class)
        
        output = generate_mock_header_from_ast(
            ast, 
            "IDatabase.h", 
            keep_class_name=False,
            mock_prefix="Stub",
            mock_suffix="Test",
            no_override=True
        )
        
        self.assertIn("class StubIDatabaseTest : public IDatabase", output)
        # Verify MOCK_METHOD does not have override keyword
        self.assertIn("MOCK_METHOD(bool, Connect, (const std::string& conn));", output)
        self.assertNotIn("override", output)

    def test_generate_mock_header_custom_includes_and_namespace_filter(self):
        # Class in namespace db
        db_class = Class("Database", "sdk::db")
        db_class.methods.append(Method("GetVal", "int", [], is_pure_virtual=True))
        
        # Class in namespace ui
        ui_class = Class("Panel", "sdk::ui")
        ui_class.methods.append(Method("Draw", "void", [], is_pure_virtual=True))
        
        ast = CppHeaderAST()
        ast.classes.extend([db_class, ui_class])
        
        output = generate_mock_header_from_ast(
            ast, 
            "Mixed.h", 
            custom_includes=['"core/helper.h"', "<vector>"],
            namespace_filter="sdk::db"
        )
        
        # Custom includes should be injected
        self.assertIn('#include "core/helper.h" // Custom include.', output)
        self.assertIn('#include <vector> // Custom include.', output)
        
        # sdk::db class should be mocked
        self.assertIn("class MockDatabase : public Database", output)
        # sdk::ui class should be filtered out
        self.assertNotIn("class MockPanel", output)

    def test_generate_templated_mock(self):
        # Class with template declaration
        t_class = Class("Cache", "sdk", template_decl="template <typename Key, typename Value>")
        t_class.methods.append(Method("Get", "Value", [{"type": "const Key&", "name": "k"}], is_pure_virtual=True))
        
        ast = CppHeaderAST()
        ast.classes.append(t_class)
        
        output = generate_mock_header_from_ast(ast, "Cache.h")
        self.assertIn("template <typename Key, typename Value>", output)
        self.assertIn("class MockCache : public Cache<Key, Value>", output)
        self.assertIn("MOCK_METHOD(Value, Get, (const Key& k), (override));", output)

    def test_generate_noexcept_mock(self):
        n_class = Class("Worker", "sdk")
        n_class.methods.append(Method("Process", "void", [], is_noexcept=True, is_pure_virtual=True))
        
        ast = CppHeaderAST()
        ast.classes.append(n_class)
        
        output = generate_mock_header_from_ast(ast, "Worker.h")
        self.assertIn("MOCK_METHOD(void, Process, (), (noexcept, override));", output)

    def test_generate_companion_mock_reset(self):
        # Companion mock for static method
        s_class = Class("Service", "sdk")
        s_class.static_methods.append(Method("Init", "bool", [], is_static=True))
        
        ast = CppHeaderAST()
        ast.classes.append(s_class)
        
        output = generate_mock_header_from_ast(ast, "Service.h")
        self.assertIn("class ServiceMock", output)
        self.assertIn("static void reset(void)", output)
        self.assertIn("::testing::Mock::VerifyAndClearExpectations(&getInstance());", output)

    def test_generate_auto_destructor(self):
        # Class with virtual methods but NO destructor
        d_class = Class("Task", "sdk")
        d_class.methods.append(Method("Execute", "void", [], is_pure_virtual=True))
        
        ast = CppHeaderAST()
        ast.classes.append(d_class)
        
        output = generate_mock_header_from_ast(ast, "Task.h")
        # Destructor should be auto-generated
        self.assertIn("virtual ~MockTask() = default;", output)

    def test_generate_move_only_return_warnings(self):
        m_class = Class("Factory", "sdk")
        m_class.methods.append(Method("Create", "std::unique_ptr<Product>", [], is_pure_virtual=True))
        
        ast = CppHeaderAST()
        ast.classes.append(m_class)
        
        output = generate_mock_header_from_ast(ast, "Factory.h")
        self.assertIn("Note: Returns a move-only type", output)

    def test_generate_preprocessor_guards(self):
        g_class = Class("Guard", "sdk", preprocessor_guards=["#ifdef ENABLE_GUARD"])
        g_class.methods.append(Method("Secure", "void", [], is_pure_virtual=True, preprocessor_guards=["#ifdef ENABLE_GUARD", "#if SECURITY_LEVEL > 1"]))
        
        ast = CppHeaderAST()
        ast.classes.append(g_class)
        
        output = generate_mock_header_from_ast(ast, "Guard.h")
        
        # Verify guards are generated around the class and methods
        self.assertIn("#ifdef ENABLE_GUARD", output)
        self.assertIn("#if SECURITY_LEVEL > 1", output)
        self.assertIn("#endif // ENABLE_GUARD", output)

if __name__ == "__main__":
    unittest.main()
