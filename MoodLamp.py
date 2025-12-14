from microbit import *
import neopixel
import music

# ============================================================
# Config / constants
# ============================================================
display.off()  # free up pins by turning off LED matrix

NEOPIXEL_PIN = pin2
NEOPIXEL_LEN = 8

ROWS = [pin3, pin4, pin5, pin6]       # keypad rows (inputs)
COLS = [pin7, pin8, pin9, pin10]      # keypad cols (outputs)

KEYMAP = [
    ['D', 'C', 'B', 'A'],
    ['#', '9', '6', '3'],
    ['0', '8', '5', '2'],
    ['*', '7', '4', '1']
]

TEMP_BLUE_LEVELS = (0, 20, 40)
COMBO_WINDOW_MS = 200      # A then B within this = RGB entry mode

BEEP_HZ = 868
BEEP_MS = 100

# Brightness steps (index 0..3). C = dimmer, D = brighter.
BRIGHTNESS_PCT = (25, 45, 70, 100)

# ============================================================
# Hardware setup
# ============================================================
np = neopixel.NeoPixel(NEOPIXEL_PIN, NEOPIXEL_LEN)

for r in ROWS:
    r.set_pull(r.PULL_UP)  # idle = 1 (HIGH)

for c in COLS:
    c.write_digital(1)     # idle = HIGH

# ============================================================
# Helpers
# ============================================================
def beep():
    music.pitch(BEEP_HZ, BEEP_MS)

def clamp8(x):
    if x < 0:
        return 0
    if x > 255:
        return 255
    return x

def scale_color(rgb, pct):
    """Scale (r,g,b) by pct (0..100) using integer math."""
    r, g, bch = rgb
    return (
        clamp8((r * pct) // 100),
        clamp8((g * pct) // 100),
        clamp8((bch * pct) // 100)
    )

def set_all(rgb):
    for i in range(len(np)):
        np[i] = rgb
    np.show()

def get_key():
    """Scan keypad once; return key char or None (debounced release)."""
    for c_idx, c_pin in enumerate(COLS):
        # all columns HIGH
        for cp in COLS:
            cp.write_digital(1)

        # current column LOW
        c_pin.write_digital(0)
        sleep(3)  # small settle time

        # read rows
        for r_idx, r_pin in enumerate(ROWS):
            if r_pin.read_digital() == 0:
                key = KEYMAP[r_idx][c_idx]

                # debounce: wait for release
                while r_pin.read_digital() == 0:
                    sleep(10)

                c_pin.write_digital(1)
                return key

        c_pin.write_digital(1)

    return None

# ============================================================
# App state
# ============================================================
is_on = True
temp_idx = 0
brightness_idx = 3               # start at 100%

base_color = (156, 68, 0)        # chosen color (before brightness)

rgb_mode = False
current_digits = ""
rgb_segments = []                # will store 3 ints: [R, G, B]

# ============================================================
# App logic
# ============================================================
def apply_output():
    """Write current state to LEDs."""
    if not is_on:
        set_all((0, 0, 0))
        return

    pct = BRIGHTNESS_PCT[brightness_idx]
    set_all(scale_color(base_color, pct))

def toggle_power():
    global is_on
    beep()
    is_on = not is_on
    apply_output()

def set_temp_color():
    global base_color
    base_color = (156, 68, TEMP_BLUE_LEVELS[temp_idx])
    apply_output()

def brightness_brighter():
    global brightness_idx
    beep()
    if brightness_idx < len(BRIGHTNESS_PCT) - 1:
        brightness_idx += 1
    apply_output()

def brightness_dimmer():
    global brightness_idx
    beep()
    if brightness_idx > 0:
        brightness_idx -= 1
    apply_output()

def enter_rgb_mode():
    global rgb_mode, current_digits, rgb_segments
    beep()
    rgb_mode = True
    current_digits = ""
    rgb_segments = []
    print("RGB Entry mode")

def exit_rgb_mode():
    global rgb_mode, current_digits, rgb_segments
    rgb_mode = False
    current_digits = ""
    rgb_segments = []

def handle_normal_mode(key):
    global temp_idx

    if key == 'A':
        # Detect A then B within COMBO_WINDOW_MS
        start = running_time()
        while running_time() - start < COMBO_WINDOW_MS:
            k2 = get_key()
            if k2 == 'B':
                enter_rgb_mode()
                return
            sleep(10)
        toggle_power()

    elif key == 'B':
        beep()
        temp_idx = (temp_idx + 1) % len(TEMP_BLUE_LEVELS)
        set_temp_color()

    elif key == 'C':
        # D = brighter
        brightness_brighter()

    elif key == 'D':
        # C = dimmer
        brightness_dimmer()

def handle_rgb_mode(key):
    global current_digits, rgb_segments, base_color

    if key in '0123456789':
        # limit to 3 digits so it stays sane (0..255)
        if len(current_digits) < 3:
            beep()
            current_digits += key
            print("Current:", current_digits)
        return

    if key == '*':
        beep()
        current_digits = ""
        rgb_segments = []
        print("Cleared")
        return

    if key == '#':
        beep()
        if current_digits == "":
            return

        value = int(current_digits)
        current_digits = ""

        if value > 255:
            print("Value too big:", value)
            return

        rgb_segments.append(value)
        print("Segment", len(rgb_segments), "=", value)

        if len(rgb_segments) == 3:
            r, g, bch = rgb_segments
            base_color = (r, g, bch)
            apply_output()
            print("Final RGB:", r, g, bch)
            exit_rgb_mode()

# Show initial color
apply_output()

# ============================================================
# Main loop
# ============================================================
while True:
    k = get_key()
    if k is not None:
        if rgb_mode:
            handle_rgb_mode(k)
        else:
            handle_normal_mode(k)

        # extra small delay makes it feel smoother / avoids accidental repeats
        sleep(30)

    sleep(20)
