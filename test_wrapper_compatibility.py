#!/usr/bin/env python3
"""
Validation tests for wrapper compatibility.

Tests prove that:
1. wallet/generator.py wrapper works correctly
2. wallet/exporter.py wrapper works correctly
3. Both wrappers maintain backward compatibility
4. Runtime AttributeError risks are mitigated
"""

import sqlite3
import tempfile
import os
from pathlib import Path
from unittest import mock
import sys

# Import the modules to test
from wallet_gen import WalletGenerator
from converter import DatabaseConverter
from wallet.generator import generate_wallets as wrapper_generate_wallets
from wallet.exporter import export_wallets as wrapper_export_wallets


class TestWalletGeneratorWrapper:
    """Test wallet/generator.py wrapper compatibility."""

    def test_generator_has_generate_wallets_method(self):
        """Verify WalletGenerator has the generate_wallets method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            generator = WalletGenerator(db_path=db_path, quiet=True)
            
            # Check method exists
            assert hasattr(generator, "generate_wallets"), \
                "WalletGenerator missing generate_wallets method"
            
            # Check method is callable
            assert callable(getattr(generator, "generate_wallets")), \
                "generate_wallets is not callable"

    def test_generate_wallets_method_signature(self):
        """Verify generate_wallets has correct method signature."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            generator = WalletGenerator(db_path=db_path, quiet=True)
            
            # Mock the generate_and_insert to avoid actual generation
            with mock.patch.object(generator, "generate_and_insert"):
                with mock.patch.object(generator, "create_connection") as mock_conn:
                    with mock.patch.object(generator, "create_table"):
                        with mock.patch.object(generator, "close_connection"):
                            mock_conn.return_value = mock.MagicMock()
                            
                            # Test method accepts count and batch_size
                            try:
                                result = generator.generate_wallets(count=10, batch_size=5)
                                assert isinstance(result, int), \
                                    f"generate_wallets should return int, got {type(result)}"
                            except AttributeError as e:
                                raise AssertionError(f"generate_wallets call failed: {e}")

    def test_wrapper_generate_wallets_call(self):
        """Test that wrapper_generate_wallets function works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Mock the WalletGenerator to avoid actual generation
            with mock.patch("wallet.generator.WalletGenerator") as MockGenerator:
                mock_gen_instance = mock.MagicMock()
                mock_gen_instance.generate_wallets.return_value = 10
                MockGenerator.return_value = mock_gen_instance
                
                # Call the wrapper
                result = wrapper_generate_wallets(count=10, db_path=db_path, batch_size=5)
                
                # Verify result
                assert result == 10, f"Expected result 10, got {result}"
                
                # Verify the method was called with correct parameters
                MockGenerator.assert_called_once_with(db_path=db_path)
                mock_gen_instance.generate_wallets.assert_called_once_with(
                    count=10, batch_size=5
                )

    def test_generate_wallets_returns_int(self):
        """Verify generate_wallets returns an integer count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            with mock.patch("wallet.generator.WalletGenerator") as MockGenerator:
                mock_gen_instance = mock.MagicMock()
                mock_gen_instance.generate_wallets.return_value = 42
                MockGenerator.return_value = mock_gen_instance
                
                result = wrapper_generate_wallets(count=42, db_path=db_path)
                
                assert isinstance(result, int), \
                    f"generate_wallets should return int, got {type(result)}"
                assert result == 42, f"Expected 42, got {result}"


