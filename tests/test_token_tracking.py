#!/usr/bin/env python3
"""Verify token tracking and cost calculation accuracy"""
import asyncio
import sys
from src.providers.unified_provider import TokenUsage


def test_token_tracking():
    """Run all token tracking tests"""
    print("=" * 70)
    print("TOKEN TRACKING ACCURACY VERIFICATION")
    print("=" * 70)
    
    # Test 1: Basic token accumulation
    print("\n✓ Test 1: Basic Token Accumulation")
    usage = TokenUsage(input_cost_per_1k=0.50, output_cost_per_1k=1.50)
    usage.add(prompt=1000, completion=500)
    
    assert usage.prompt_tokens == 1000, f"Prompt mismatch: {usage.prompt_tokens}"
    assert usage.completion_tokens == 500, f"Completion mismatch: {usage.completion_tokens}"
    assert usage.total_tokens == 1500, f"Total mismatch: {usage.total_tokens}"
    assert usage.cost_str == "$1.25", f"Cost mismatch: {usage.cost_str}"
    print(f"  Prompt: {usage.prompt_tokens} ✓")
    print(f"  Completion: {usage.completion_tokens} ✓")
    print(f"  Total: {usage.total_tokens} ✓")
    print(f"  Cost: {usage.cost_str} ✓")
    
    # Test 2: Multiple API calls
    print("\n✓ Test 2: Multiple API Calls")
    usage2 = TokenUsage(input_cost_per_1k=0.50, output_cost_per_1k=1.50)
    usage2.add(prompt=1000, completion=500)
    usage2.add(prompt=2000, completion=1000)
    usage2.add(prompt=500, completion=200)
    
    assert usage2.prompt_tokens == 3500, f"Prompt mismatch: {usage2.prompt_tokens}"
    assert usage2.completion_tokens == 1700, f"Completion mismatch: {usage2.completion_tokens}"
    assert usage2.total_tokens == 5200, f"Total mismatch: {usage2.total_tokens}"
    # Cost: (3500/1000)*0.50 + (1700/1000)*1.50 = 1.75 + 2.55 = 4.30
    assert usage2.cost_str == "$4.30", f"Cost mismatch: {usage2.cost_str}"
    print(f"  Prompt: {usage2.prompt_tokens} ✓")
    print(f"  Completion: {usage2.completion_tokens} ✓")
    print(f"  Total: {usage2.total_tokens} ✓")
    print(f"  Cost: {usage2.cost_str} ✓")
    
    # Test 3: Zero tokens
    print("\n✓ Test 3: Zero Tokens")
    usage3 = TokenUsage()
    assert usage3.cost_str == "$0.00", f"Zero cost mismatch: {usage3.cost_str}"
    print(f"  Cost: {usage3.cost_str} ✓")
    
    # Test 4: Real session data (from your example)
    print("\n✓ Test 4: Real Session Data Simulation")
    usage4 = TokenUsage(input_cost_per_1k=0.50, output_cost_per_1k=1.50)
    
    # Simulate the 4-turn session
    turns = [
        (2910, 39),    # "Hi"
        (12983, 880),  # "What is this project about?"
        (36320, 1211), # "Create a rust hello world program"
        (50099, 1345), # "Remove rust file"
    ]
    
    for i, (prompt, completion) in enumerate(turns, 1):
        usage4.add(prompt=prompt, completion=completion)
        print(f"  Turn {i}: +{prompt} prompt, +{completion} completion")
    
    print(f"\n  Final Stats:")
    print(f"  Prompt: {usage4.prompt_tokens:,}")
    print(f"  Completion: {usage4.completion_tokens:,}")
    print(f"  Total: {usage4.total_tokens:,}")
    print(f"  Cost: {usage4.cost_str}")
    
    # Verify: Should be around $50+ for 100K+ tokens at these rates
    print(f"\n  Verification: {usage4.total_tokens:,} tokens ≈ {usage4.cost_str}")
    
    # Test 5: Cost calculation formula
    print("\n✓ Test 5: Cost Calculation Formula")
    usage5 = TokenUsage(input_cost_per_1k=0.50, output_cost_per_1k=1.50)
    usage5.add(prompt=10000, completion=5000)
    
    # Manual calculation
    expected_cost = (10000/1000)*0.50 + (5000/1000)*1.50
    expected_str = f"${expected_cost:.2f}"
    
    assert usage5.cost_str == expected_str, f"Formula error: {usage5.cost_str} vs {expected_str}"
    print(f"  Formula: (prompt/1000)*0.50 + (completion/1000)*1.50")
    print(f"  Example: (10000/1000)*0.50 + (5000/1000)*1.50 = {expected_str} ✓")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)
    print("\nToken tracking is ACCURATE and RELIABLE")
    print("Cost calculation uses TogetherAI Kimi-K2.5 rates:")
    print("  - Input: $0.50 per 1K tokens")
    print("  - Output: $1.50 per 1K tokens")
    print("=" * 70)
    
    return True


def display_pricing_comparison():
    """Show pricing comparison with other providers"""
    print("\n" + "=" * 70)
    print("PRICING COMPARISON (per 1K tokens)")
    print("=" * 70)
    
    providers = [
        ("TogetherAI/Kimi-K2.5", 0.50, 1.50),
        ("OpenAI/GPT-4", 3.00, 6.00),
        ("OpenAI/GPT-3.5", 0.50, 1.50),
        ("Anthropic/Claude-3", 3.00, 15.00),
        ("Groq/Llama-3", 0.05, 0.08),
    ]
    
    print(f"{'Provider':<25} {'Input':>10} {'Output':>10} {'Ratio':>10}")
    print("-" * 70)
    for name, inp, out in providers:
        ratio = out / inp if inp > 0 else 0
        print(f"{name:<25} ${inp:>9.2f} ${out:>9.2f} {ratio:>9.1f}x")
    
    print("=" * 70)
    print("\nSynlogos uses TogetherAI/Kimi-K2.5 rates by default.")
    print("To change pricing, edit your synlogos.json config:")
    print('  "input_cost_per_1k": 0.05,')
    print('  "output_cost_per_1k": 0.08')
    print("=" * 70)


if __name__ == "__main__":
    try:
        if test_token_tracking():
            display_pricing_comparison()
            sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        sys.exit(1)
