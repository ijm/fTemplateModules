"""Verify all import hook patterns work correctly."""
# pylint: disable=import-error,no-name-in-module,reimported
import sys
from pathlib import Path

# Add parent directory to path for this test
sys.path.insert(0, str(Path(__file__).parent))

# Install the hook
from ftemplatemodules import install_hook  # noqa: E402
install_hook()

# Test 1: Top-level absolute import
import standalone as a  # noqa: E402
result = a.test()
assert result == "Ok.\n", f"standalone failed: got {result!r}"
print("✓ import standalone")

# Test 2: Absolute dotted import (path=None, dots resolved)
import testpkg.top as b  # noqa: E402
result = b.test()
assert result == "Ok.\n", f"testpkg.top failed: got {result!r}"
print("✓ import testpkg.top")

# Test 3: Deep absolute dotted import
import testpkg.subpkg.nested as c  # noqa: E402
result = c.test()
assert result == "Ok.\n", f"testpkg.subpkg.nested failed: got {result!r}"
print("✓ import testpkg.subpkg.nested")

# Test 4: from package import (path set)
from testpkg import top as d  # noqa: E402
result = d.test()
assert result == "Ok.\n", f"from testpkg import top failed: got {result!r}"
print("✓ from testpkg import top")

# Test 5: Deep from import (path set) - the most complex case
from testpkg.subpkg import nested as e  # noqa: E402
result = e.test()
msg = f"from testpkg.subpkg import nested failed: got {result!r}"
assert result == "Ok.\n", msg
print("✓ from testpkg.subpkg import nested")

# Test 6: from import specific function (most difficult with from)
from testpkg.subpkg.nested import test as nested_test  # noqa: E402
result = nested_test()
assert result == "Ok.\n", f"from nested import test failed: got {result!r}"
print("✓ from testpkg.subpkg.nested import test")

print("\nAll import hook tests passed!")
