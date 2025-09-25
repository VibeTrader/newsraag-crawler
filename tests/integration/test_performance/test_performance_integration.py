"""
Performance integration tests for NewsRaag Crawler.

Tests system performance under realistic load conditions.
"""
import pytest
import asyncio
import time
import psutil
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path  
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


class TestCrawlerPerformance:
    """Performance tests for crawler operations."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_multiple_source_crawling_performance(self, memory_profiler):
        """Test performance when crawling multiple sources."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler not available")
        
        # Create multiple test sources
        test_sources = []
        for i in range(5):
            test_sources.append({
                'name': f'perf_test_source_{i}',
                'type': 'rss',
                'url': f'https://httpbin.org/status/{200 if i % 2 == 0 else 404}',
                'enabled': True
            })
        
        # Measure performance
        start_time = time.time()
        start_memory = memory_profiler()
        
        # Process all sources
        results = []
        for source in test_sources:
            result = await crawl_source(source)
            results.append(result)
            # Small delay to prevent overwhelming
            await asyncio.sleep(0.1)
        
        end_time = time.time()
        end_memory = memory_profiler()
        
        # Performance assertions
        total_time = end_time - start_time
        memory_increase = end_memory - start_memory
        
        assert total_time < 30.0  # Should complete within 30 seconds
        assert memory_increase < 100  # Should not use more than 100MB additional memory
        
        # Verify all sources were processed
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) >= 2
    
    @pytest.mark.integration
    @pytest.mark.performance
    def test_monitoring_system_performance(self):
        """Test monitoring system performance under load."""
        monitoring_results = {}
        
        # Test metrics performance
        try:
            from monitoring.metrics import get_metrics
            
            start_time = time.time()
            for i in range(100):
                metrics = get_metrics()
                # Simulate some operations if methods exist
                if hasattr(metrics, 'start_cycle'):
                    cycle_id = metrics.start_cycle()
                    if hasattr(metrics, 'end_cycle'):
                        metrics.end_cycle(cycle_id, success=True)
            end_time = time.time()
            
            monitoring_results['metrics'] = end_time - start_time
            
        except ImportError:
            pass
        
        # Test duplicate detector performance
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            
            detector = get_duplicate_detector()
            if detector and hasattr(detector, 'is_duplicate'):
                start_time = time.time()
                
                # Test with multiple articles
                for i in range(50):
                    test_article = {
                        'title': f'Performance Test Article {i}',
                        'url': f'https://example.com/perf-test-{i}',
                        'content': f'Test content for performance article {i}'
                    }
                    
                    result = detector.is_duplicate(test_article)
                    if hasattr(detector, 'add_article'):
                        detector.add_article(test_article)
                
                end_time = time.time()
                monitoring_results['duplicate_detector'] = end_time - start_time
                
        except ImportError:
            pass
        
        # Verify performance is acceptable
        if monitoring_results:
            for component, duration in monitoring_results.items():
                assert duration < 10.0, f"{component} took too long: {duration}s"
        else:
            pytest.skip("No monitoring components available for performance testing")


