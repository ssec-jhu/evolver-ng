from evolver import __version__


class TestHtmlApp:
    def test_html_network(self, app_client):
        response = app_client.get("/html/network")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/html; charset=utf-8"

        html_content = response.text
        assert "<html>" in html_content
        assert "<title>Evolver</title>" in html_content
        if __version__:
            assert __version__ in html_content
        assert "device network details" in html_content
        assert "Hostname:" in html_content
        assert "IP Address:" in html_content
