#!/usr/bin/env python3
"""
Production-grade EVM Wallet Generator.

Generates EVM-compatible wallets for Ethereum and EVM-compatible chains including:
- Ethereum
- Polygon
- Arbitrum
- Optimism
- BNB Chain
- Avalanche C-Chain
- Linea
- Scroll
- zkSync Era
- Blast
- Mantle
- And other standard EVM chains using secp256k1 keys

Features:
- Secure cryptographic randomness
- Batch wallet generation
- Multiple export formats (JSON, CSV, TXT)
- Rich console UI with progress display
- Comprehensive logging
- CLI support with configurable options
- Production-ready error handling
"""

import argparse
import csv
import json
import logging
import logging.handlers
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eth_account import Account
from rich.console import Console
from rich.progress import Progress
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


class WalletGenerator:
    """Production-grade EVM wallet generator with secure randomness."""

    def __init__(self, output_dir: str = "output", log_dir: str = "logs"):
        """
        Initialize wallet generator with output and log directories.

        Args:
            output_dir: Directory to save generated wallets.
            log_dir: Directory for log files.
        """
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.console = Console()
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """
        Set up logging with rotating file handler.

        Returns:
            Configured logger instance.
        """
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger = logging.getLogger("wallet_gen")
        logger.setLevel(logging.DEBUG)

        # Create rotating file handler
        log_file = self.log_dir / "wallet_gen.log"
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    def generate_wallet(self) -> Dict[str, str]:
        """
        Generate a single EVM wallet using cryptographically secure randomness.

        Uses eth_account.Account to create wallets with secp256k1 keys,
        compatible with all standard EVM chains.

        Returns:
            Dictionary with 'address' and 'private_key' keys.
        """
        try:
            # Generate secure random bytes for private key (32 bytes = 256 bits)
            random_bytes = secrets.token_bytes(32)
            
            # Create account from random bytes
            account = Account.from_key(random_bytes)
            
            wallet = {
                "address": account.address,
                "private_key": account.key.hex()
            }
            
            self.logger.debug(f"Generated wallet: {account.address}")
            return wallet
            
        except Exception as e:
            self.logger.error(f"Error generating wallet: {e}")
            raise

    def generate_wallets(self, count: int) -> List[Dict[str, str]]:
        """
        Generate multiple EVM wallets efficiently.

        Args:
            count: Number of wallets to generate.

        Returns:
            List of wallet dictionaries with 'address' and 'private_key'.

        Raises:
            ValueError: If count is not a positive integer.
        """
        if not isinstance(count, int) or count <= 0:
            raise ValueError("Count must be a positive integer")

        wallets = []
        
        with Progress(console=self.console) as progress:
            task = progress.add_task(
                "[cyan]Generating wallets...",
                total=count
            )
            
            for _ in range(count):
                try:
                    wallet = self.generate_wallet()
                    wallets.append(wallet)
                    progress.update(task, advance=1)
                except Exception as e:
                    self.logger.error(f"Failed to generate wallet: {e}")
                    progress.stop()
                    raise

        self.logger.info(f"Successfully generated {count} wallets")
        return wallets

    def save_json(self, wallets: List[Dict[str, str]], path: Optional[str] = None) -> str:
        """
        Save wallets to JSON format with wallet IDs.

        Args:
            wallets: List of wallet dictionaries.
            path: Optional custom output path.

        Returns:
            Path to saved file.

        Raises:
            IOError: If file cannot be written.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            if path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.output_dir / f"wallets_{timestamp}.json"
            else:
                path = self.output_dir / path
            
            # Add IDs to wallets
            wallets_with_ids = [
                {**wallet, "id": idx + 1}
                for idx, wallet in enumerate(wallets)
            ]
            
            with open(path, "w") as f:
                json.dump(wallets_with_ids, f, indent=2)
            
            self.logger.info(f"Saved {len(wallets)} wallets to JSON: {path}")
            return str(path)
            
        except IOError as e:
            self.logger.error(f"Failed to save JSON: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving JSON: {e}")
            raise

    def save_csv(self, wallets: List[Dict[str, str]], path: Optional[str] = None) -> str:
        """
        Save wallets to CSV format with columns: id, address, private_key.

        Args:
            wallets: List of wallet dictionaries.
            path: Optional custom output path.

        Returns:
            Path to saved file.

        Raises:
            IOError: If file cannot be written.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            if path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.output_dir / f"wallets_{timestamp}.csv"
            else:
                path = self.output_dir / path
            
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "address", "private_key"])
                
                for idx, wallet in enumerate(wallets):
                    writer.writerow([
                        idx + 1,
                        wallet["address"],
                        wallet["private_key"]
                    ])
            
            self.logger.info(f"Saved {len(wallets)} wallets to CSV: {path}")
            return str(path)
            
        except IOError as e:
            self.logger.error(f"Failed to save CSV: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving CSV: {e}")
            raise

    def save_txt(self, wallets: List[Dict[str, str]], path: Optional[str] = None) -> str:
        """
        Save wallets to TXT format with one wallet per line: 0xADDRESS|0xPRIVATEKEY.

        Args:
            wallets: List of wallet dictionaries.
            path: Optional custom output path.

        Returns:
            Path to saved file.

        Raises:
            IOError: If file cannot be written.
        """
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            if path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = self.output_dir / f"wallets_{timestamp}.txt"
            else:
                path = self.output_dir / path
            
            with open(path, "w") as f:
                for wallet in wallets:
                    f.write(f"{wallet['address']}|{wallet['private_key']}\n")
            
            self.logger.info(f"Saved {len(wallets)} wallets to TXT: {path}")
            return str(path)
            
        except IOError as e:
            self.logger.error(f"Failed to save TXT: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error saving TXT: {e}")
            raise

    def display_summary(self, count: int, output_file: str, export_format: str) -> None:
        """
        Display a rich formatted summary of wallet generation.

        Args:
            count: Number of wallets generated.
            output_file: Path to output file.
            export_format: Export format used (json, csv, txt).
        """
        # Create summary table
        summary = Table(title="Wallet Generation Summary", show_header=True)
        summary.add_column("Parameter", style="cyan")
        summary.add_column("Value", style="green")
        
        summary.add_row("Total Wallets", str(count))
        summary.add_row("Export Format", export_format.upper())
        summary.add_row("Output File", output_file)
        summary.add_row("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Display with panel
        panel = Panel(
            summary,
            title="[bold]Generation Complete[/bold]",
            border_style="green"
        )
        self.console.print(panel)


def parse_arguments() -> argparse.Namespace:
    """
    Parse and validate command-line arguments.

    Returns:
        Parsed arguments.

    Raises:
        SystemExit: On invalid arguments.
    """
    parser = argparse.ArgumentParser(
        description="Production-grade EVM wallet generator for Ethereum and EVM-compatible chains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wallet_gen.py --count 100
  python wallet_gen.py --count 500 --format csv
  python wallet_gen.py --count 1000 --format json --output wallets.json
  python wallet_gen.py --count 10 --quiet
        """
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="Number of wallets to generate (default: 1)"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "csv", "txt"],
        default="json",
        help="Export format: json, csv, or txt (default: json)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Custom output filename (default: auto-generated with timestamp)"
    )
    
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output"
    )
    
    args = parser.parse_args()
    
    # Validate count
    if args.count < 1:
        parser.error("--count must be at least 1")
    
    if args.count > 1000000:
        parser.error("--count cannot exceed 1,000,000")
    
    return args


def main() -> None:
    """
    Main entry point for wallet generator CLI.

    Handles argument parsing, wallet generation, export, and error handling.
    """
    try:
        args = parse_arguments()
        
        # Initialize generator
        generator = WalletGenerator()
        
        # Display banner
        if not args.quiet:
            banner = Text("EVM Wallet Generator", style="bold cyan")
            generator.console.print(
                Panel(
                    banner,
                    border_style="green",
                    padding=(1, 2)
                )
            )
        
        # Generate wallets
        generator.logger.info(
            f"Starting wallet generation: count={args.count}, "
            f"format={args.format}"
        )
        
        wallets = generator.generate_wallets(args.count)
        
        # Determine output filename
        if args.output:
            output_file = f"{args.output}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = args.format
            output_file = f"wallets_{timestamp}.{extension}"
        
        # Export wallets
        if args.format == "json":
            saved_path = generator.save_json(wallets, output_file)
        elif args.format == "csv":
            saved_path = generator.save_csv(wallets, output_file)
        elif args.format == "txt":
            saved_path = generator.save_txt(wallets, output_file)
        
        # Display summary
        if not args.quiet:
            generator.display_summary(args.count, saved_path, args.format)
            generator.console.print(
                f"✓ Wallets saved to: [bold green]{saved_path}[/bold green]"
            )
            generator.console.print(
                f"✓ Logs saved to: [bold green]logs/wallet_gen.log[/bold green]"
            )
        else:
            print(f"Generated {args.count} wallets and saved to {saved_path}")
        
        generator.logger.info(f"Wallet generation completed successfully")
        
    except KeyboardInterrupt:
        generator.logger.warning("Wallet generation interrupted by user")
        print("\n[yellow]Wallet generation interrupted by user[/yellow]")
    except ValueError as e:
        generator.logger.error(f"Invalid argument: {e}")
        print(f"[red]Error: {e}[/red]")
    except IOError as e:
        generator.logger.error(f"File I/O error: {e}")
        print(f"[red]Error: Unable to write output file: {e}[/red]")
    except ImportError as e:
        generator.logger.error(f"Missing dependency: {e}")
        print(f"[red]Error: Missing dependency. Run: pip install -r requirements.txt[/red]")
    except Exception as e:
        generator.logger.exception(f"Unexpected error: {e}")
        print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    main()
