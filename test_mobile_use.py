
try:
    from mobile_use.mobilerun import MobileRun
    print("MobileRun imported successfully")
except ImportError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"Other error: {e}")
