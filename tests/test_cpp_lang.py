import unittest
import os
from jrdev.languages.cpp_lang import CppLang

class TestCppLang(unittest.TestCase):
    def setUp(self):
        self.cpp_lang = CppLang()
    
    def test_parse_signature_with_class(self):
        """Test parsing signatures with class name"""
        # Basic class::function syntax
        class_name, func_name = self.cpp_lang.parse_signature("ClassName::functionName")
        self.assertEqual(class_name, "ClassName")
        self.assertEqual(func_name, "functionName")
        
        # With parameters
        class_name, func_name = self.cpp_lang.parse_signature("ClassName::functionName()")
        self.assertEqual(class_name, "ClassName")
        self.assertEqual(func_name, "functionName")
        
        # With parameters and spaces
        class_name, func_name = self.cpp_lang.parse_signature("ClassName::functionName (int a, int b)")
        self.assertEqual(class_name, "ClassName")
        self.assertEqual(func_name, "functionName")
        
        # With destructor
        class_name, func_name = self.cpp_lang.parse_signature("ClassName::~ClassName()")
        self.assertEqual(class_name, "ClassName")
        self.assertEqual(func_name, "~ClassName")
    
    def test_parse_signature_without_class(self):
        """Test parsing signatures without class name"""
        # Basic function name only
        class_name, func_name = self.cpp_lang.parse_signature("functionName")
        self.assertIsNone(class_name)
        self.assertEqual(func_name, "functionName")
        
        # With parameters
        class_name, func_name = self.cpp_lang.parse_signature("functionName()")
        self.assertIsNone(class_name)
        self.assertEqual(func_name, "functionName")
        
        # With parameters and spaces
        class_name, func_name = self.cpp_lang.parse_signature("functionName (int a, int b)")
        self.assertIsNone(class_name)
        self.assertEqual(func_name, "functionName")

    def test_parse_signature_edge_cases(self):
        """Test parsing signatures with edge cases"""
        # Template function
        class_name, func_name = self.cpp_lang.parse_signature("functionName<T>")
        self.assertIsNone(class_name)
        self.assertEqual(func_name, "functionName<T>")
        
        # Empty string
        class_name, func_name = self.cpp_lang.parse_signature("")
        self.assertIsNone(class_name)
        self.assertEqual(func_name, "")
        
        # Malformed with multiple ::
        class_name, func_name = self.cpp_lang.parse_signature("Namespace::Class::function")
        self.assertEqual(class_name, "Namespace")
        self.assertEqual(func_name, "Class::function")
        
    def test_parse_functions_in_header(self):
        """Test parsing functions in header files"""
        header_path = os.path.join(os.path.dirname(__file__), 'mock/pricechartwidget.h')
        if not os.path.exists(header_path):
            self.skipTest(f"Mock header file not found: {header_path}")
            
        header_functions = self.cpp_lang.parse_functions(header_path)
        
        # Verify we found a reasonable number of function declarations
        self.assertTrue(len(header_functions) >= 10, f"Expected to find at least 10 functions, found {len(header_functions)}")
        
        # Check for specific functions we expect to find
        function_names = [func["name"] for func in header_functions]
        self.assertIn("PriceChartWidget", function_names)
        self.assertIn("~PriceChartWidget", function_names)
        self.assertIn("SetTimeRange", function_names)
        self.assertIn("paintEvent", function_names)
        
        # Verify class name for functions
        class_names = set(func["class"] for func in header_functions if func["class"] is not None)
        self.assertEqual(len(class_names), 1)
        self.assertEqual(list(class_names)[0], "PriceChartWidget")
    
    def test_parse_functions_in_implementation(self):
        """Test parsing functions in implementation files"""
        impl_path = os.path.join(os.path.dirname(__file__), 'mock/pricechartwidget.cpp')
        if not os.path.exists(impl_path):
            self.skipTest(f"Mock implementation file not found: {impl_path}")
        
        impl_functions = self.cpp_lang.parse_functions(impl_path)
        
        # Verify we found function definitions
        self.assertTrue(len(impl_functions) >= 2, f"Expected to find at least 2 functions, found {len(impl_functions)}")
        
        # Check for specific functions we expect to find
        function_names = [func["name"] for func in impl_functions]
        self.assertIn("~PriceChartWidget", function_names)
        self.assertIn("Check", function_names)
        
        # Verify class name for functions
        class_names = set(func["class"] for func in impl_functions if func["class"] is not None)
        self.assertEqual(len(class_names), 1)
        self.assertEqual(list(class_names)[0], "PriceChartWidget")

if __name__ == '__main__':
    unittest.main()