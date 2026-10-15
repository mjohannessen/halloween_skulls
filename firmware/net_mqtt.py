"""WiFi + MQTT wiring for the Halloween skulls control box.

Same as lr_light's net_mqtt.py (itself adapted from led_flowerpot's).
Connects to WiFi and the mosquitto broker on the Mac mini, subscribes to
`skulls/command`, and forwards each payload into
skulls_controller.handle_command() — no parsing of its own, so the serial
protocol works identically over MQTT. Replies are republished
(retained) to `skulls/reply`.

Topics:
    skulls/command   in: one command per message
    skulls/reply     out, retained: OK / ERR ... / STATUS lines / HELP text
    skulls/status    out, retained LWT: online / offline — availability only,
                      since openHAB parses every message on its availability
                      topic as online/offline (the flowerpot logged a WARN per
                      reply when the two shared a topic)
    skulls/power     out, retained: ON / OFF, republished whenever it
                      changes, whoever changed it (MQTT, serial, startup) —
                      openHAB's switch uses it as its state topic so it
                      follows the web UI

Broker: 192.168.1.220:1883, anonymous, no TLS.
"""

import network
import time
from umqtt.simple import MQTTClient, MQTTException

from wifi_secrets import WIFI_SSID, WIFI_PASSWORD

BROKER_HOST = "192.168.1.220"
BROKER_PORT = 1883
CLIENT_ID = "skulls-pico-1"
KEEPALIVE_S = 60  # so the broker reaps a session orphaned by a hard reset
TOPIC_COMMAND = b"skulls/command"
TOPIC_STATUS = b"skulls/status"
TOPIC_REPLY = b"skulls/reply"
TOPIC_POWER = b"skulls/power"

WIFI_CONNECT_TIMEOUT_MS = 15000  # first connect, at boot
WIFI_RECONNECT_TIMEOUT_MS = 3000  # after a drop; short so patterns don't stall
RECONNECT_INTERVAL_MS = 5000
# umqtt.simple never pings on its own, and check_msg() just sees "no data" on
# a half-open socket, so a session the broker dropped while WiFi was out
# (2026-10-14: "disconnected: Operation timed out") went unnoticed until a
# power cycle. Pinging makes the broker answer with an RST, which the next
# check_msg() raises on, so poll() reconnects.
PING_INTERVAL_MS = KEEPALIVE_S * 1000 // 2

wlan = network.WLAN(network.STA_IF)


def wifi_connect(timeout_ms=WIFI_CONNECT_TIMEOUT_MS, feed=None):
    """Blocking connect with a timeout; returns True/False. Doesn't re-call
    .connect() mid-join (that restarts the association), and catches
    everything: the cyw43 driver occasionally raises OSError out of
    connect()/isconnected(), which would otherwise kill main()'s loop."""
    try:
        if wlan.isconnected():
            return True
        wlan.active(True)
        if wlan.status() != network.STAT_CONNECTING:
            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        start = time.ticks_ms()
        while not wlan.isconnected():
            if feed:
                feed()
            if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
                print("WiFi connect timed out (status=%d)" % wlan.status())
                return False
            time.sleep_ms(100)
        print("WiFi connected:", wlan.ifconfig())
        return True
    except Exception as e:
        print("WiFi connect failed:", e)
        return False


class SkullsMQTT:
    """Call poll() once per main-loop tick. Non-blocking once connected; on a
    drop it retries at most every RECONNECT_INTERVAL_MS."""

    def __init__(self, handle_command, get_power, feed=None):
        self.handle_command = handle_command
        self.get_power = get_power
        self.feed = feed
        self.client = None
        self.connected = False
        self._last_attempt = 0
        self._last_ping = 0
        self._first_attempt = True
        self._published_power = None

    def _on_message(self, topic, msg):
        # handle_command() takes an `out` callback because this MicroPython
        # build has no swappable sys.stdout to capture print() with
        lines = []
        self.handle_command(msg.decode(), out=lambda s: lines.append(str(s)))
        if lines:
            self._publish(TOPIC_REPLY, "\n".join(lines))

    def _publish(self, topic, payload):
        try:
            self.client.publish(topic, payload.encode(), retain=True)
            return True
        except (OSError, MQTTException) as e:
            print("MQTT publish failed:", e)
            self.connected = False
            return False

    def _connect(self, wifi_timeout_ms):
        if not wifi_connect(wifi_timeout_ms, feed=self.feed):
            return False
        if self.client:
            try:
                self.client.sock.close()  # the dead session's socket
            except Exception:
                pass
            self.client = None
        client =MQTTClient(CLIENT_ID, BROKER_HOST, port=BROKER_PORT, keepalive=KEEPALIVE_S)
        client.set_last_will(TOPIC_STATUS, b"offline", retain=True)
        client.set_callback(self._on_message)
        try:
            client.connect()
            client.subscribe(TOPIC_COMMAND)
            client.publish(TOPIC_STATUS, b"online", retain=True)
        except (OSError, MQTTException) as e:
            print("MQTT connect failed:", e)
            return False
        self.client = client
        self.connected = True
        self._last_ping = time.ticks_ms()
        self._published_power = None  # republish power after every reconnect
        print("MQTT connected to", BROKER_HOST)
        return True

    def poll(self):
        now = time.ticks_ms()
        if not self.connected:
            if time.ticks_diff(now, self._last_attempt) < RECONNECT_INTERVAL_MS:
                return
            self._last_attempt = now
            timeout = WIFI_CONNECT_TIMEOUT_MS if self._first_attempt else WIFI_RECONNECT_TIMEOUT_MS
            self._first_attempt = False
            self._connect(timeout)
            return

        try:
            self.client.check_msg()
        except (OSError, MQTTException) as e:
            print("MQTT check_msg failed, will reconnect:", e)
            self.connected = False
            return

        if time.ticks_diff(now, self._last_ping) >= PING_INTERVAL_MS:
            self._last_ping = now
            try:
                self.client.ping()
            except (OSError, MQTTException) as e:
                print("MQTT ping failed, will reconnect:", e)
                self.connected = False
                return

        power = self.get_power()
        if power != self._published_power:
            if self._publish(TOPIC_POWER, "ON" if power else "OFF"):
                self._published_power = power
