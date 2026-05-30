import unittest
from gtest_migration_factory.parser.bbrainy_gtest import TestScenario
from gtest_migration_factory.generator.unit_test_converter import convert_scenarios_to_gtest

class TestUnitTestConverter(unittest.TestCase):
    def test_convert_scenarios_to_gtest(self):
        scenario = TestScenario(
            method_name="Deposit",
            scenario_type="edge_case",
            scenario_name="EdgeCase_amountZeroOrLess",
            arrange_statements=["double amount = 0;"],
            act_statement="bool actual = mock_instance.Deposit(amount);",
            assert_statements=["EXPECT_THAT(actual, Eq(false));"]
        )
        
        output = convert_scenarios_to_gtest([scenario], "Account", "MockAccount")
        
        self.assertIn("TEST_F(AccountTest, Deposit_EdgeCase_amountZeroOrLess)", output)
        self.assertIn("// Arrange", output)
        self.assertIn("double amount = 0;", output)
        self.assertIn("MockAccount mock_instance;", output)
        self.assertIn("// Act", output)
        self.assertIn("bool actual = mock_instance.Deposit(amount);", output)
        self.assertIn("// Assert", output)
        self.assertIn("EXPECT_THAT(actual, Eq(false));", output)

if __name__ == "__main__":
    unittest.main()
