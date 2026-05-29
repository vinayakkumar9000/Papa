#!/usr/bin/env python3
"""
Integration tests for wrapper functionality with real operations.

Tests verify that:
1. generator wrapper can generate and store real wallets
2. exporter wrapper can export wallets in all formats
3. No runtime AttributeErrors occur
"""

import sqlite3
import tempfile
import os
from pathlib import Path
import sys

# Import the wrapper functions
from wallet.generator import generate_wallets as wrapper_generate_wallets
from wallet.exporter import export_wallets as wrapper_export_wallets
from wallet_gen import WalletGenerator
from converter import DatabaseConverter


def test_real_wallet_generation():
    """Test real wallet generation through wrapper."""
    print("\nTest: Real Wallet Generation")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_wallets.db")
        
        try:
            # Generate wallets using wrapper
            count = wrapper_generate_wallets(count=5, db_path=db_path, batch_size=0)
            
            assert count == 5, f"Expected 5 wallets, got {count}"
            
            # Verify database has wallets
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM wallets")
            db_count = cursor.fetchone()[0]
            conn.close()
            
            assert db_count == 5, f"Database should have 5 wallets, got {db_count}"
            
            print(f"✓ Successfully generated {count} wallets")
            print(f"✓ Database contains {db_count} wallets")
            return True
            
        except Exception as e:
            print(f"✗ Wallet generation failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_real_wallet_export():
    """Test real wallet export through wrapper."""
    print("\nTest: Real Wallet Export")
    print("-" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # First create a database with test wallets
        db_path = os.path.join(tmpdir, "export_test.db")
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
        test_wallets = [
            ("0x1234567890abcdef1234567890abcdef12345678", "0xprivkey1"),
            ("0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", "0xprivkey2"),
        ]
        
        for address, privkey in test_wallets:
            cursor.execute(
                "INSERT INTO wallets (address, private_key) VALUES (?, ?)",
                (address, privkey)
            )
        
        conn.commit()
        conn.close()
        
        # Test export with all formats
        formats = ["txt", "json", "csv", "sql", "ndjson", "tsv"]
        successful_exports = []
        
        for fmt in formats:
            try:
                result = wrapper_export_wallets(fmt=fmt, db_path=db_path)
                
                assert result is not None, f"Export returned None for {fmt}"
                assert isinstance(result, str), f"Export should return string, got {type(result)}"
                
                # Verify file was created
                assert os.path.exists(result), f"Export file not created: {result}"
                
                # Verify file has content
                with open(result, 'r') as f:
                    content = f.read()
                    assert len(content) > 0, f"Export file is empty for {fmt}"
                
                successful_exports.append(fmt)
                print(f"✓ Successfully exported to {fmt.upper()}")
                
            except Exception as e:
                print(f"✗ Export to {fmt.upper()} failed: {e}")
                import traceback
                traceback.print_exc()
        
        return len(successful_exports) == len(formats)


def test_wrapper_method_existence():
    """Test that all required methods exist and are callable."""
    print("\nTest: Wrapper Method Existence")
    print("-" * 50)
    
    try:
        # Check WalletGenerator methods
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WalletGenerator(db_path=os.path.join(tmpdir, "test.db"), quiet=True)
            
            required_gen_methods = [
                "generate_wallets",
                "generate_and_insert",
                "generate_wallet",
                "insert_wallet",
                "insert_wallet_batch",
                "count_wallets",
                "create_connection",
                "create_table",
                "close_connection",
                "main_flow",
            ]
            
            for method_name in required_gen_methods:
                assert hasattr(gen, method_name), f"WalletGenerator missing {method_name}"
                assert callable(getattr(gen, method_name)), f"{method_name} not callable"
            
            print(f"✓ WalletGenerator has all {len(required_gen_methods)} required methods")
        
        # Check DatabaseConverter methods
        converter = DatabaseConverter(quiet=True)
        
        required_converter_methods = [
            "export_wallets",
            "export_txt",
            "export_json",
            "export_csv",
            "export_sql",
            "export_ndjson",
            "export_tsv",
            "close",
            "close_connection",
            "find_databases",
            "select_database",
            "connect_database",
            "validate_database",
            "get_wallet_count",
        ]
        
        for method_name in required_converter_methods:
            assert hasattr(converter, method_name), f"DatabaseConverter missing {method_name}"
            assert callable(getattr(converter, method_name)), f"{method_name} not callable"
        
        print(f"✓ DatabaseConverter has all {len(required_converter_methods)} required methods")
        return True
        
    except Exception as e:
        print(f"✗ Method existence check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_wrapper_method_signatures():
    """Test that wrapper methods have correct signatures."""
    print("\nTest: Wrapper Method Signatures")
    print("-" * 50)
    
    import inspect
    
    try:
        # Check generate_wallets signature
        with tempfile.TemporaryDirectory() as tmpdir:
            gen = WalletGenerator(db_path=os.path.join(tmpdir, "test.db"), quiet=True)
            sig = inspect.signature(gen.generate_wallets)
            params = list(sig.parameters.keys())
            
            expected_params = ["self", "count", "batch_size"]
            # Note: self is implicit, not in params
            assert "count" in params, "generate_wallets missing count parameter"
            assert "batch_size" in params, "generate_wallets missing batch_size parameter"
            
            print("✓ WalletGenerator.generate_wallets has correct signature")
        
        # Check export_wallets signature
        converter = DatabaseConverter(quiet=True)
        sig = inspect.signature(converter.export_wallets)
        params = list(sig.parameters.keys())
        
        assert "fmt" in params, "export_wallets missing fmt parameter"
        
        print("✓ DatabaseConverter.export_wallets has correct signature")
        
        # Check close_connection exists
        assert hasattr(converter, "close_connection"), "Missing close_connection method"
        assert callable(getattr(converter, "close_connection")), "close_connection not callable"
        
        print("✓ DatabaseConverter.close_connection exists and is callable")
        
        return True
        
    except Exception as e:
        print(f"✗ Signature check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_integration_tests():
    """Run all integration tests."""
    print("\n" + "=" * 70)
    print("WRAPPER INTEGRATION TESTS")
    print("=" * 70)
    
    tests = [
        ("Method Existence", test_wrapper_method_existence),
        ("Method Signatures", test_wrapper_method_signatures),
        ("Real Wallet Generation", test_real_wallet_generation),
        ("Real Wallet Export", test_real_wallet_export),
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
    print("INTEGRATION TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return passed == total


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
