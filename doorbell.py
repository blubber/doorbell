from collections import deque
from datetime import datetime, timedelta
import sys

from pvrecorder import PvRecorder
import requests

WEBHOOK_URL = "http://homeassistant.local:8123/api/webhook/doorbell"


def send_event():
    now = datetime.now()

    if now - send_event.last_event > timedelta(seconds=5):
        send_event.last_event = now
        print(f"[{datetime.now()}]  Send event to home assistant")
        requests.post(WEBHOOK_URL)

send_event.last_event = datetime.min


def listen(recorder):
    frame_interval = recorder.frame_length / recorder.sample_rate
    maxlen = int(2 / frame_interval)
    buffer = deque([0] * maxlen, maxlen=maxlen)
    last_trigger = datetime.min

    while recorder.is_recording:
        frame = recorder.read()
        mean = sum(abs(x) for x in frame) / len(frame)

        buffer.append(mean)
        noise_floor = sum(buffer) / maxlen

        if (normalized := max(0, mean - noise_floor)) > 300:
            now = datetime.now()

            if now - last_trigger < timedelta(seconds=1):
                send_event()

            last_trigger = now


def main():
    microphone_name = sys.argv[1]

    available_devices = PvRecorder.get_available_devices()

    try:
        microphone_index = available_devices.index(microphone_name)
    except IndexError:
        print("Micropone not found")
        return -1

    recorder = PvRecorder(device_index=microphone_index, frame_length=1)

    sample_rate = recorder.sample_rate
    frame_length = sample_rate // 4

    recorder.delete()

    recorder = PvRecorder(device_index=microphone_index, frame_length=frame_length)
    recorder.start()

    try:
        listen(recorder)
    except KeyboardInterrupt:
        pass
    finally:
        recorder.delete()


if __name__ == "__main__":
    sys.exit(main())
