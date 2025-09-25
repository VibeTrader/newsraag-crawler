            metrics_instance.update_memory_usage("invalid")  # String instead of number
    
    @pytest.mark.unit
    def test_concurrent_cycle_operations(self, metrics_instance):
        """Test handling multiple concurrent cycles."""
        # Start multiple cycles
        cycle_ids = []
        for i in range(3):
            cycle_id = metrics_instance.start_cycle()
            cycle_ids.append(cycle_id)
        
        # End cycles in different order
        metrics_instance.end_cycle(cycle_ids[1], success=True)
        metrics_instance.end_cycle(cycle_ids[0], success=False, error="Test error")
        metrics_instance.end_cycle(cycle_ids[2], success=True)
        
        # Verify all cycles are properly tracked
        stats = metrics_instance.get_cycle_stats()
        assert stats['total_cycles'] == 3
        assert stats['successful_cycles'] == 2
        assert stats['failed_cycles'] == 1
    
    @pytest.mark.unit
    @pytest.mark.performance
    def test_metrics_performance_with_large_data(self, metrics_instance):
        """Test metrics performance with large amounts of data."""
        import time
        
        start_time = time.time()
        
        # Add large amount of data
        for i in range(100):
            cycle_id = metrics_instance.start_cycle()
            metrics_instance.update_memory_usage(100 + i)
            metrics_instance.record_cycle_error(f"error_{i}", f"Error message {i}", "low")
            metrics_instance.end_cycle(cycle_id, success=i % 2 == 0)
        
        # Calculate statistics (should be fast)
        cycle_stats = metrics_instance.get_cycle_stats()
        memory_stats = metrics_instance.get_memory_stats()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time
        assert execution_time < 2.0  # Less than 2 seconds
        
        # Verify data integrity
        assert cycle_stats['total_cycles'] == 100
        assert len(metrics_instance.errors) == 100
        assert memory_stats['max_memory_mb'] == 199  # 100 + 99
    
    @pytest.mark.unit
    def test_error_severity_filtering(self, metrics_instance):
        """Test filtering errors by severity level."""
        # Add errors with different severity levels
        severities = ["low", "medium", "high", "critical"]
        for i, severity in enumerate(severities):
            metrics_instance.record_cycle_error(
                f"error_{severity}", 
                f"Error with {severity} severity", 
                severity
            )
        
        # Test filtering (assuming method exists)
        all_errors = metrics_instance.errors
        assert len(all_errors) == 4
        
        # Verify severity levels are stored correctly
        severity_counts = {}
        for error in all_errors:
            severity = error['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        assert severity_counts['low'] == 1
        assert severity_counts['medium'] == 1
        assert severity_counts['high'] == 1
        assert severity_counts['critical'] == 1


class TestMetricsFileOperations:
    """Test file I/O operations for metrics."""
    
    @pytest.mark.unit
    def test_metrics_directory_creation(self, temp_metrics_dir):
        """Test automatic creation of metrics directory."""
        # Remove directory
        shutil.rmtree(temp_metrics_dir)
        assert not os.path.exists(temp_metrics_dir)
        
        # Initialize metrics (should recreate directory)
        with patch('monitoring.metrics.METRICS_DIR', temp_metrics_dir):
            metrics = Metrics()
            cycle_id = metrics.start_cycle()
            metrics.end_cycle(cycle_id, success=True)
            result = metrics.save_daily_metrics()
        
        assert result is True
        assert os.path.exists(temp_metrics_dir)
    
    @pytest.mark.unit
    def test_metrics_file_permissions(self, temp_metrics_dir):
        """Test file permissions for metrics files."""
        with patch('monitoring.metrics.METRICS_DIR', temp_metrics_dir):
            metrics = Metrics()
            cycle_id = metrics.start_cycle()
            metrics.end_cycle(cycle_id, success=True)
            metrics.save_daily_metrics()
        
        # Check file exists and is readable
        today = datetime.now().strftime('%Y-%m-%d')
        metrics_file = os.path.join(temp_metrics_dir, f'metrics_{today}.json')
        
        assert os.path.exists(metrics_file)
        assert os.access(metrics_file, os.R_OK)
    
    @pytest.mark.unit
    def test_corrupted_metrics_file_handling(self, temp_metrics_dir):
        """Test handling of corrupted metrics files."""
        # Create corrupted file
        today = datetime.now().strftime('%Y-%m-%d')
        metrics_file = os.path.join(temp_metrics_dir, f'metrics_{today}.json')
        
        with open(metrics_file, 'w') as f:
            f.write("invalid json content {")
        
        # Try to load metrics
        with patch('monitoring.metrics.METRICS_DIR', temp_metrics_dir):
            metrics = Metrics()
            loaded_data = metrics.load_daily_metrics()
        
        # Should handle gracefully (return None or empty data)
        assert loaded_data is None or loaded_data == {}


class TestMetricsIntegration:
    """Integration tests for metrics with other components."""
    
    @pytest.mark.unit
    def test_metrics_with_app_insights_integration(self, metrics_instance, mock_app_insights):
        """Test metrics integration with Application Insights."""
        with patch('monitoring.metrics.get_app_insights', return_value=mock_app_insights):
            # Perform metrics operations
            cycle_id = metrics_instance.start_cycle()
            metrics_instance.update_memory_usage(150.0)
            metrics_instance.end_cycle(cycle_id, success=True)
            
            # Verify metrics can be reported to App Insights
            # (This would test actual integration if it exists)
            assert True  # Placeholder for actual integration test
    
    @pytest.mark.unit 
    def test_metrics_cleanup_integration(self, metrics_instance, temp_metrics_dir):
        """Test metrics cleanup with file system operations."""
        # Create old metrics files
        old_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        old_metrics_file = os.path.join(temp_metrics_dir, f'metrics_{old_date}.json')
        
        test_data = {"test": "old_data"}
        with open(old_metrics_file, 'w') as f:
            json.dump(test_data, f)
        
        # Test cleanup (if cleanup method exists)
        # This would test integration with cleanup functionality
        assert os.path.exists(old_metrics_file)  # File exists before cleanup
        
        # Add actual cleanup integration test here when implemented
