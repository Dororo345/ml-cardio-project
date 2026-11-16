"""Corrected acceptance check after the LZ10 negative CI experiment."""
from app import app


def test_lz10_login_is_available():
    with app.test_client() as client:
        response = client.get("/login")
        assert response.status_code == 200
        assert b"<html" in response.data.lower()
