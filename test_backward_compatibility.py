#!/usr/bin/env python3
"""
Backward compatibility test to verify direct usage still works.

Tests that the added methods don't break existing direct usage of:
1. WalletGenerator via wallet_gen.py
2. DatabaseConverter via converter.py
"""

import sqlite3
import tempfile
import os
from pathlib import Path
import sys

from wallet_gen import WalletGenerator
from converter import DatabaseConverter


def test_direct_wallet_generation():
    """Test direct usage of WalletGenerator (not through wrapper)."""
    print("\nTest: Direct WalletGenerator Usage")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "direct_test.db")
        
        try:
            generator = WalletGenerator(db_path=db_path, quiet=True)
            
            # Use existing main_flow method (original usage)
            generator.main_flow(count=3, batch_size=0)
            
            # Verify wallets were created
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wallets")
            count = cursor.fetchone()[0]
            conn.close()
            
            assert count == 3, f"Expected 3 wallets, got {count}"
            
            print(f"✓ Direct main_flow usage works, generated {count} wallets")
            return True
            
        except Exception as e:
            print(f"✗ Direct usage failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_direct_converter_usage():
    """Test direct usage of DatabaseConverter (not through wrapper)."""
    print("\nTest: Direct DatabaseConverter Usage")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test database
        db_path = os.path.join(tmpdir, "converter_test.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL UNIQUE,
                private_key TEXT NOT NULL
            )
        """)
        
        # Add test wallets
        cursor.execute(
            "INSERT INTO wallets (address, private_key) VALUES (?, ?)",
            ("0xtest1234", "0xprivkey1")
        )
        cursor.execute(
            "INSERT INTO wallets (address, private_key) VALUES (?, ?)",
            ("0xtest5678", "0xprivkey2")
        )
        conn.commit()
        conn.close()
        
        try:
            converter = DatabaseConverter(quiet=True)
            
            # Use proper API: connect_database and validate_database
            db_path_obj = Path(db_path)
            if not converter.connect_database(db_path_obj):
                raise RuntimeError("Failed to connect to database")
            
            if not converter.validate_database():
                raise RuntimeError("Database validation failed")
            
            # Use existing export_txt method directly (original usage)
            result = converter.export_txt(output_path="test_export.txt")
            
            assert result is not None, "export_txt should return path"
            assert os.path.exists(result), f"Export file not created: {result}"
            
            # Verify file content
            with open(result, 'r') as f:
                content = f.read()
                assert len(content) > 0, "Export file is empty"
                # Should have two wallet lines
                lines = content.strip().split('\n')
                assert len(lines) >= 2, f"Expected at least 2 wallet lines, got {len(lines)}"
            
            converter.close()
            
            print(f"✓ Direct export_txt usage works")
            print(f"✓ Export file created with {len(lines)} wallets")
            return True
            
        except Exception as e:
            print(f"✗ Direct usage failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_new_methods_dont_interfere():
    """Test that new methods don't interfere with existing code."""
    print("\nTest: New Methods Don't Interfere")
    print("-" * 50)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "interference_test.db")
            
            # Test WalletGenerator
            gen = WalletGenerator(db_path=db_path, quiet=True)
            
            # Verify both old and new methods exist
            assert hasattr(gen, "main_flow"), "Old main_flow method missing"
            assert hasattr(gen, "generate_wallets"), "New generate_wallets method missing"
            assert hasattr(gen, "generate_and_insert"), "Old generate_and_insert method missing"
            
            print("✓ WalletGenerator has both old and new methods")
            
            # Test DatabaseConverter
            converter = DatabaseConverter(quiet=True)
            
            # Verify both old and new methods exist
            assert hasattr(converter, "export_txt"), "Old export_txt method missing"
            assert hasattr(converter, "export_wallets"), "New export_wallets method missing"
            assert hasattr(converter, "close"), "Old close method missing"
            assert hasattr(converter, "close_connection"), "New close_connection method missing"
            
            print("✓ DatabaseConverter has both old and new methods")
            
            # Verify methods don't override each other
            assert converter.close != converter.close_connection, \
                "close_connection should be different from close (not same object)"
            
            print("✓ New methods don't override existing methods")
            return True
            
    except Exception as e:
        print(f"✗ Interference test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_method_return_types():
    """Test that new methods return correct types."""
    print("\nTest: Method Return Types")
    print("-" * 50)
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test WalletGenerator.generate_wallets return type
            db_path1 = os.path.join(tmpdir, "return_type_test_gen.db")
            gen = WalletGenerator(db_path=db_path1, quiet=True)
            gen.connection = gen.create_connection()
            gen.create_table()
            
            result = gen.generate_wallets(count=2, batch_size=0)
            
            assert isinstance(result, int), \
                f"generate_wallets should return int, got {type(result)}"
            assert result >= 0, \
                f"generate_wallets should return non-negative int, got {result}"
            
            gen.close_connection()
            
            print(f"✓ WalletGenerator.generate_wallets returns int: {result}")
            
            # Test DatabaseConverter.export_wallets return type
            # Use different tmpdir for converter test
            db_path2 = os.path.join(tmpdir, "return_type_test_conv.db")
            conn = sqlite3.connect(db_path2)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    address TEXT NOT NULL UNIQUE,
                    private_key TEXT NOT NULL
                )
            """)
            cursor.execute(
                "INSERT INTO wallets (address, private_key) VALUES (?, ?)",
                ("0xtest1234", "0xprivkey1")
            )
            conn.commit()
            conn.close()
            
            converter = DatabaseConverter(quiet=True)
            db_path_obj = Path(db_path2)
            
            if converter.connect_database(db_path_obj):
                result = converter.export_wallets(fmt="txt")
                
                # Should return str or None
                assert isinstance(result, (str, type(None))), \
                    f"export_wallets should return str or None, got {type(result)}"
                
                if result:
                    assert os.path.exists(result), f"Exported file not found: {result}"
                
                print(f"✓ DatabaseConverter.export_wallets returns str: {result}")
            
            converter.close_connection()
            
            return True
            
    except Exception as e:
        print(f"✗ Return type test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_backward_compatibility_tests():
    """Run all backward compatibility tests."""
    print("\n" + "=" * 70)
    print("BACKWARD COMPATIBILITY TESTS")
    print("=" * 70)
    
    tests = [
        ("Direct WalletGenerator Usage", test_direct_wallet_generation),
        ("Direct DatabaseConverter Usage", test_direct_converter_usage),
        ("New Methods Don't Interfere", test_new_methods_dont_interfere),
        ("Method Return Types", test_method_return_types),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nUnexpected error in {test_name}: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "=" * 70)
    print("BACKWARD COMPATIBILITY TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_backward_compatibility_tests()
    sys.exit(0 if success else 1)
