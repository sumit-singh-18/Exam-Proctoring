import tkinter as tk  # for GUI portion
from tkinter import messagebox
import threading
import cv2  # for webcam access
import mediapipe as mp  # for face detection
import sounddevice as sd
import numpy as np
from pynput import keyboard
import sys
# -----------------------
# Global flags
# -----------------------
sound_enabled = False
running = True
suspicious_count = 0
SUSPICIOUS_LIMIT = 5
face_event_triggered = False
audio_event_triggered = False
last_warning_message = ""
# -----------------------
# Audio globals
# -----------------------
AUDIO_THRESHOLD = 0.02
audio_rms = 0.0

def audio_callback(indata, frames, time_info, status_info):
    global audio_rms
    audio_rms = np.sqrt(np.mean(indata.astype(np.float64)**2))

def audio_thread():
    try:
        with sd.InputStream(callback=audio_callback, channels=1, samplerate=44100):
            while running:
                sd.sleep(100)
    except Exception as e:
        print("Audio stream error:", e)

# -----------------------
# Keyboard listener
# -----------------------
def on_press(key):
    global sound_enabled, running, suspicious_count, last_warning_message
    try:
        if key.char in ['a', 'A']:
            sound_enabled = not sound_enabled
            print("Audio detection:", "ON" if sound_enabled else "OFF")
            return
        if key.char in ['q', 'Q']:
            running = False
            return False
    except AttributeError:
        pass

    # Any other key is suspicious
    try:
        key_name = str(key.char)
    except AttributeError:
        key_name = str(key)
    last_warning_message = f"Key pressed: {key_name}"
    suspicious_count += 1

listener = keyboard.Listener(on_press=on_press)
listener.start()

# -----------------------
# Face detection setup
# -----------------------
mp_face = mp.solutions.face_detection
mp_draw = mp.solutions.drawing_utils
face_detector = mp_face.FaceDetection(min_detection_confidence=0.5)

# -----------------------
# Proctoring dashboard function
# -----------------------
def start_proctoring():
    global running
    running = True
    threading.Thread(target=audio_thread, daemon=True).start()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "Cannot open webcam")
        return

    while running:
        ret, frame = cap.read()
        if not ret:
            break

        # -----------------------
        # Resize frame for larger dashboard
        # -----------------------
        frame = cv2.resize(frame, (1280, 720))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_detector.process(rgb)

        global face_event_triggered, audio_event_triggered
        if results.detections:
            face_event_triggered = False
            face_status = "FACE: DETECTED"
            face_color = (0, 255, 0)
        else:
            face_status = "FACE: NOT DETECTED"
            face_color = (0, 0, 255)
            if not face_event_triggered:
                global suspicious_count
                suspicious_count += 1
                global last_warning_message
                last_warning_message = "FACE MISSING!"
                face_event_triggered = True

        # Audio detection
        if sound_enabled and audio_rms > AUDIO_THRESHOLD:
            if not audio_event_triggered:
                suspicious_count += 1
                last_warning_message = "AUDIO DETECTED!"
                audio_event_triggered = True
        else:
            audio_event_triggered = False

        # -----------------------
        # Draw dashboard
        # -----------------------
        cv2.rectangle(frame, (0,0), (frame.shape[1], 180), (50,50,50), -1)
        cv2.putText(frame, face_status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, face_color, 2)
        cv2.putText(frame, f"Audio detection: {'ON' if sound_enabled else 'OFF'}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (200,200,200), 2)
        cv2.putText(frame, f"Suspicious count: {suspicious_count}/{SUSPICIOUS_LIMIT}", (10, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        if last_warning_message != "":
            cv2.putText(frame, f"⚠ {last_warning_message}", (10, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

        # -----------------------
        # Auto terminate with hold
        # -----------------------
        if suspicious_count >= SUSPICIOUS_LIMIT:
            cv2.putText(frame, "You Broke The Promise.. As Always You Do..", (10, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 3)
            
            # Hold the frame for 7 seconds
            end_time = cv2.getTickCount()
            fps = cv2.getTickFrequency()
            duration = 7  # seconds
            while (cv2.getTickCount() - end_time)/fps < duration:
                cv2.imshow("Proctoring Dashboard", frame)
                if cv2.waitKey(1) & 0xFF == 27:  # Esc can exit early
                    break

            running = False
            break

        cv2.imshow("Proctoring Dashboard", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    running = False
    cap.release()
    cv2.destroyAllWindows()
    listener.stop()

# -----------------------
# Tkinter GUI for checkbox
# -----------------------
def show_checkbox_window():
    def on_start():
        if var.get() == 1:
            root.destroy()
            start_proctoring()
        else:
            messagebox.showwarning("Cheater Alert!", "You didn't promise! You are a CHEATER! 🤣")
            root.destroy()
            sys.exit()

    root = tk.Tk()
    root.title("Exam Proctoring Agreement")
    root.geometry("500x200")

    tk.Label(root, text="Check the box to promise you won't cheat in this exam", font=("Arial", 12)).pack(pady=20)
    var = tk.IntVar()
    tk.Checkbutton(root, text="I PROMISE I WON'T CHEAT 😇", variable=var, font=("Arial", 12)).pack()
    tk.Button(root, text="Start Exam", command=on_start, font=("Arial", 12), bg="green", fg="white").pack(pady=20)

    root.mainloop()
# -----------------------
# Run the GUI first
# -----------------------
show_checkbox_window()
