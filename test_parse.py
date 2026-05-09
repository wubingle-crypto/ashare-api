#!/usr/bin/env python3
"""Test Tencent API parsing."""
import re
import subprocess

# Test raw data
result = subprocess.run(
    ["curl", "-s", "https://qt.gtimg.cn/q=sh600519", "--max-time", "8"],
    capture_output=True,
    timeout=10,
)
raw = result.stdout
try:
    raw = raw.decode("utf-8")
except UnicodeDecodeError:
    raw = raw.decode("gbk")

print(f"Raw length: {len(raw)}")
print(f"Raw ends with: {repr(raw[-50:])}")
print(f"Raw has newline: {raw.endswith(chr(10))}")
print(f"Raw repr first 80: {repr(raw[:80])}")

# Try regex
match = re.search(r'^[^=]+="(.+)"\s*$', raw, re.MULTILINE)
print(f"\nRegex match: {match}")
if match:
    fields = match.group(1).split("~")
    print(f"Fields count: {len(fields)}")
    print(f"Code: {fields[2]}, Name: {fields[1]}, Price: {fields[3]}")
else:
    # Try parsing without regex - just extract between quotes
    start = raw.find('"')
    end = raw.rfind('"')
    if start >= 0 and end > start:
        content = raw[start+1:end]
        fields = content.split("~")
        print(f"Manual parse - Fields: {len(fields)}")
        print(f"Code: {fields[2]}, Name: {fields[1]}, Price: {fields[3]}")