class TestDatabaseConverterWrapper:
    """Test wallet/exporter.py wrapper compatibility."""

    def test_converter_has_export_wallets_method(self):
        """Verify DatabaseConverter has the export_wallets method."""
        converter = DatabaseConverter(quiet=True)
        
        assert hasattr(converter, "export_wallets"), \
            "DatabaseConverter missing export_wallets method"
        
        assert callable(getattr(converter, "export_wallets")), \
            "export_wallets is not callable"

    def test_converter_has_close_connection_method(self):
        """Verify DatabaseConverter has the close_connection method."""
        converter = DatabaseConverter(quiet=True)
        
        assert hasattr(converter, "close_connection"), \
            "DatabaseConverter missing close_connection method"
        
        assert callable(getattr(converter, "close_connection")), \
            "close_connection is not callable"

    def test_export_wallets_routes_formats_correctly(self):
        """Test export_wallets routes to correct format handlers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = DatabaseConverter(quiet=True)
            
            # Test routing for each format
            formats = ["txt", "json", "csv", "sql", "ndjson", "tsv"]
            
            for fmt in formats:
                with mock.patch.object(converter, f"export_{fmt}") as mock_export:
                    mock_export.return_value = f"/path/to/export.{fmt}"
                    
                    # Call export_wallets with the format
                    result = converter.export_wallets(fmt=fmt)
                    
                    # Verify the correct export method was called
                    mock_export.assert_called_once()

    def test_export_wallets_with_uppercase_format(self):
        """Test export_wallets handles uppercase format strings."""
        converter = DatabaseConverter(quiet=True)
        
        with mock.patch.object(converter, "export_txt") as mock_export:
            mock_export.return_value = "/path/to/export.txt"
            
            # Call with uppercase format
            result = converter.export_wallets(fmt="TXT")
            
            # Should still work (converted to lowercase)
            mock_export.assert_called_once()

    def test_export_wallets_invalid_format(self):
        """Test export_wallets handles invalid format."""
        converter = DatabaseConverter(quiet=True)
        
        result = converter.export_wallets(fmt="invalid_format")
        
        assert result is None, "export_wallets should return None for invalid format"

    def test_close_connection_calls_close(self):
        """Test close_connection calls the underlying close method."""
        converter = DatabaseConverter(quiet=True)
        
        with mock.patch.object(converter, "close") as mock_close:
            converter.close_connection()
            
            mock_close.assert_called_once()

    def test_wrapper_export_wallets_call(self):
        """Test that wrapper_export_wallets function works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "wallets.db")
            
            # Create a temporary database for testing
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE wallets (
                    id INTEGER PRIMARY KEY,
                    address TEXT NOT NULL UNIQUE,
                    private_key TEXT NOT NULL
                )
            """)
            # Add a test wallet
            cursor.execute(
                "INSERT INTO wallets (address, private_key) VALUES (?, ?)",
                ("0x123abc", "0xprivkey123")
            )
            conn.commit()
            conn.close()
            
            # Mock the converter to avoid actual operations
            with mock.patch("wallet.exporter.DatabaseConverter") as MockConverter:
                mock_conv_instance = mock.MagicMock()
                mock_conv_instance.find_databases.return_value = [Path(db_path)]
                mock_conv_instance.select_database.return_value = Path(db_path)
                mock_conv_instance.connect_database.return_value = True
                mock_conv_instance.validate_database.return_value = True
                mock_conv_instance.export_wallets.return_value = f"{db_path}.txt"
                MockConverter.return_value = mock_conv_instance
                
                # Call the wrapper
                result = wrapper_export_wallets(fmt="txt", db_path=db_path)
                
                # Verify result is a string
                assert isinstance(result, str), \
                    f"export_wallets should return str, got {type(result)}"
                
                # Verify the export method was called
                mock_conv_instance.export_wallets.assert_called_once_with("txt")
                mock_conv_instance.close_connection.assert_called_once()


class TestRuntimeCompatibility:
    """Test runtime compatibility and error handling."""

    def test_generate_wallets_no_attribute_error_on_call(self):
        """Verify no AttributeError when calling wrapper."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            with mock.patch("wallet.generator.WalletGenerator") as MockGenerator:
                mock_gen_instance = mock.MagicMock()
                mock_gen_instance.generate_wallets.return_value = 5
                MockGenerator.return_value = mock_gen_instance
                
                # Should not raise AttributeError
                try:
                    result = wrapper_generate_wallets(count=5, db_path=db_path)
                    assert result == 5
                except AttributeError as e:
                    raise AssertionError(f"AttributeError raised: {e}")

    def test_export_wallets_no_attribute_error_on_call(self):
        """Verify no AttributeError when calling wrapper."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "wallets.db")
            
            with mock.patch("wallet.exporter.DatabaseConverter") as MockConverter:
                mock_conv_instance = mock.MagicMock()
                mock_conv_instance.find_databases.return_value = [Path(db_path)]
                mock_conv_instance.select_database.return_value = Path(db_path)
                mock_conv_instance.connect_database.return_value = True
                mock_conv_instance.validate_database.return_value = True
                mock_conv_instance.export_wallets.return_value = f"{db_path}.txt"
                MockConverter.return_value = mock_conv_instance
                
                # Should not raise AttributeError
                try:
                    result = wrapper_export_wallets(fmt="txt", db_path=db_path)
                    assert isinstance(result, str)
                except AttributeError as e:
                    raise AssertionError(f"AttributeError raised: {e}")


class TestBackwardCompatibility:
    """Test backward compatibility with existing code."""

    def test_generator_default_batch_size(self):
        """Test generate_wallets works with default batch_size."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            with mock.patch("wallet.generator.WalletGenerator") as MockGenerator:
                mock_gen_instance = mock.MagicMock()
                mock_gen_instance.generate_wallets.return_value = 100
                MockGenerator.return_value = mock_gen_instance
                
                # Call without batch_size (should use default)
                result = wrapper_generate_wallets(count=100, db_path=db_path)
                
                assert result == 100
                # Verify batch_size was passed as default (1000)
                mock_gen_instance.generate_wallets.assert_called_with(
                    count=100, batch_size=1000
                )

    def test_exporter_formats_list(self):
        """Test all export formats are supported."""
        converter = DatabaseConverter(quiet=True)
        
        supported_formats = ["txt", "json", "csv", "sql", "ndjson", "tsv"]
        
        for fmt in supported_formats:
            with mock.patch.object(converter, f"export_{fmt}") as mock_export:
                mock_export.return_value = f"/path/export.{fmt}"
                
                result = converter.export_wallets(fmt=fmt)
                
                # Should not return None (indicates success)
                assert result == f"/path/export.{fmt}", \
                    f"Format {fmt} should be supported"


def run_tests():
    """Run all tests and report results."""
    print("\n" + "=" * 70)
    print("WRAPPER COMPATIBILITY VALIDATION TESTS")
    print("=" * 70 + "\n")
    
    test_classes = [
        TestWalletGeneratorWrapper,
        TestDatabaseConverterWrapper,
        TestRuntimeCompatibility,
        TestBackwardCompatibility,
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        print("-" * 70)
        
        test_instance = test_class()
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith("test_")]
        
        for test_method in test_methods:
            total_tests += 1
            method = getattr(test_instance, test_method)
            
            try:
                method()
                print(f"  ✓ {test_method}")
                passed_tests += 1
            except Exception as e:
                print(f"  ✗ {test_method}")
                print(f"    Error: {str(e)}")
                failed_tests.append((test_class.__name__, test_method, str(e)))
    
    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  - {class_name}.{method_name}: {error}")
        return False
    else:
        print("\n✓ All wrapper compatibility tests passed!")
        return True


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
