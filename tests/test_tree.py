#!/usr/bin/env python3

"""
Test script to compare tree outputs.
"""

import os
from jrdev.utils.treechart import generate_tree, generate_compact_tree

# Get current directory
current_dir = os.getcwd()

# Generate tree with both methods
original_tree = generate_tree(current_dir, "original_tree.txt")
compact_tree = generate_compact_tree(current_dir, "compact_tree.txt")

# Compare token counts
print("Original tree size:", len(original_tree), "characters")
print("Compact tree size:", len(compact_tree), "characters")
print("Size reduction:", round((1 - len(compact_tree) / len(original_tree)) * 100, 2), "%")

# Print a sample of both outputs
print("\nSample of original tree output:")
print("\n".join(original_tree.split("\n")[:10]))

print("\nSample of compact tree output:")
print("\n".join(compact_tree.split("\n")[:10]))