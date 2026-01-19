"""
Tests for the duplicate key handling utility functions in hierarchy_crud.py
"""
import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.hierarchy_crud import get_next_available_number, get_next_available_code


class TestGetNextAvailableNumber:
    """Tests for the get_next_available_number utility function"""
    
    def test_sequential_list_returns_next(self):
        """[1, 2, 3] should return 4"""
        assert get_next_available_number([1, 2, 3]) == 4
    
    def test_sequential_with_gaps(self):
        """[1, 3, 5] should return 6 (sequential)"""
        assert get_next_available_number([1, 3, 5]) == 6
    
    def test_empty_list_returns_one(self):
        """Empty list should return 1"""
        assert get_next_available_number([]) == 1
    
    def test_starting_gap_sequential(self):
        """[2, 3] should return 4 (sequential)"""
        assert get_next_available_number([2, 3]) == 4
    
    def test_large_gap_sequential(self):
        """[1, 100] should return 101 (sequential)"""
        assert get_next_available_number([1, 100]) == 101
    
    def test_multiple_gaps_sequential(self):
        """[1, 3, 7, 10] should return 11 (max + 1)"""
        assert get_next_available_number([1, 3, 7, 10]) == 11
    
    def test_ignores_negative_numbers(self):
        """[-1, 0, 2, 3] should return 4 (negatives/zero ignored, max+1)"""
        assert get_next_available_number([-1, 0, 2, 3]) == 4
    
    def test_ignores_zero(self):
        """[0, 2, 3] should return 4 (zero ignored, max+1)"""
        assert get_next_available_number([0, 2, 3]) == 4
    
    def test_single_element(self):
        """[1] should return 2"""
        assert get_next_available_number([1]) == 2
    
    def test_single_element_sequential(self):
        """[5] should return 6"""
        assert get_next_available_number([5]) == 6


class TestGetNextAvailableCode:
    """Tests for the get_next_available_code utility function"""
    
    def test_empty_list_returns_prefix_001(self):
        """Empty list should return PREFIX001"""
        assert get_next_available_code([], "SUBJ") == "SUBJ001"
    
    def test_sequential_codes_returns_next(self):
        """[SUBJ001, SUBJ002] should return SUBJ003"""
        assert get_next_available_code(["SUBJ001", "SUBJ002"], "SUBJ") == "SUBJ003"
    
    def test_sequential_codes(self):
        """[SUBJ001, SUBJ003] should return SUBJ004 (sequential)"""
        assert get_next_available_code(["SUBJ001", "SUBJ003"], "SUBJ") == "SUBJ004"
    
    def test_different_prefix_ignored(self):
        """Codes with different prefixes should be ignored"""
        assert get_next_available_code(["OTHER001", "OTHER002"], "SUBJ") == "SUBJ001"
    
    def test_mixed_prefixes(self):
        """Should only consider codes with matching prefix (sequential)"""
        assert get_next_available_code(["SUBJ001", "OTHER002", "SUBJ003"], "SUBJ") == "SUBJ004"
    
    def test_custom_prefix(self):
        """Should work with custom prefixes"""
        assert get_next_available_code(["CS001", "CS002"], "CS") == "CS003"


if __name__ == "__main__":
    # Simple test runner for quick validation
    import traceback
    
    tests_passed = 0
    tests_failed = 0
    
    for test_class in [TestGetNextAvailableNumber, TestGetNextAvailableCode]:
        instance = test_class()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"✓ {test_class.__name__}.{method_name}")
                    tests_passed += 1
                except AssertionError as e:
                    print(f"✗ {test_class.__name__}.{method_name}: {e}")
                    tests_failed += 1
                except Exception as e:
                    print(f"✗ {test_class.__name__}.{method_name}: {traceback.format_exc()}")
                    tests_failed += 1
    
    print(f"\n{tests_passed} passed, {tests_failed} failed")
