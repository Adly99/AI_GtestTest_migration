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

if __name__ == "__main__":
    unittest.main()
