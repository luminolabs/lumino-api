import json

from app.core.utils import recursive_json_decode


def test_recursive_json_decode_basic():
    """Test basic JSON decoding."""
    # Simple string
    assert recursive_json_decode('{"key": "value"}') == {"key": "value"}

    # Nested structure
    nested = '{"outer": {"inner": "value"}}'
    assert recursive_json_decode(nested) == {"outer": {"inner": "value"}}

    # Array
    array = '[1, 2, 3]'
    assert recursive_json_decode(array) == [1, 2, 3]

def test_recursive_json_decode_nested():
    """Test nested JSON decoding."""
    # Deeply nested structure
    nested = json.dumps({
        "level1": json.dumps({
            "level2": json.dumps({
                "level3": "value"
            })
        })
    })

    expected = {
        "level1": {
            "level2": {
                "level3": "value"
            }
        }
    }

    assert recursive_json_decode(nested) == expected

def test_recursive_json_decode_mixed():
    """Test mixed content JSON decoding."""
    # Mix of encoded and non-encoded data
    mixed = {
        "encoded": json.dumps({"key": "value"}),
        "plain": "text",
        "number": 42,
        "list": json.dumps([1, 2, 3])
    }

    expected = {
        "encoded": {"key": "value"},
        "plain": "text",
        "number": 42,
        "list": [1, 2, 3]
    }

    assert recursive_json_decode(mixed) == expected

def test_recursive_json_decode_invalid():
    """Test invalid JSON handling."""
    # Invalid JSON string should be returned as-is
    invalid = "Not a JSON string"
    assert recursive_json_decode(invalid) == invalid

    # Partially invalid structure
    partial = {
        "valid": json.dumps({"key": "value"}),
        "invalid": "Not JSON"
    }

    result = recursive_json_decode(partial)
    assert result["valid"] == {"key": "value"}
    assert result["invalid"] == "Not JSON"

def test_recursive_json_decode_special_types():
    """Test JSON decoding with special types."""
    # Test with None
    assert recursive_json_decode(None) is None

    # Test with numbers
    assert recursive_json_decode(42) == 42
    assert recursive_json_decode(3.14) == 3.14

    # Test with boolean
    assert recursive_json_decode(True) is True
    assert recursive_json_decode(False) is False

def test_recursive_json_decode_complex_nested():
    """Test complex nested structures with mixed content."""
    complex_data = {
        "string": "plain text",
        "encoded_dict": json.dumps({"key": "value"}),
        "list_mixed": [
            json.dumps({"item": 1}),
            "plain",
            json.dumps([1, 2, 3])
        ],
        "nested_dict": {
            "encoded": json.dumps({"deep": "value"}),
            "plain": "text"
        }
    }

    result = recursive_json_decode(complex_data)

    assert result["string"] == "plain text"
    assert result["encoded_dict"] == {"key": "value"}
    assert result["list_mixed"][0] == {"item": 1}
    assert result["list_mixed"][1] == "plain"
    assert result["list_mixed"][2] == [1, 2, 3]
    assert result["nested_dict"]["encoded"] == {"deep": "value"}
    assert result["nested_dict"]["plain"] == "text"