#!/usr/bin/env python3
"""
Test runner script for NewsRaag Crawler.

Provides convenient commands for running different types of tests.
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path


class TestRunner:
    """Test runner with various test execution options."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"
    
    def run_command(self, command, description=""):
        """Run a command and handle output."""
        print(f"\n{'='*60}")
        print(f"🚀 {description or 'Running command'}")
        print(f"Command: {' '.join(command)}")
        print(f"{'='*60}")
        
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=self.project_root)
            
            if result.stdout:
                print(result.stdout)
            
            if result.stderr:
                print(f"⚠️ Stderr: {result.stderr}", file=sys.stderr)
            
            if result.returncode != 0:
                print(f"❌ Command failed with exit code: {result.returncode}")
                return False
            else:
                print(f"✅ Command completed successfully")
                return True
                
        except Exception as e:
            print(f"❌ Error running command: {e}")
            return False
    
    def install_test_dependencies(self):
        """Install test dependencies."""
        print("📦 Installing test dependencies...")
        
        commands = [
            (["pip", "install", "-r", "requirements-test.txt"], "Installing test requirements"),
            (["pip", "install", "-e", "."], "Installing project in development mode (if setup.py exists)")
        ]
        
        success = True
        for command, description in commands:
            if not self.run_command(command, description):
                if "setup.py" not in description:  # setup.py is optional
                    success = False
        
        return success
    
    def run_unit_tests(self, verbose=False, coverage=False):
        """Run unit tests."""
        command = ["python", "-m", "pytest", "tests/unit/"]
        
        if verbose:
            command.append("-v")
        
        if coverage:
            command.extend(["--cov=crawler", "--cov=monitoring", "--cov=clients", "--cov=utils"])
        
        command.append("--tb=short")
        
        return self.run_command(command, "Running unit tests")
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        command = ["python", "-m", "pytest", "tests/integration/", "-m", "integration"]
        
        if verbose:
            command.append("-v")
        
        command.append("--tb=short")
        
        return self.run_command(command, "Running integration tests")
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests."""
        command = ["python", "-m", "pytest", "-m", "performance"]
        
        if verbose:
            command.append("-v")
        
        command.append("--tb=short")
        
        return self.run_command(command, "Running performance tests")
    
    def run_all_tests(self, verbose=False, coverage=False):
        """Run all tests."""
        command = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            command.append("-v")
        
        if coverage:
            command.extend([
                "--cov=crawler", 
                "--cov=monitoring", 
                "--cov=clients", 
                "--cov=utils",
                "--cov-report=html",
                "--cov-report=term-missing"
            ])
        
        command.append("--tb=short")
        
        return self.run_command(command, "Running all tests")
    
    def run_specific_test(self, test_path, verbose=False):
        """Run a specific test file or function."""
        command = ["python", "-m", "pytest", test_path]
        
        if verbose:
            command.append("-v")
        
        command.append("--tb=short")
        
        return self.run_command(command, f"Running specific test: {test_path}")
    
    def run_tests_by_marker(self, marker, verbose=False):
        """Run tests with specific marker."""
        command = ["python", "-m", "pytest", "-m", marker]
        
        if verbose:
            command.append("-v")
        
        command.append("--tb=short")
        
        return self.run_command(command, f"Running tests with marker: {marker}")
    
    def generate_coverage_report(self):
        """Generate detailed coverage report."""
        command = [
            "python", "-m", "pytest", "tests/",
            "--cov=crawler", 
            "--cov=monitoring", 
            "--cov=clients", 
            "--cov=utils",
            "--cov-report=html:htmlcov",
            "--cov-report=xml",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ]
        
        success = self.run_command(command, "Generating coverage report")
        
        if success:
            print("\n📊 Coverage reports generated:")
            print(f"   📄 HTML: {self.project_root}/htmlcov/index.html")
            print(f"   📄 XML: {self.project_root}/coverage.xml")
        
        return success
    
    def clean_test_artifacts(self):
        """Clean test artifacts and cache files."""
        artifacts_to_clean = [
            ".pytest_cache",
            "__pycache__",
            "*.pyc",
            ".coverage",
            "htmlcov",
            "coverage.xml",
            ".tox"
        ]
        
        print("🧹 Cleaning test artifacts...")
        
        import shutil
        import glob
        
        cleaned = []
        
        for pattern in artifacts_to_clean:
            if pattern.startswith(".") and not pattern.endswith("*"):
                # Directory or file
                path = self.project_root / pattern
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    cleaned.append(str(path))
            else:
                # Glob pattern
                for path in glob.glob(str(self.project_root / "**" / pattern), recursive=True):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        cleaned.append(path)
                    except OSError:
                        pass
        
        if cleaned:
            print(f"✅ Cleaned {len(cleaned)} artifacts")
            for artifact in cleaned[:10]:  # Show first 10
                print(f"   🗑️ {artifact}")
            if len(cleaned) > 10:
                print(f"   ... and {len(cleaned) - 10} more")
        else:
            print("✅ No artifacts to clean")
    
    def show_test_structure(self):
        """Show the test directory structure."""
        print("📁 Test Structure:")
        print(f"   {self.tests_dir}")
        
        def print_tree(directory, prefix="   "):
            try:
                items = sorted(directory.iterdir())
                for i, item in enumerate(items):
                    is_last = i == len(items) - 1
                    current_prefix = "└── " if is_last else "├── "
                    print(f"{prefix}{current_prefix}{item.name}")
                    
                    if item.is_dir() and not item.name.startswith('.') and item.name != '__pycache__':
                        extension_prefix = "    " if is_last else "│   "
                        print_tree(item, prefix + extension_prefix)
            except PermissionError:
                pass
        
        if self.tests_dir.exists():
            print_tree(self.tests_dir)
        else:
            print("   ❌ Tests directory not found")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(description="NewsRaag Crawler Test Runner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-c", "--coverage", action="store_true", help="Generate coverage report")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Install command
    subparsers.add_parser("install", help="Install test dependencies")
    
    # Test commands
    subparsers.add_parser("unit", help="Run unit tests")
    subparsers.add_parser("integration", help="Run integration tests")
    subparsers.add_parser("performance", help="Run performance tests")
    subparsers.add_parser("all", help="Run all tests")
    
    # Specific test command
    test_parser = subparsers.add_parser("test", help="Run specific test")
    test_parser.add_argument("path", help="Path to test file or function")
    
    # Marker command
    marker_parser = subparsers.add_parser("marker", help="Run tests by marker")
    marker_parser.add_argument("marker", help="Test marker (unit, integration, performance, etc.)")
    
    # Utility commands
    subparsers.add_parser("coverage", help="Generate coverage report")
    subparsers.add_parser("clean", help="Clean test artifacts")
    subparsers.add_parser("structure", help="Show test structure")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute commands
    success = True
    
    if args.command == "install":
        success = runner.install_test_dependencies()
    elif args.command == "unit":
        success = runner.run_unit_tests(args.verbose, args.coverage)
    elif args.command == "integration":
        success = runner.run_integration_tests(args.verbose)
    elif args.command == "performance":
        success = runner.run_performance_tests(args.verbose)
    elif args.command == "all":
        success = runner.run_all_tests(args.verbose, args.coverage)
    elif args.command == "test":
        success = runner.run_specific_test(args.path, args.verbose)
    elif args.command == "marker":
        success = runner.run_tests_by_marker(args.marker, args.verbose)
    elif args.command == "coverage":
        success = runner.generate_coverage_report()
    elif args.command == "clean":
        runner.clean_test_artifacts()
    elif args.command == "structure":
        runner.show_test_structure()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
