from app.services.file_data_provider import FileDataProvider
# Add more imports for other DBs as needed

def get_data_provider(config):
    provider_type = getattr(config, 'DB_TYPE', 'file')
    provider_type = provider_type.lower().strip()
    if provider_type == 'file':
        return FileDataProvider(config.DATA_DIR)
    else:
        raise ValueError(f"Unsupported data provider: {provider_type}")
