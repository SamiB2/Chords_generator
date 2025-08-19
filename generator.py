from flask import Flask, render_template, Response, jsonify
import random
import time
import mido
import threading
import json

app = Flask(__name__)

# --- Global variables ---
score = 0
time_limit = 60
session_active = False
current_chord = None
played_notes = set()
session_start_time = None     # session timer (do NOT reset during session)
chord_start_time = None       # per-chord timer (reset when new chord chosen)
device_name = None
last_points = 0

# --- Chords dictionary ---
chords = { "C major": ["C", "E", "G"], 
          "C# major": ["C#", "E#", "G#"], 
          "D major": ["D", "F#", "A"], 
          "Eb major": ["Eb", "G", "Bb"], 
          "E major": ["E", "G#", "B"], 
          "F major": ["F", "A", "C"], 
          "F# major": ["F#", "A#", "C#"], 
          "G major": ["G", "B", "D"], 
          "Ab major": ["Ab", "C", "Eb"], 
          "A major": ["A", "C#", "E"], 
          "Bb major": ["Bb", "D", "F"], 
          "B major": ["B", "D#", "F#"], 
          "C minor": ["C", "Eb", "G"], 
          "C# minor": ["C#", "E", "G#"], 
          "D minor": ["D", "F", "A"], 
          "Eb minor": ["Eb", "Gb", "Bb"], 
          "E minor": ["E", "G", "B"], 
          "F minor": ["F", "Ab", "C"], 
          "F# minor": ["F#", "A", "C#"], 
          "G minor": ["G", "Bb", "D"], 
          "Ab minor": ["Ab", "B", "Eb"], 
          "A minor": ["A", "C", "E"], 
          "Bb minor": ["Bb", "Db", "F"], 
          "B minor": ["B", "D", "F#"], 
          "C diminished": ["C", "Eb", "Gb"], 
          "C# diminished": ["C#", "E", "G"], 
          "D diminished": ["D", "F", "Ab"], 
          "Eb diminished": ["Eb", "Gb", "A"], 
          "E diminished": ["E", "G", "Bb"], 
          "F diminished": ["F", "Ab", "B"], 
          "F# diminished": ["F#", "A", "C"], 
          "G diminished": ["G", "Bb", "Db"], 
          "Ab diminished": ["Ab", "Cb", "D"], 
          "A diminished": ["A", "C", "Eb"], 
          "Bb diminished": ["Bb", "Db", "E"], 
          "B diminished": ["B", "D", "F"] 
}

enharmonic_map = {
    "C": "C", "B#": "C",
    "C#": "C#", "Db": "C#",
    "D": "D",
    "D#": "D#", "Eb": "D#",
    "E": "E", "Fb": "E",
    "F": "F", "E#": "F",
    "F#": "F#", "Gb": "F#",
    "G": "G",
    "G#": "G#", "Ab": "G#",
    "A": "A",
    "A#": "A#", "Bb": "A#",
    "B": "B", "Cb": "B"
}

note_names_sharp = ["C", "C#", "D", "D#", "E", "F",
                    "F#", "G", "G#", "A", "A#", "B"]

# Generate all MIDI note names
# Example: 60 -> "C4", 61 -> "C#4", 62 -> "D4", etc.
note_names = {i: f"{note_names_sharp[i % 12]}{(i // 12)-1}" for i in range(128)}

# --- Helper functions ---
def normalize(note):
    """
    Normalize a note name to its canonical form using enharmonic_map.
    For example, "Db" and "C#" both become "C#".
    Args:
        note (str): The note name (e.g., "C#", "Db", "E").
    Returns:
        str: The normalized note name.
    """
    note_base = ''.join(filter(lambda c: c.isalpha() or c == '#', note))
    return enharmonic_map.get(note_base, note_base)

def check_chord_played(chord_notes, played_notes):
    """
    Check if all notes in the chord are present in the played notes.
    Both chord_notes and played_notes are normalized for enharmonic equivalence.
    Args:
        chord_notes (list of str): The notes required for the chord.
        played_notes (set of str): The notes currently being played.
    Returns:
        bool: True if all chord notes are being played, False otherwise.
    """
    norm_chord = set(normalize(n) for n in chord_notes)
    norm_played = set(normalize(n) for n in played_notes)
    return norm_chord <= norm_played

