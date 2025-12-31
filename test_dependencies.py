#!/usr/bin/env python3
"""Test script to verify image handling dependencies"""

print("Testing image handling dependencies...\n")

# Test PIL/Pillow
try:
    from PIL import Image
    from io import BytesIO
    print("✅ PIL/Pillow is available")
    PIL_AVAILABLE = True
except ImportError as e:
    print(f"❌ PIL/Pillow NOT available: {e}")
    PIL_AVAILABLE = False

# Test openpyxl
try:
    import openpyxl
    from openpyxl.drawing.image import Image as ExcelImage
    from openpyxl.utils import get_column_letter
    print("✅ openpyxl is available")
    OPENPYXL_AVAILABLE = True
except ImportError as e:
    print(f"❌ openpyxl NOT available: {e}")
    OPENPYXL_AVAILABLE = False

# Test pandas
try:
    import pandas as pd
    print("✅ pandas is available")
    PANDAS_AVAILABLE = True
except ImportError as e:
    print(f"❌ pandas NOT available: {e}")
    PANDAS_AVAILABLE = False

# Test requests
try:
    import requests
    print("✅ requests is available")
    REQUESTS_AVAILABLE = True
except ImportError as e:
    print(f"❌ requests NOT available: {e}")
    REQUESTS_AVAILABLE = False

print("\n" + "="*50)
print("SUMMARY:")
print("="*50)
print(f"PIL/Pillow:  {'✅ OK' if PIL_AVAILABLE else '❌ MISSING'}")
print(f"openpyxl:    {'✅ OK' if OPENPYXL_AVAILABLE else '❌ MISSING'}")
print(f"pandas:      {'✅ OK' if PANDAS_AVAILABLE else '❌ MISSING'}")
print(f"requests:    {'✅ OK' if REQUESTS_AVAILABLE else '❌ MISSING'}")

if not all([PIL_AVAILABLE, OPENPYXL_AVAILABLE, PANDAS_AVAILABLE, REQUESTS_AVAILABLE]):
    print("\n⚠️  Some dependencies are missing!")
    print("Install them with:")
    missing = []
    if not PIL_AVAILABLE:
        missing.append("Pillow")
    if not OPENPYXL_AVAILABLE:
        missing.append("openpyxl")
    if not PANDAS_AVAILABLE:
        missing.append("pandas")
    if not REQUESTS_AVAILABLE:
        missing.append("requests")
    print(f"pip install {' '.join(missing)}")
else:
    print("\n✅ All dependencies are installed!")

