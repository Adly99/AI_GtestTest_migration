def convert_scenarios_to_gtest(scenarios, class_name, mock_class_name):
    """
    Translates a list of TestScenario metadata into C++ GoogleTest functions.
    Uses EXPECT_THAT matchers to verify assertions and maps Arrange/Act/Assert structures.
    """
    lines = []
    fixture_name = f"{class_name}Test"
    
    for sc in scenarios:
        # Formulate GTest TEST_F case
        lines.append(f"TEST_F({fixture_name}, {sc.method_name}_{sc.scenario_name}) {{")
        
        # Arrange
        lines.append("    // Arrange")
        for arr in sc.arrange_statements:
            lines.append(f"    {arr}")
        lines.append(f"    {mock_class_name} mock_instance;")
        lines.append("")
        
        # Act
        lines.append("    // Act")
        lines.append(f"    {sc.act_statement}")
        lines.append("")
        
        # Assert
        lines.append("    // Assert")
        for ass in sc.assert_statements:
            lines.append(f"    {ass}")
            
        lines.append("}")
        lines.append("")
        
    return "\n".join(lines)