def midi_to_note(note_number):
    """
    Convert a MIDI note number to a note name with octave.
    Args:
        note_number (int): MIDI note number (0-127).
    Returns:
        str: Note name with octave (e.g., "C4").
    """
    return note_names.get(note_number, "Unknown")

def pick_chord():
    """
    Randomly select a chord from the chords dictionary.
    Returns:
        tuple: (chord name, list of notes)
    """
    return random.choice(list(chords.items()))

# --- MIDI listening thread (non-blocking) ---
def midi_listener():
    """
    Listen for MIDI input events in a separate thread.
    When the correct chord is played, award points based on speed,
    pick a new chord, and reset the timer for the next chord.
    Updates global state variables accordingly.
    """
    global score, played_notes, current_chord, chord_start_time, session_active, device_name, last_points
    inputs = mido.get_input_names()
    if not inputs:
        print("No MIDI device found. Connect one!")
        return
    device_name = inputs[0]
    try:
        with mido.open_input(device_name) as inport:
            while session_active:
                # process any pending messages without blocking
                for msg in inport.iter_pending():
                    if not session_active:
                        break
                    if msg.type == 'note_on' and msg.velocity > 0:
                        note = normalize(midi_to_note(msg.note))
                        played_notes.add(note)
                    if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        note = normalize(midi_to_note(msg.note))
                        played_notes.discard(note)

                    # Check if chord is complete
                    if current_chord and check_chord_played(current_chord[1], played_notes):
                        if chord_start_time is None:
                            chord_elapsed = 0
                        else:
                            chord_elapsed = time.time() - chord_start_time
                        points = max(10 - int(chord_elapsed), 1)
                        score += points
                        last_points = points

                        # pick next chord and reset chord timer (do NOT touch session_start_time)
                        current_chord = pick_chord()
                        chord_start_time = time.time()
                        played_notes.clear()
                # small sleep so we don't busy-spin
                time.sleep(0.01)
    except Exception as e:
        print("MIDI listener error:", e)

# --- Flask routes ---
@app.route("/")
def index():
    """
    Render the main HTML page for the MIDI Chord Trainer.
    """
    return render_template("index.html")

@app.route("/start_session")
def start_session():
    """
    Start a new training session.
    Resets score, timers, and picks the first chord.
    Launches the MIDI listener thread.
    Returns:
        str: Status message.
    """
    global session_active, session_start_time, chord_start_time, score, current_chord, played_notes, last_points
    if session_active:
        return "Session already active", 400

    session_active = True
    score = 0
    last_points = 0
    session_start_time = time.time()
    current_chord = pick_chord()
    chord_start_time = time.time()
    played_notes.clear()

    # start MIDI thread
    t = threading.Thread(target=midi_listener, daemon=True)
    t.start()
    return "Session started"

@app.route("/stop_session", methods=["POST"])
def stop_session():
    """
    Stop the current training session.
    Returns:
        JSON: Status message.
    """
    global session_active
    session_active = False
    return jsonify({"status": "stopped"})

@app.route("/stream")
def stream():
    """
    Stream real-time game state updates to the frontend using Server-Sent Events (SSE).
    Sends current chord, score, time left, and last points.
    Ends the stream when the session is over.
    Returns:
        Response: SSE stream.
    """
    def event_stream():
        global session_active, current_chord, score, session_start_time, device_name, last_points
        while True:
            if not session_active:
                payload = {"status": "end", "score": score}
                yield f"data: {json.dumps(payload)}\n\n"
                break
            elapsed = time.time() - session_start_time
            if elapsed > time_limit:
                session_active = False
                payload = {"status": "end", "score": score}
                yield f"data: {json.dumps(payload)}\n\n"
                break
            if current_chord:
                remaining = max(0, int(time_limit - elapsed))
                data = {"status": "running",
                        "chord_name": current_chord[0],
                        "chord_notes": current_chord[1],
                        "score": score,
                        "time_left": remaining,
                        "device_name": device_name,
                        "last_points": last_points}
                # Do not clear last_points here; it will be overwritten when next chord hit
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(0.2)
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=True)