from unittest.mock import patch

from src.config.settings import Settings


def test_settings_load():
    with patch.dict(
        "os.environ",
        {
            "DSA_EMAIL": "test@example.com",
            "DSA_PASSWORD": "testpass",
            "OLLAMA_API_KEYS": "key1,key2,key3",
        },
    ):
        settings = Settings()
        assert settings.dsa_email == "test@example.com"
        assert settings.dsa_password == "testpass"
        assert len(settings.api_keys_list) == 3


def test_api_keys_parsing():
    with patch.dict(
        "os.environ",
        {
            "DSA_EMAIL": "test@example.com",
            "DSA_PASSWORD": "testpass",
            "OLLAMA_API_KEYS": "key1,key2,key3",
        },
    ):
        settings = Settings()
        keys = settings.api_keys_list
        assert all(isinstance(k, str) for k in keys)
        assert keys == ["key1", "key2", "key3"]
