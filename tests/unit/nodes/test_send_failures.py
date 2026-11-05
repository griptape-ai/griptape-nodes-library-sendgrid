"""Send failures through the real SDK path, with `OpenerDirector.open` patched to fail.

Needs the engine installed, so it is skipped where it is not.
"""

import importlib.util
import socket
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytest.importorskip("griptape_nodes")
pytest.importorskip("sendgrid")

from griptape_nodes.exe_types.core_types import NodeError  # noqa: E402
from griptape_nodes.retained_mode.griptape_nodes import GriptapeNodes  # noqa: E402

NODE_FILE = Path(__file__).parents[3] / "sendgrid_nodes" / "sendgrid_email_node.py"


def _load_node_class():
    spec = importlib.util.spec_from_file_location("sendgrid_email_node_under_test", NODE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SendGridEmailNode


@pytest.fixture
def node(monkeypatch):
    node = _load_node_class()(name="Email")
    monkeypatch.setattr(GriptapeNodes.SecretsManager(), "get_secret", lambda *_a, **_k: "SG.test")
    values = {"to": "a@example.com", "from": "b@example.com", "text_content": "hi", "send": True}
    monkeypatch.setattr(node, "get_parameter_value", lambda name: values.get(name))
    monkeypatch.setattr(node, "get_parameter_list_value", lambda _name: [])
    return node


@pytest.mark.parametrize(
    "reason",
    [ConnectionRefusedError(111, "Connection refused"), socket.timeout("timed out"), socket.gaierror(8, "no such host")],
)
def test_unreachable_urlerror_has_a_plain_message(node, monkeypatch, reason):
    def fail(self, request, timeout=None):
        raise urllib.error.URLError(reason)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", fail)
    with pytest.raises(NodeError) as raised:
        node.process()
    message = str(raised.value)
    assert message == "Could not reach SendGrid. Check your internet connection, then run the node again."
    assert "urlopen" not in message
    assert raised.value.fields["reason"] == str(reason)
