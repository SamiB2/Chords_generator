import random        # for picking random chords
import time          # for delays
import mido          # for MIDI input

# --- 1. Define all chords ---
chords = {
    "C major": ["C", "E", "G"],
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
    "Ab minor": ["Ab", "Cb(B)", "Eb"],
    "A minor": ["A", "C", "E"],
    "Bb minor": ["Bb", "Db", "F"],
    "B minor": ["B", "D", "F#"],
    "C diminished": ["C", "Eb", "Gb"],
    "C# diminished": ["C#", "E", "G"],
    "D diminished": ["D", "F", "Ab"],
    "Eb diminished": ["Eb", "Gb", "Bbb(A)"],
    "E diminished": ["E", "G", "Bb"],
    "F diminished": ["F", "Ab", "Cb(B)"],
    "F# diminished": ["F#", "A", "C"],
    "G diminished": ["G", "Bb", "Db"],
    "Ab diminished": ["Ab", "Cb", "Ebb(D)"],
    "A diminished": ["A", "C", "Eb"],
    "Bb diminished": ["Bb", "Db", "Fb(E)"],
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


# List of all 12 note names in an octave
note_names_sharp = ["C", "C#", "D", "D#", "E", "F",
                    "F#", "G", "G#", "A", "A#", "B"]

# --- 0. Generate a dictionary for all MIDI notes (0-127) ---
note_names = {}
for midi_num in range(128):
    octave = (midi_num // 12) - 1       # MIDI octave calculation
    note = note_names_sharp[midi_num % 12]
    note_names[midi_num] = f"{note}{octave}"

# --- Normalize all the notes ---
def normalize(note):
    """Convert note to a standard enharmonic equivalent"""
    # Remove octave number if present (e.g., C4 → C)
    note_base = ''.join(filter(str.isalpha, note)) + ('#' if '#' in note else '')
    return enharmonic_map.get(note_base, note_base)

# ---Check chord played using normalized notes ---
def check_chord_played(chord_notes, played_notes):
    norm_chord = set(normalize(n) for n in chord_notes)
    norm_played = set(normalize(n) for n in played_notes)
    return norm_chord <= norm_played  # all chord notes must be in played notes

# --- 2. Map MIDI note numbers to note names ---
def midi_to_note(note_number):
    """Convert MIDI note number to note name, wrapping across octaves."""
    # MIDI notes repeat every 12, so we use modulo 12 plus offset for middle C
    return note_names.get(60 + (note_number % 12), "Unknown")

# --- 4. Main loop ---
def play_chords_with_midi(chords):
    # 4a. List available MIDI devices
    inputs = mido.get_input_names()
    if not inputs:
        print("No MIDI input devices found. Please connect a keyboard.")
        return
    print(f"Using MIDI input: {inputs[0]}")

    with mido.open_input(inputs[0]) as inport:
        try:
            while True:
                # 4b. Pick a random chord
                chord_name, chord_notes = random.choice(list(chords.items()))
                print(f"\nPlay this chord: {chord_name} – {', '.join(chord_notes)}")

                played_notes = set()
                
                # 4c. Wait until all chord notes are pressed
                while True:
                    msg = inport.receive()  # blocking call, waits for MIDI input

                    # Note pressed
                    if msg.type == 'note_on' and msg.velocity > 0:
                        note = midi_to_note(msg.note)       # e.g., "E4"
                        note = normalize(note)              # remove octave & map enharmonics
                        played_notes.add(note)
                        print(f"Pressed: {note}")

                    # Note released
                    if msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        note = midi_to_note(msg.note)
                        note = normalize(note)
                        played_notes.discard(note)

                    # Check if all chord notes are in played_notes (ignore extras)
                    if check_chord_played(chord_notes, played_notes):
                        print("✅ Correct! Moving to next chord...")
                        
                        for i in range(3, 0, -1):  # 3, 2, 1
                            print(f"Next chord in {i}...")
                            time.sleep(1)
                        break  # exit inner loop to pick next chord

        except KeyboardInterrupt:
            print("\nStopped chord generator.")

# --- 5. Run the program ---
play_chords_with_midi(chords)
# This code listens for MIDI input and checks if the played notes match a randomly selected chord.