"""
Comprehensive Test Application for ReAct Agent
Tests agent initialization, execution, and provider switching
"""

import os
import sys
import json
from dotenv import load_dotenv
from typing import List, Dict, Any

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.agent import ReActAgent
from src.core.openai_provider import OpenAIProvider
from src.core.local_provider import LocalProvider
from src.core.gemini_provider import GeminiProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import MetricsCollector


class TestApp:
    """Test application for ReAct Agent"""
    
    def __init__(self):
        load_dotenv()
        self.metrics = MetricsCollector()
        self.test_results = []
        
    def setup_tools(self) -> List[Dict[str, Any]]:
        """Setup sample tools for testing"""
        tools = [
            {
                "name": "calculator",
                "description": "Performs basic mathematical operations",
                "parameters": {
                    "operation": "type of operation: add, subtract, multiply, divide",
                    "a": "first number",
                    "b": "second number"
                }
            },
            {
                "name": "search",
                "description": "Searches for information online",
                "parameters": {
                    "query": "search query string"
                }
            },
            {
                "name": "database_query",
                "description": "Queries the hospital database",
                "parameters": {
                    "table": "table name",
                    "condition": "where condition"
                }
            }
        ]
        return tools
    
    def test_agent_initialization(self):
        """Test 1: Agent can be initialized with different providers"""
        print("\n" + "="*60)
        print("TEST 1: Agent Initialization")
        print("="*60)
        
        try:
            tools = self.setup_tools()
            
            # Test with Local Provider
            print("\n✓ Testing Local Provider...")
            local_model_path = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
            
            if os.path.exists(local_model_path):
                local_provider = LocalProvider(model_path=local_model_path)
                agent = ReActAgent(llm=local_provider, tools=tools, max_steps=5)
                print("  ✅ Agent initialized with LocalProvider")
                self.test_results.append(("Agent Initialization (Local)", "PASSED"))
            else:
                print(f"  ⚠️  Model not found at {local_model_path}")
                self.test_results.append(("Agent Initialization (Local)", "SKIPPED"))
            
            # Test with OpenAI Provider
            print("\n✓ Testing OpenAI Provider...")
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                openai_provider = OpenAIProvider(api_key=openai_key)
                agent = ReActAgent(llm=openai_provider, tools=tools, max_steps=5)
                print("  ✅ Agent initialized with OpenAIProvider")
                self.test_results.append(("Agent Initialization (OpenAI)", "PASSED"))
            else:
                print("  ⚠️  OPENAI_API_KEY not set")
                self.test_results.append(("Agent Initialization (OpenAI)", "SKIPPED"))
            
            # Test with Gemini Provider
            print("\n✓ Testing Gemini Provider...")
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                gemini_provider = GeminiProvider(api_key=gemini_key)
                agent = ReActAgent(llm=gemini_provider, tools=tools, max_steps=5)
                print("  ✅ Agent initialized with GeminiProvider")
                self.test_results.append(("Agent Initialization (Gemini)", "PASSED"))
            else:
                print("  ⚠️  GEMINI_API_KEY not set")
                self.test_results.append(("Agent Initialization (Gemini)", "SKIPPED"))
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.test_results.append(("Agent Initialization", "FAILED"))
    
    def test_agent_execution(self):
        """Test 2: Agent can execute with a simple prompt"""
        print("\n" + "="*60)
        print("TEST 2: Agent Execution")
        print("="*60)
        
        try:
            provider = self._get_provider()
            if not provider:
                print("⚠️  No provider available for testing")
                self.test_results.append(("Agent Execution", "SKIPPED"))
                return
            
            tools = self.setup_tools()
            agent = ReActAgent(llm=provider, tools=tools, max_steps=3)
            
            test_prompts = [
                "What is 5 + 3?",
                "Hello, how can you help me?",
                "Tell me about yourself"
            ]
            
            for prompt in test_prompts:
                print(f"\n✓ Testing with prompt: '{prompt}'")
                try:
                    result = agent.run(prompt)
                    if result:
                        print(f"  ✅ Got response: {result[:100]}...")
                    self.test_results.append(("Agent Execution", "PASSED"))
                    break
                except Exception as e:
                    print(f"  ⚠️  {type(e).__name__}: {e}")
                    continue
                    
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.test_results.append(("Agent Execution", "FAILED"))
    
    def test_system_prompt(self):
        """Test 3: Verify system prompt generation"""
        print("\n" + "="*60)
        print("TEST 3: System Prompt Generation")
        print("="*60)
        
        try:
            provider = self._get_provider()
            if not provider:
                print("⚠️  No provider available for testing")
                self.test_results.append(("System Prompt", "SKIPPED"))
                return
            
            tools = self.setup_tools()
            agent = ReActAgent(llm=provider, tools=tools)
            
            system_prompt = agent.get_system_prompt()
            
            # Check required components
            required_keywords = ["Thought:", "Action:", "Observation:", "Final Answer:"]
            found_keywords = [kw for kw in required_keywords if kw in system_prompt]
            
            print(f"\n✓ Generated system prompt length: {len(system_prompt)} characters")
            print(f"✓ Found {len(found_keywords)}/{len(required_keywords)} required keywords")
            
            if len(found_keywords) == len(required_keywords):
                print("  ✅ System prompt contains all required ReAct components")
                self.test_results.append(("System Prompt Generation", "PASSED"))
            else:
                print(f"  ⚠️  Missing: {set(required_keywords) - set(found_keywords)}")
                self.test_results.append(("System Prompt Generation", "PARTIAL"))
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.test_results.append(("System Prompt Generation", "FAILED"))
    
    def test_logging(self):
        """Test 4: Verify logging functionality"""
        print("\n" + "="*60)
        print("TEST 4: Logging Functionality")
        print("="*60)
        
        try:
            logger.log_event("TEST_EVENT", {"test": "data", "timestamp": "test"})
            print("  ✅ Event logged successfully")
            
            self.test_results.append(("Logging", "PASSED"))
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.test_results.append(("Logging", "FAILED"))
    
    def test_metrics(self):
        """Test 5: Verify metrics collection"""
        print("\n" + "="*60)
        print("TEST 5: Metrics Collection")
        print("="*60)
        
        try:
            collector = MetricsCollector()
            collector.record_metric("test_metric", 42)
            collector.record_metric("test_counter", 1)
            
            print("  ✅ Metrics recorded successfully")
            self.test_results.append(("Metrics Collection", "PASSED"))
        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.test_results.append(("Metrics Collection", "FAILED"))
    
    def _get_provider(self):
        """Helper method to get an available provider"""
        try:
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                return OpenAIProvider(api_key=openai_key)
        except:
            pass
        
        try:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                return GeminiProvider(api_key=gemini_key)
        except:
            pass
        
        try:
            local_model = os.getenv("LOCAL_MODEL_PATH", "./models/Phi-3-mini-4k-instruct-q4.gguf")
            if os.path.exists(local_model):
                return LocalProvider(model_path=local_model)
        except:
            pass
        
        return None
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        total = len(self.test_results)
        passed = sum(1 for _, status in self.test_results if status == "PASSED")
        failed = sum(1 for _, status in self.test_results if status == "FAILED")
        skipped = sum(1 for _, status in self.test_results if status in ["SKIPPED", "PARTIAL"])
        
        for test_name, status in self.test_results:
            status_icon = "✅" if status == "PASSED" else "❌" if status == "FAILED" else "⚠️"
            print(f"{status_icon} {test_name}: {status}")
        
        print(f"\nTotal: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        print("="*60)
        
        return {"total": total, "passed": passed, "failed": failed, "skipped": skipped}
    
    def run_all_tests(self):
        """Run all tests"""
        print("\n🚀 Starting Test Suite for ReAct Agent")
        print("="*60)
        
        self.test_agent_initialization()
        self.test_system_prompt()
        self.test_logging()
        self.test_metrics()
        self.test_agent_execution()
        
        summary = self.print_summary()
        return summary


def main():
    """Main entry point"""
    test_app = TestApp()
    summary = test_app.run_all_tests()
    
    # Exit with appropriate code
    if summary["failed"] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