class TestMemoryLeakDetection:
    """Test for memory leaks during extended operations."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.slow
    def test_memory_stability_over_time(self, memory_profiler):
        """Test memory stability during repeated operations."""
        try:
            from monitoring.metrics import get_metrics
        except ImportError:
            pytest.skip("metrics not available")
        
        memory_readings = []
        
        # Take baseline reading
        initial_memory = memory_profiler()
        memory_readings.append(initial_memory)
        
        # Perform repeated operations
        for cycle in range(10):
            metrics = get_metrics()
            
            # Simulate a work cycle
            if hasattr(metrics, 'start_cycle'):
                cycle_id = metrics.start_cycle()
                
                # Simulate some work
                time.sleep(0.1)
                
                if hasattr(metrics, 'update_memory_usage'):
                    try:
                        current_mem = memory_profiler()
                        metrics.update_memory_usage(current_mem)
                    except Exception:
                        pass
                
                if hasattr(metrics, 'end_cycle'):
                    metrics.end_cycle(cycle_id, success=True)
            
            # Take memory reading
            current_memory = memory_profiler()
            memory_readings.append(current_memory)
            
            # Brief pause
            time.sleep(0.1)
        
        # Analyze memory trend
        memory_increase = memory_readings[-1] - memory_readings[0]
        max_memory = max(memory_readings)
        min_memory = min(memory_readings)
        memory_range = max_memory - min_memory
        
        # Memory should not continuously increase (indicating leak)
        assert memory_increase < 50, f"Memory increased too much: {memory_increase}MB"
        assert memory_range < 100, f"Memory fluctuation too high: {memory_range}MB"
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_operations_memory(self, memory_profiler):
        """Test memory usage during concurrent operations."""
        try:
            from crawler.core.source_crawler import crawl_source
        except ImportError:
            pytest.skip("source_crawler not available")
        
        initial_memory = memory_profiler()
        
        # Create concurrent tasks
        tasks = []
        for i in range(3):
            config = {
                'name': f'concurrent_test_{i}',
                'type': 'rss',
                'url': 'https://httpbin.org/status/200',
                'enabled': True
            }
            task = asyncio.create_task(crawl_source(config))
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = memory_profiler()
        memory_increase = final_memory - initial_memory
        
        # Verify results
        assert len(results) == 3
        for result in results:
            if not isinstance(result, Exception):
                assert result is not None
        
        # Memory usage should be reasonable
        assert memory_increase < 150, f"Concurrent operations used too much memory: {memory_increase}MB"


class TestSystemResourceUsage:
    """Test system resource usage during operations."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    def test_cpu_usage_monitoring(self):
        """Test CPU usage during typical operations."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil not available")
        
        # Get baseline CPU usage
        psutil.cpu_percent(interval=1)  # Initialize
        initial_cpu = psutil.cpu_percent(interval=0.1)
        
        # Perform CPU-intensive operation
        start_time = time.time()
        try:
            from monitoring.metrics import get_metrics
            from monitoring.duplicate_detector import get_duplicate_detector
            
            # Simulate typical workload
            for i in range(20):
                metrics = get_metrics()
                detector = get_duplicate_detector()
                
                # Simulate work
                if hasattr(detector, 'is_duplicate'):
                    test_article = {
                        'title': f'CPU Test Article {i}',
                        'url': f'https://example.com/cpu-test-{i}',
                        'content': 'CPU test content'
                    }
                    detector.is_duplicate(test_article)
                
        except ImportError:
            # Fallback to generic CPU test
            for i in range(1000):
                _ = str(i) * 100
        
        end_time = time.time()
        final_cpu = psutil.cpu_percent(interval=0.1)
        
        duration = end_time - start_time
        
        # Verify reasonable resource usage
        assert duration < 10.0, f"Operations took too long: {duration}s"
        # CPU usage might be higher during tests, so we're lenient
        assert final_cpu < 90, f"CPU usage too high: {final_cpu}%"
    
    @pytest.mark.integration
    @pytest.mark.performance  
    def test_file_handle_management(self, temp_dir):
        """Test file handle management during operations."""
        try:
            import psutil
            process = psutil.Process()
        except ImportError:
            pytest.skip("psutil not available")
        
        initial_handles = len(process.open_files())
        
        # Perform file operations
        try:
            from monitoring.metrics import get_metrics
            metrics = get_metrics()
            
            # Simulate multiple save operations if available
            if hasattr(metrics, 'save_daily_metrics'):
                with patch('monitoring.metrics.METRICS_DIR', temp_dir):
                    for i in range(10):
                        try:
                            metrics.save_daily_metrics()
                        except Exception:
                            pass
            
        except ImportError:
            # Fallback file operations
            for i in range(10):
                test_file = os.path.join(temp_dir, f'test_{i}.txt')
                with open(test_file, 'w') as f:
                    f.write(f'Test data {i}')
                with open(test_file, 'r') as f:
                    content = f.read()
                os.remove(test_file)
        
        final_handles = len(process.open_files())
        handle_increase = final_handles - initial_handles
        
        # Should not leak file handles
        assert handle_increase <= 2, f"Too many file handles opened: {handle_increase}"


class TestScalabilityLimits:
    """Test system scalability limits."""
    
    @pytest.mark.integration
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_dataset_handling(self):
        """Test handling of large datasets."""
        try:
            from monitoring.duplicate_detector import get_duplicate_detector
            detector = get_duplicate_detector()
        except ImportError:
            pytest.skip("duplicate_detector not available")
        
        if not hasattr(detector, 'is_duplicate') or not hasattr(detector, 'add_article'):
            pytest.skip("duplicate_detector methods not available")
        
        start_time = time.time()
        
        # Add large number of articles
        for i in range(1000):
            article = {
                'title': f'Scalability Test Article {i}',
                'url': f'https://example.com/scale-test-{i}',
                'content': f'Scalability test content for article number {i}'
            }
            
            is_dup = detector.is_duplicate(article)
            detector.add_article(article)
            
            # Progress check every 100 articles
            if i % 100 == 0 and i > 0:
                elapsed = time.time() - start_time
                if elapsed > 30:  # Stop if taking too long
                    break
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should handle large dataset in reasonable time
        assert total_time < 60, f"Large dataset processing took too long: {total_time}s"


if __name__ == "__main__":
    print("Running performance integration tests...")
    import subprocess
    import sys
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-v", 
        "-m", "integration and performance", "--tb=short"
    ], cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    
    sys.exit(result.returncode)
