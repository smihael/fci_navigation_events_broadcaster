import base64
import hashlib
import json
import os
import ssl
import threading
import time
from typing import Callable, Dict, Iterable, Optional
from urllib import parse

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool

import requests
from requests.packages import urllib3


BUTTONS = ("circle", "cross", "check", "left", "right", "down", "up")


def encode_desk_password(username: str, password: str) -> str:
    """Encode a Desk password the same way the Franka Desk login API expects."""
    digest = hashlib.sha256(f"{password}#{username}@franka".encode("utf-8")).digest()
    bytes_str = ",".join(str(byte) for byte in digest)
    return base64.encodebytes(bytes_str.encode("utf-8")).decode("utf-8")


class DeskNavigationEventClient:
    def __init__(
        self,
        host: str,
        event_path: str,
        username: str = "",
        password: str = "",
        authorization_token: str = "",
        timeout_s: float = 1.0,
        verify_tls: bool = False,
    ) -> None:
        self._host = host
        self._event_path = event_path
        self._username = username
        self._password = password
        self._authorization_token = authorization_token
        self._timeout_s = timeout_s
        self._verify_tls = verify_tls
        self._session = requests.Session()
        self._session.verify = verify_tls

        if not verify_tls:
            urllib3.disable_warnings()

    def listen(
        self,
        callback: Callable[[Dict[str, bool]], None],
        stop_event: threading.Event,
    ) -> None:
        import websocket

        self._login_if_configured()

        headers = []
        authorization = self._authorization_token or self._session.cookies.get("authorization")
        if authorization:
            headers.append(f"authorization: {authorization}")

        url = f"wss://{self._host}{self._event_path}"
        ssl_options = {}
        if not self._verify_tls:
            ssl_options = {
                "cert_reqs": ssl.CERT_NONE,
                "check_hostname": False,
            }

        ws = websocket.create_connection(
            url,
            header=headers,
            timeout=self._timeout_s,
            sslopt=ssl_options,
        )
        try:
            while not stop_event.is_set():
                try:
                    payload = ws.recv()
                    event = json.loads(payload)
                except websocket.WebSocketTimeoutException:
                    continue

                if isinstance(event, dict):
                    callback(event)
        finally:
            ws.close()

    def _login_if_configured(self) -> None:
        if self._authorization_token:
            return
        if not self._username and not self._password:
            return
        if not self._username or not self._password:
            raise ValueError("Desk username and password must either both be set or both be empty")

        response = self._session.post(
            parse.urljoin(f"https://{self._host}", "/admin/api/login"),
            json={
                "login": self._username,
                "password": encode_desk_password(self._username, self._password),
            },
        )
        if response.status_code != 200:
            raise ConnectionError(response.text)
        self._session.cookies.set("authorization", response.text)


def authorization_token_from_env(env_var_name: str) -> str:
    if not env_var_name:
        return ""
    return os.environ.get(env_var_name, "")


class NavigationEventsBroadcaster(Node):
    def __init__(self) -> None:
        super().__init__("navigation_events_broadcaster")

        self.declare_parameter("host", "192.168.1.1")
        self.declare_parameter("event_path", "/desk/api/navigation/events")
        self.declare_parameter("topic_namespace", "navigation_events")
        self.declare_parameter("username", "")
        self.declare_parameter("password", "")
        self.declare_parameter("authorization_token", "")
        self.declare_parameter("authorization_token_env", "FRANKA_DESK_AUTHORIZATION")
        self.declare_parameter("verify_tls", False)
        self.declare_parameter("reconnect_delay_s", 2.0)
        self.declare_parameter("websocket_timeout_s", 1.0)

        self._button_state = {button: False for button in BUTTONS}
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        topic_namespace = self._normalize_topic_namespace(
            self.get_parameter("topic_namespace").get_parameter_value().string_value
        )
        qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._publishers = {
            button: self.create_publisher(Bool, f"{topic_namespace}/{button}", qos)
            for button in BUTTONS
        }

        self._publish_initial_state(BUTTONS)
        self._start_listener()

    def destroy_node(self) -> bool:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        return super().destroy_node()

    def _start_listener(self) -> None:
        self._thread = threading.Thread(target=self._listen_forever, daemon=True)
        self._thread.start()

    def _listen_forever(self) -> None:
        reconnect_delay_s = self.get_parameter("reconnect_delay_s").value
        while rclpy.ok() and not self._stop_event.is_set():
            try:
                client = DeskNavigationEventClient(
                    host=self.get_parameter("host").value,
                    event_path=self.get_parameter("event_path").value,
                    username=self.get_parameter("username").value,
                    password=self.get_parameter("password").value,
                    authorization_token=self._authorization_token(),
                    timeout_s=self.get_parameter("websocket_timeout_s").value,
                    verify_tls=self.get_parameter("verify_tls").value,
                )
                client.listen(self._handle_event, self._stop_event)
            except Exception as exc:  # pylint: disable=broad-except
                if not self._stop_event.is_set():
                    self.get_logger().warn(
                        f"Desk navigation event listener disconnected: {exc}. "
                        f"Retrying in {reconnect_delay_s:.1f}s."
                    )
                    time.sleep(reconnect_delay_s)

    def _handle_event(self, event: Dict[str, bool]) -> None:
        for button in BUTTONS:
            if button not in event:
                continue

            value = bool(event[button])
            if self._button_state[button] == value:
                continue

            self._button_state[button] = value
            self._publish(button, value)

    def _publish_initial_state(self, buttons: Iterable[str]) -> None:
        for button in buttons:
            self._publish(button, False)

    def _publish(self, button: str, value: bool) -> None:
        message = Bool()
        message.data = value
        self._publishers[button].publish(message)

    def _authorization_token(self) -> str:
        token = self.get_parameter("authorization_token").value
        if token:
            return token
        env_var_name = self.get_parameter("authorization_token_env").value
        return authorization_token_from_env(env_var_name)

    @staticmethod
    def _normalize_topic_namespace(topic_namespace: str) -> str:
        namespace = topic_namespace.strip("/")
        return namespace if namespace else "navigation_events"


def main(args=None) -> None:
    rclpy.init(args=args)
    node = NavigationEventsBroadcaster()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
