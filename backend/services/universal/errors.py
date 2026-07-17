class UniversalSearchError(Exception):
    error_code = "universal_search_failed"


class UnknownProviderError(UniversalSearchError):
    error_code = "unknown_provider"


class DuplicateProviderError(UniversalSearchError):
    error_code = "duplicate_provider"

