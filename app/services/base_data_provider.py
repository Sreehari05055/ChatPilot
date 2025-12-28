class BaseDataProvider:
    """
    Abstract base class for all data providers.
    """
    def fetch_documents(self):
        """
        Should return a list of dicts, each representing a document.
        """
        raise NotImplementedError("fetch_documents() must be implemented by subclasses.")
