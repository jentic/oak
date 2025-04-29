from mcp.core.generators.code_samples import CODE_SAMPLES


def _normalise_format(format: str) -> str:
    """
    Normalizes various format inputs to match known formats in the CODE_SAMPLES dictionary.

    Args:
        format: The input format string to normalize (e.g., 'ChatGPT', 'chat_gpt', 'openai')

    Returns:
        A normalized format string that matches keys in CODE_SAMPLES
    """
    format = format.lower().replace("-", "").replace("_", "").replace(" ", "")

    # Map various format names to standard keys
    format_mapping = {
        # ChatGPT/OpenAI variations
        "chatgpt": "chatgpt",
        "openai": "chatgpt",
        # Claude/Anthropic variations
        "claude": "claude",
        "anthropic": "claude",
    }

    return format_mapping.get(format, "claude")  # Default to claude if no match


def generate_code_sample(format: str = "claude", language: str = "python") -> str:
    """
    Generate a code sample based on the specified format and programming language.

    Args:
        format: The format of the code sample to generate (e.g., 'claude', 'chatgpt')
        language: The programming language of the code sample (e.g., 'python', 'javascript')

    Returns:
        A string containing the requested code sample
    """
    format = _normalise_format(format)
    language = language.lower()

    # Check if the format exists
    if format in CODE_SAMPLES:
        # Check if the language exists for that format
        if language in CODE_SAMPLES[format]:
            return CODE_SAMPLES[format][language]
        else:
            # Get available languages for this format
            available_languages = list(CODE_SAMPLES[format].keys())
            error_message = f"Sample not found for programming language: {language}.\n"
            error_message += f'Available languages for {format}: {", ".join(available_languages)}'
            return error_message
    else:
        # If format not found, show available formats
        available_formats = list(CODE_SAMPLES.keys())
        error_message = f"Sample not found for format: {format}.\n"
        error_message += f'Available formats: {", ".join(available_formats)}'
        return error_message
