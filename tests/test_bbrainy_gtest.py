import unittest
import tempfile
import os
from gtest_migration_factory.parser.cpp_parser import Method, Class
from gtest_migration_factory.parser.bbrainy_gtest import (
    extract_method_body,
    analyze_method_body,
    analyze_cpp_file
)

class TestBBrainyGTest(unittest.TestCase):
    def test_extract_method_body(self):
        cpp_content = """
        #include "Account.h"
        namespace bank {
            bool Account::Deposit(double amount) {
                if (amount <= 0) {
                    return false;
                }
                balance += amount;
                return true;
            }
        }
        """
        body = extract_method_body(cpp_content, "Account", "Deposit")
        self.assertIsNotNone(body)
        self.assertIn("amount <= 0", body)
        self.assertIn("balance += amount", body)

    def test_analyze_method_body_numeric_bounds(self):
        method = Method("Deposit", "bool", [{"type": "double", "name": "amount"}])
        body_text = """
            if (amount <= 0) {
                return false;
            }
            return true;
        """
        scenarios = analyze_method_body(method, body_text)
        # Should generate a Positive scenario and an EdgeCase scenario
        self.assertEqual(len(scenarios), 2)
        
        pos = scenarios[0]
        self.assertEqual(pos.scenario_type, "positive")
        self.assertEqual(pos.scenario_name, "Success_DefaultBehavior")
        self.assertTrue(any("amount = 10" in decl for decl in pos.arrange_statements))
        
        neg = scenarios[1]
        self.assertEqual(neg.scenario_type, "edge_case")
        self.assertEqual(neg.scenario_name, "EdgeCase_amountZeroOrLess")
        self.assertTrue(any("amount = 0" in decl for decl in neg.arrange_statements))
        self.assertIn("EXPECT_THAT(actual, Eq(false));", neg.assert_statements)

    def test_analyze_method_body_null_pointers(self):
        method = Method("ProcessData", "void*", [{"type": "int*", "name": "data"}])
        body_text = """
            if (!data) {
                return nullptr;
            }
            return data;
        """
        scenarios = analyze_method_body(method, body_text)
        self.assertEqual(len(scenarios), 2)
        
        neg = scenarios[1]
        self.assertEqual(neg.scenario_type, "negative")
        self.assertEqual(neg.scenario_name, "Failure_dataNull")
        self.assertTrue(any("data = nullptr" in decl for decl in neg.arrange_statements))
        self.assertIn("EXPECT_THAT(actual, Eq(nullptr));", neg.assert_statements)

    def test_analyze_method_body_string_empty(self):
        method = Method("SetName", "bool", [{"type": "const std::string&", "name": "name"}])
        body_text = """
            if (name.empty()) {
                return false;
            }
            return true;
        """
        scenarios = analyze_method_body(method, body_text)
        self.assertEqual(len(scenarios), 2)
        
        neg = scenarios[1]
        self.assertEqual(neg.scenario_type, "edge_case")
        self.assertEqual(neg.scenario_name, "EdgeCase_nameEmpty")
        self.assertTrue(any('name = "";' in decl for decl in neg.arrange_statements))

    def test_analyze_method_body_smart_pointers(self):
        method = Method("Execute", "void", [
            {"type": "std::shared_ptr<Database>", "name": "db"},
            {"type": "std::unique_ptr<Connection>&", "name": "conn"}
        ])
        scenarios = analyze_method_body(method)
        self.assertEqual(len(scenarios), 1)
        pos = scenarios[0]
        
        # db shared_ptr should be make_shared
        self.assertTrue(any("std::shared_ptr<Database> db = std::make_shared<MockDatabase>();" in decl for decl in pos.arrange_statements))
        # conn unique_ptr should be make_unique
        self.assertTrue(any("std::unique_ptr<Connection> conn = std::make_unique<MockConnection>();" in decl for decl in pos.arrange_statements))
        
    def test_analyze_method_body_mocked_dependencies(self):
        method = Method("Process", "bool", [{"type": "Database*", "name": "db"}])
        body_text = """
            if (!db) return false;
            db->query();
            return true;
        """
        scenarios = analyze_method_body(method, body_text)
        # Should detect 'query' is called on 'db'
        pos = [s for s in scenarios if s.scenario_name == "Success_DefaultBehavior"][0]
        self.assertTrue(any("MockDatabase mock_db;" in decl for decl in pos.arrange_statements))
        self.assertTrue(any("Database* db = &mock_db;" in decl for decl in pos.arrange_statements))
        self.assertTrue(any("EXPECT_CALL(mock_db, query(::testing::_))" in decl for decl in pos.arrange_statements))

    def test_type_alias_resolution(self):
        from gtest_migration_factory.parser.bbrainy_gtest import extract_type_aliases, resolve_type
        # Test using
        alias_map = extract_type_aliases([
            {"is_special": True, "text": "using MyInt = int;"},
            {"is_special": True, "text": "using DoubleAlias = double;"}
        ], [
            {"text": "typedef MyInt CountType;"}
        ])
        
        self.assertEqual(alias_map.get("MyInt"), "int")
        self.assertEqual(alias_map.get("DoubleAlias"), "double")
        self.assertEqual(alias_map.get("CountType"), "MyInt")
        
        # Test recursive resolution
        self.assertEqual(resolve_type("CountType", alias_map), "int")
        self.assertEqual(resolve_type("const CountType&", alias_map), "const int&")

    def test_container_default_values(self):
        method = Method("ProcessVectors", "void", [
            {"type": "const std::vector<int>&", "name": "vec_int"},
            {"type": "std::map<std::string, bool>", "name": "map_val"}
        ])
        
        scenarios = analyze_method_body(method)
        self.assertEqual(len(scenarios), 1)
        pos = scenarios[0]
        
        # Verify vector non-empty initializer
        self.assertTrue(any("std::vector<int> vec_int = {1, 2, 3};" in decl for decl in pos.arrange_statements))
        # Verify map non-empty initializer
        self.assertTrue(any('std::map<std::string, bool> map_val = {{"key1", true}};' in decl or 'std::map<std::string, bool> map_val = {{"key1", true}};' in decl.replace(" ", "") for decl in pos.arrange_statements))

if __name__ == "__main__":
    unittest.main()
