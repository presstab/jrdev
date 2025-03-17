import unittest
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

if __name__ == '__main__':
    unittest.main()