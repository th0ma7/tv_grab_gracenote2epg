#!/usr/bin/env python3
"""
Benchmark script for testing parallel download performance
"""

import time
import statistics
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Tuple
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class PerformanceBenchmark:
    """Benchmark parallel vs sequential download performance"""

    def __init__(self, config_file: Path = None, gracenote_path: Path = None):
        self.config_file = config_file or Path.home() / "gracenote2epg/conf/gracenote2epg.xml"
        self.gracenote_path = gracenote_path or self._find_gracenote_module()
        self.results = {
            'sequential': [],
            'parallel': []
        }

    def _find_gracenote_module(self) -> Path:
        """Find gracenote2epg module path"""
        # Try to find the module in common locations
        script_dir = Path(__file__).parent
        project_root = script_dir.parent

        # Check if we're in the gracenote2epg project directory
        gracenote_module = project_root / "gracenote2epg"
        if gracenote_module.exists() and (gracenote_module / "__init__.py").exists():
            return project_root

        # Try parent directories
        for parent in project_root.parents:
            gracenote_module = parent / "gracenote2epg"
            if gracenote_module.exists() and (gracenote_module / "__init__.py").exists():
                return parent

        # Default to current directory
        return Path.cwd()

    def run_benchmark(self, days: int = 1, iterations: int = 3) -> Dict:
        """
        Run benchmark comparing sequential and parallel modes

        Args:
            days: Number of days to download
            iterations: Number of test iterations

        Returns:
            Benchmark results dictionary
        """
        import subprocess

        logging.info("Starting performance benchmark")
        logging.info(f"Configuration: {days} days, {iterations} iterations")
        logging.info(f"Gracenote2EPG path: {self.gracenote_path}")
        logging.info(f"Config file: {self.config_file}")

        # Test configurations
        test_configs = [
            {
                'name': 'Sequential',
                'env': {
                    'GRACENOTE_PARALLEL': 'false'
                }
            },
            {
                'name': 'Parallel-2',
                'env': {
                    'GRACENOTE_PARALLEL': 'true',
                    'GRACENOTE_MAX_WORKERS': '2'
                }
            },
            {
                'name': 'Parallel-4',
                'env': {
                    'GRACENOTE_PARALLEL': 'true',
                    'GRACENOTE_MAX_WORKERS': '4'
                }
            },
            {
                'name': 'Parallel-6',
                'env': {
                    'GRACENOTE_PARALLEL': 'true',
                    'GRACENOTE_MAX_WORKERS': '6'
                }
            },
            {
                'name': 'Parallel-Adaptive',
                'env': {
                    'GRACENOTE_PARALLEL': 'true',
                    'GRACENOTE_MAX_WORKERS': '4',
                    'GRACENOTE_ADAPTIVE': 'true'
                }
            }
        ]

        results = {}

        for config in test_configs:
            config_name = config['name']
            logging.info(f"\nTesting configuration: {config_name}")

            times = []
            success_count = 0

            for i in range(iterations):
                logging.info(f"  Iteration {i+1}/{iterations}")

                # Set environment variables
                env = os.environ.copy()
                env.update(config['env'])
                env['PYTHONPATH'] = str(self.gracenote_path)

                # Run gracenote2epg using python module
                start_time = time.time()

                try:
                    # Use python -m to run the module
                    cmd = [
                        sys.executable, '-m', 'gracenote2epg',
                        '--days', str(days),
                        '--config-file', str(self.config_file),
                        '--quiet'  # Suppress output for benchmark
                    ]

                    result = subprocess.run(
                        cmd,
                        env=env,
                        cwd=str(self.gracenote_path),
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )

                    if result.returncode == 0:
                        elapsed = time.time() - start_time
                        times.append(elapsed)
                        success_count += 1
                        logging.info(f"    Success: {elapsed:.2f} seconds")
                    else:
                        logging.warning(f"    Failed with code: {result.returncode}")
                        logging.debug(f"    Stdout: {result.stdout}")
                        logging.debug(f"    Stderr: {result.stderr}")

                except subprocess.TimeoutExpired:
                    logging.error("    Timeout exceeded")
                except Exception as e:
                    logging.error(f"    Error: {e}")

                # Wait between iterations to avoid rate limiting
                if i < iterations - 1:
                    time.sleep(2)

            # Calculate statistics
            if times:
                results[config_name] = {
                    'times': times,
                    'min': min(times),
                    'max': max(times),
                    'mean': statistics.mean(times),
                    'median': statistics.median(times),
                    'stdev': statistics.stdev(times) if len(times) > 1 else 0,
                    'success_rate': (success_count / iterations) * 100,
                    'speedup': None  # Will calculate relative to sequential
                }
                logging.info(f"  {config_name} results: {statistics.mean(times):.2f}s avg, {success_count}/{iterations} success")
            else:
                logging.warning(f"  {config_name}: No successful runs")

        # Calculate speedup relative to sequential
        if 'Sequential' in results:
            sequential_mean = results['Sequential']['mean']
            for config_name, data in results.items():
                if config_name != 'Sequential':
                    data['speedup'] = sequential_mean / data['mean']

        return results

    def run_quick_test(self) -> bool:
        """Run a quick test to verify the module works"""
        import subprocess

        logging.info("Running quick test...")

        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(self.gracenote_path)

            cmd = [
                sys.executable, '-m', 'gracenote2epg',
                '--version'
            ]

            result = subprocess.run(
                cmd,
                env=env,
                cwd=str(self.gracenote_path),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.info(f"Quick test passed: {result.stdout.strip()}")
                return True
            else:
                logging.error(f"Quick test failed with code: {result.returncode}")
                logging.error(f"Stderr: {result.stderr}")
                return False

        except Exception as e:
            logging.error(f"Quick test error: {e}")
            return False

    def print_results(self, results: Dict):
        """Print formatted benchmark results"""

        if not results:
            print("\n❌ No benchmark results to display")
            print("All test configurations failed to run successfully.")
            return

        print("\n" + "=" * 80)
        print("PERFORMANCE BENCHMARK RESULTS")
        print("=" * 80)

        # Header
        print(f"\n{'Configuration':<20} {'Mean':<10} {'Min':<10} {'Max':<10} {'StdDev':<10} {'Speedup':<10}")
        print("-" * 80)

        # Results
        for config_name, data in results.items():
            speedup_str = f"{data['speedup']:.2f}x" if data['speedup'] else "baseline"

            print(f"{config_name:<20} "
                  f"{data['mean']:<10.2f} "
                  f"{data['min']:<10.2f} "
                  f"{data['max']:<10.2f} "
                  f"{data['stdev']:<10.2f} "
                  f"{speedup_str:<10}")

        print("\n" + "=" * 80)
        print("PERFORMANCE SUMMARY")
        print("=" * 80)

        # Find best configuration
        best_config = min(results.items(), key=lambda x: x[1]['mean'])
        print(f"\nBest configuration: {best_config[0]}")
        print(f"Average time: {best_config[1]['mean']:.2f} seconds")

        if 'Sequential' in results:
            sequential_time = results['Sequential']['mean']
            best_time = best_config[1]['mean']
            improvement = ((sequential_time - best_time) / sequential_time) * 100
            print(f"Performance improvement: {improvement:.1f}%")
            print(f"Speedup: {sequential_time / best_time:.2f}x faster")

        # Success rates
        print("\nSuccess rates:")
        for config_name, data in results.items():
            print(f"  {config_name}: {data['success_rate']:.1f}%")

    def save_results(self, results: Dict, filename: str = "benchmark_results.json"):
        """Save benchmark results to JSON file"""

        if not results:
            logging.warning("No results to save")
            return

        # Convert to serializable format
        serializable_results = {}
        for config_name, data in results.items():
            serializable_results[config_name] = {
                'times': data['times'],
                'min': data['min'],
                'max': data['max'],
                'mean': data['mean'],
                'median': data['median'],
                'stdev': data['stdev'],
                'success_rate': data['success_rate'],
                'speedup': data['speedup']
            }

        # Add metadata
        benchmark_metadata = {
            'timestamp': time.time(),
            'gracenote_path': str(self.gracenote_path),
            'config_file': str(self.config_file),
            'results': serializable_results
        }

        with open(filename, 'w') as f:
            json.dump(benchmark_metadata, f, indent=2)

        logging.info(f"Results saved to {filename}")

    def generate_chart(self, results: Dict):
        """Generate performance comparison chart (requires matplotlib)"""
        if not results:
            logging.warning("No results to chart")
            return

        try:
            import matplotlib.pyplot as plt

            configs = list(results.keys())
            means = [results[c]['mean'] for c in configs]
            mins = [results[c]['min'] for c in configs]
            maxs = [results[c]['max'] for c in configs]

            x = range(len(configs))

            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

            # Bar chart of mean times
            bars = ax1.bar(x, means, color=['red', 'orange', 'yellow', 'green', 'blue'][:len(configs)])
            ax1.set_xlabel('Configuration')
            ax1.set_ylabel('Time (seconds)')
            ax1.set_title('Average Download Time by Configuration')
            ax1.set_xticks(x)
            ax1.set_xticklabels(configs, rotation=45, ha='right')

            # Add value labels on bars
            for bar, mean in zip(bars, means):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{mean:.1f}s', ha='center', va='bottom')

            # Speedup chart
            speedups = []
            for c in configs:
                if results[c]['speedup']:
                    speedups.append(results[c]['speedup'])
                else:
                    speedups.append(1.0)  # Sequential baseline

            bars2 = ax2.bar(x, speedups, color=['red', 'orange', 'yellow', 'green', 'blue'][:len(configs)])
            ax2.set_xlabel('Configuration')
            ax2.set_ylabel('Speedup Factor')
            ax2.set_title('Performance Speedup vs Sequential')
            ax2.set_xticks(x)
            ax2.set_xticklabels(configs, rotation=45, ha='right')
            ax2.axhline(y=1, color='black', linestyle='--', alpha=0.3)

            # Add value labels
            for bar, speedup in zip(bars2, speedups):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{speedup:.2f}x', ha='center', va='bottom')

            plt.tight_layout()
            plt.savefig('benchmark_chart.png', dpi=100)
            plt.show()

            logging.info("Chart saved to benchmark_chart.png")

        except ImportError:
            logging.warning("matplotlib not available, skipping chart generation")


def main():
    """Main benchmark execution"""
    import argparse

    parser = argparse.ArgumentParser(description='Benchmark gracenote2epg performance')
    parser.add_argument('--days', type=int, default=1, help='Number of days to download')
    parser.add_argument('--iterations', type=int, default=3, help='Number of test iterations')
    parser.add_argument('--config', type=Path, help='Configuration file path')
    parser.add_argument('--gracenote-path', type=Path, help='Path to gracenote2epg module')
    parser.add_argument('--chart', action='store_true', help='Generate performance chart')
    parser.add_argument('--save', action='store_true', help='Save results to JSON')
    parser.add_argument('--quick-test', action='store_true', help='Run quick test only')

    args = parser.parse_args()

    # Create benchmark instance
    benchmark = PerformanceBenchmark(
        config_file=args.config,
        gracenote_path=args.gracenote_path
    )

    # Run quick test if requested
    if args.quick_test:
        success = benchmark.run_quick_test()
        sys.exit(0 if success else 1)

    # Verify module works before starting benchmark
    if not benchmark.run_quick_test():
        print("❌ Quick test failed. Please check your gracenote2epg installation.")
        print(f"Gracenote path: {benchmark.gracenote_path}")
        print(f"Config file: {benchmark.config_file}")
        sys.exit(1)

    # Run benchmark
    results = benchmark.run_benchmark(days=args.days, iterations=args.iterations)

    # Display results
    benchmark.print_results(results)

    # Save results if requested
    if args.save:
        benchmark.save_results(results)

    # Generate chart if requested
    if args.chart:
        benchmark.generate_chart(results)

    if results:
        print("\n✅ Benchmark complete!")
    else:
        print("\n❌ Benchmark failed - no successful runs")
        sys.exit(1)


if __name__ == "__main__":
    main()
