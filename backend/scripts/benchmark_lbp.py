"""
NeoFace Anti-Spoof Service — LBP Vectorization Benchmark

Measures performance improvement from nested-loop LBP to vectorized NumPy.

Target improvement: 5x–20x faster without changing outputs.

Usage:
    python benchmark_lbp.py
"""

import time
import numpy as np
import cv2
from pathlib import Path


def lbp_variance_naive(gray: np.ndarray, radius: int = 1, n_points: int = 8) -> float:
    """
    Original nested-loop implementation (slow).
    
    This is the baseline we're comparing against.
    """
    h, w = gray.shape
    lbp = np.zeros_like(gray, dtype=np.float32)
    
    for i in range(1, h - 1):
        for j in range(1, w - 1):
            center = gray[i, j]
            code = 0
            neighbors = [
                gray[i-1, j-1], gray[i-1, j], gray[i-1, j+1],
                gray[i,   j+1], gray[i+1, j+1], gray[i+1, j],
                gray[i+1, j-1], gray[i,   j-1],
            ]
            for k, nb in enumerate(neighbors):
                if nb >= center:
                    code |= (1 << k)
            lbp[i, j] = code
    
    return float(lbp.var())


def lbp_variance_vectorized(gray: np.ndarray, radius: int = 1, n_points: int = 8) -> float:
    """
    Fully vectorized NumPy implementation (fast).
    
    Uses np.roll() for circular shifts and np.where() for vectorized operations.
    No Python loops.
    """
    h, w = gray.shape
    
    if h < 3 or w < 3:
        return 0.0
    
    # Extract center region (avoiding edges)
    center = gray[1:-1, 1:-1].astype(np.float32)
    
    # Get all 8 neighbors using np.roll() for circular shifts
    neighbors = [
        np.roll(np.roll(gray, 1, axis=0), 1, axis=1)[1:-1, 1:-1],    # top-left
        np.roll(gray, 1, axis=0)[1:-1, 1:-1],                        # top
        np.roll(np.roll(gray, 1, axis=0), -1, axis=1)[1:-1, 1:-1],   # top-right
        np.roll(gray, -1, axis=1)[1:-1, 1:-1],                       # right
        np.roll(np.roll(gray, -1, axis=0), -1, axis=1)[1:-1, 1:-1],  # bottom-right
        np.roll(gray, -1, axis=0)[1:-1, 1:-1],                       # bottom
        np.roll(np.roll(gray, -1, axis=0), 1, axis=1)[1:-1, 1:-1],   # bottom-left
        np.roll(gray, 1, axis=1)[1:-1, 1:-1],                        # left
    ]
    
    # Compute LBP codes vectorized
    lbp = np.zeros_like(center, dtype=np.uint8)
    
    for bit_pos, neighbor in enumerate(neighbors):
        lbp |= np.where(neighbor >= center, 1 << bit_pos, 0).astype(np.uint8)
    
    return float(np.var(lbp.astype(np.float32)))


def generate_test_image(width: int = 320, height: int = 240) -> np.ndarray:
    """Generate a test image with realistic texture."""
    # Create a base with different regions
    img = np.zeros((height, width), dtype=np.uint8)
    
    # Real face-like region (high texture variance)
    y1, y2 = 30, 150
    x1, x2 = 30, 180
    face_texture = np.random.normal(128, 25, (y2-y1, x2-x1)).astype(np.uint8)
    img[y1:y2, x1:x2] = face_texture
    
    # Printed photo region (low texture variance)
    y1, y2 = 30, 150
    x1, x2 = 190, 310
    photo_texture = np.random.normal(128, 5, (y2-y1, x2-x1)).astype(np.uint8)
    img[y1:y2, x1:x2] = photo_texture
    
    # Add some noise to all regions
    noise = np.random.normal(0, 3, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    return img


def benchmark_single_image(img: np.ndarray, iterations: int = 10) -> dict:
    """Run benchmark on a single image."""
    results = {
        "image_size": img.shape,
        "iterations": iterations,
        "naive": [],
        "vectorized": [],
    }
    
    # Warmup
    _ = lbp_variance_naive(img)
    _ = lbp_variance_vectorized(img)
    
    # Benchmark naive
    for _ in range(iterations):
        t0 = time.perf_counter()
        result_naive = lbp_variance_naive(img)
        t1 = time.perf_counter()
        results["naive"].append((t1 - t0) * 1000)  # ms
    
    # Benchmark vectorized
    for _ in range(iterations):
        t0 = time.perf_counter()
        result_vec = lbp_variance_vectorized(img)
        t1 = time.perf_counter()
        results["vectorized"].append((t1 - t0) * 1000)  # ms
    
    # Verify outputs match
    if abs(result_naive - result_vec) > 0.01:
        print(f"WARNING: Results differ! naive={result_naive:.4f}, vec={result_vec:.4f}")
    
    return results


def main():
    """Run comprehensive LBP benchmark."""
    print("=" * 70)
    print("NeoFace LBP Vectorization Benchmark")
    print("=" * 70)
    print()
    
    # Test multiple image sizes
    sizes = [
        (80, 80),       # MiniFASNet input size
        (160, 160),     # Typical face crop
        (320, 240),     # VGA
        (640, 480),     # D1
    ]
    
    all_results = {}
    
    for width, height in sizes:
        print(f"Testing {width}x{height} image...")
        print("-" * 70)
        
        img = generate_test_image(width, height)
        results = benchmark_single_image(img, iterations=20)
        all_results[(width, height)] = results
        
        naive_times = results["naive"]
        vec_times = results["vectorized"]
        
        naive_mean = np.mean(naive_times)
        naive_std = np.std(naive_times)
        vec_mean = np.mean(vec_times)
        vec_std = np.std(vec_times)
        speedup = naive_mean / vec_mean
        
        print(f"  Naive (nested loops):")
        print(f"    Mean: {naive_mean:.3f} ms, Std: {naive_std:.3f} ms")
        print(f"  Vectorized (NumPy):")
        print(f"    Mean: {vec_mean:.3f} ms, Std: {vec_std:.3f} ms")
        print(f"  Speedup: {speedup:.1f}x")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    speedups = []
    for (width, height), results in all_results.items():
        naive_mean = np.mean(results["naive"])
        vec_mean = np.mean(results["vectorized"])
        speedup = naive_mean / vec_mean
        speedups.append(speedup)
        print(f"{width:3d}x{height:3d}: {speedup:5.1f}x faster")
    
    avg_speedup = np.mean(speedups)
    min_speedup = np.min(speedups)
    max_speedup = np.max(speedups)
    
    print()
    print(f"Average speedup: {avg_speedup:.1f}x")
    print(f"Min speedup: {min_speedup:.1f}x")
    print(f"Max speedup: {max_speedup:.1f}x")
    print()
    
    # Target validation
    if avg_speedup >= 5.0:
        print("✓ PASS: Average speedup >= 5x")
    else:
        print("✗ FAIL: Average speedup < 5x")
    
    if max_speedup >= 20.0:
        print("✓ EXCELLENT: Max speedup >= 20x")
    elif max_speedup >= 10.0:
        print("✓ GOOD: Max speedup >= 10x")
    else:
        print("~ OK: Acceptable improvement")


if __name__ == "__main__":
    main()
