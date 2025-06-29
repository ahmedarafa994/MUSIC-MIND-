import pytest
import asyncio
from unittest.mock import Mock, patch
from app.services.api_integration_manager import APIIntegrationManager, GenericAPIClient

@pytest.fixture
def api_manager():
    return APIIntegrationManager()

@pytest.fixture
def mock_client():
    return GenericAPIClient(
        endpoint="https://test.api.com",
        api_key="test-key",
        timeout=30,
        provider="test"
    )

class TestAPIIntegrationManager:
    
    @pytest.mark.asyncio
    async def test_initialize_clients(self, api_manager):
        """Test API client initialization"""
        with patch.object(api_manager, 'api_configs', {
            "test_service": {
                "provider": "test",
                "endpoint": "https://test.com",
                "api_key_env": "TEST_API_KEY",
                "rate_limit": {"requests_per_minute": 60},
                "timeout": 30
            }
        }):
            with patch('app.core.config.settings') as mock_settings:
                mock_settings.TEST_API_KEY = "test-key"
                await api_manager.initialize_clients()
                
                assert "test_service" in api_manager.api_clients
                assert "test_service" in api_manager.rate_limiters

    @pytest.mark.asyncio
    async def test_execute_api_request_success(self, api_manager):
        """Test successful API request execution"""
        mock_client = Mock()
        mock_client.execute_request.return_value = {"result": "success"}
        
        api_manager.api_clients["test_service"] = mock_client
        api_manager.api_configs["test_service"] = {
            "retry_attempts": 3,
            "cost_per_request": 0.01
        }
        
        # Mock rate limiter
        mock_rate_limiter = Mock()
        mock_rate_limiter.can_proceed.return_value = True
        mock_rate_limiter.record_request.return_value = None
        api_manager.rate_limiters["test_service"] = mock_rate_limiter
        
        with patch('app.services.cost_tracker.cost_tracker.track_usage'):
            result = await api_manager.execute_api_request(
                "test_service", 
                {"prompt": "test"}
            )
            
            assert result["status"] == "success"
            assert result["response"] == {"result": "success"}
            assert "execution_time" in result

    @pytest.mark.asyncio
    async def test_execute_api_request_rate_limited(self, api_manager):
        """Test rate limit handling"""
        from app.core.exceptions import RateLimitExceededError
        
        mock_rate_limiter = Mock()
        mock_rate_limiter.can_proceed.return_value = False
        api_manager.rate_limiters["test_service"] = mock_rate_limiter
        api_manager.api_clients["test_service"] = Mock()
        
        with pytest.raises(RateLimitExceededError):
            await api_manager.execute_api_request(
                "test_service", 
                {"prompt": "test"}
            )

    def test_calculate_cost_per_request(self, api_manager):
        """Test cost calculation for per-request pricing"""
        cost = api_manager._calculate_cost(
            "test_service",
            {"duration": 30},
            10.0
        )
        
        # Should return default cost since service not in configs
        assert cost == 0.01

    def test_calculate_cost_per_second(self, api_manager):
        """Test cost calculation for per-second pricing"""
        api_manager.api_configs["test_service"] = {
            "cost_per_second": 0.01
        }
        
        cost = api_manager._calculate_cost(
            "test_service",
            {"duration": 30},
            10.0
        )
        
        assert cost == 0.30  # 30 seconds * 0.01

class TestGenericAPIClient:
    
    @pytest.mark.asyncio
    async def test_huggingface_request(self, mock_client):
        """Test Hugging Face API request formatting"""
        mock_client.provider = "huggingface"
        
        with patch.object(mock_client, 'client') as mock_http_client:
            mock_response = Mock()
            mock_response.json.return_value = {"audio": "data"}
            mock_response.raise_for_status.return_value = None
            mock_http_client.post.return_value = mock_response
            
            result = await mock_client.execute_request({
                "prompt": "test music",
                "duration": 30
            })
            
            assert result == {"audio": "data"}
            
            # Verify the request was formatted correctly
            call_args = mock_http_client.post.call_args
            assert call_args[1]["json"]["inputs"] == "test music"
            assert call_args[1]["json"]["parameters"]["duration"] == 30

    @pytest.mark.asyncio
    async def test_stability_request(self, mock_client):
        """Test Stability AI API request formatting"""
        mock_client.provider = "stability_ai"
        
        with patch.object(mock_client, 'client') as mock_http_client:
            mock_response = Mock()
            mock_response.json.return_value = {"audio_url": "https://example.com/audio.wav"}
            mock_response.raise_for_status.return_value = None
            mock_http_client.post.return_value = mock_response
            
            result = await mock_client.execute_request({
                "prompt": "electronic music",
                "duration": 60
            })
            
            assert result == {"audio_url": "https://example.com/audio.wav"}
            
            # Verify the request was formatted correctly
            call_args = mock_http_client.post.call_args
            assert call_args[1]["json"]["prompt"] == "electronic music"
            assert call_args[1]["json"]["duration"] == 60

if __name__ == "__main__":
    pytest.main([__file__])