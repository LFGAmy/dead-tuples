from badgeware import *

# DEAD TUPLES, a Supabase Select badge game
# Every UPDATE in Postgres heap leaves a dead row behind.
# VACUUM them before the table fills and you hit wraparound.
#   A = vacuum the column under the cursor (3+ at once = CLEAN bonus)
#   C = OrioleDB, charged by vacuuming: updates in place, no dead rows
#   B = restart

badge.mode(LORES | VSYNC)
display.backlight(0.9)

COLS = 16
ROWS = 6
N = COLS * ROWS
GX = 8
GY = 20
P = 9
S = 7
CHARGE = 20
STEP_MS = 70        # cursor speed
START_MS = 300      # time between UPDATEs at the start
MIN_MS = 90         # fastest it gets
ORIOLE_MS = 5000

BG = color.rgb(18, 28, 24)
GREEN = color.rgb(62, 207, 142)
DEAD = color.rgb(150, 66, 66)
SPARK = color.rgb(255, 150, 150)
EMPTY = color.rgb(34, 46, 40)
LANE = color.rgb(52, 74, 62)
AMBER = color.rgb(255, 180, 80)
RED = color.rgb(240, 90, 90)
DIM = color.rgb(150, 170, 160)

seed = 7
best = 0
mode = 0  # 0 title, 1 play, 2 game over
now = 0
last = 0
strip = [0] * COLS
strip_next = 0


def rnd(n):
    global seed
    seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
    return seed % n


def reset():
    global grid, cur, xid, vac, meter, oriole_end, interval
    global next_upd, next_step, flash_end, parts, pop, pop_end, over_at
    grid = [0] * N
    for _ in range(40):
        grid[rnd(N)] = 1
    cur = 0
    xid = 0
    vac = 0
    meter = 0
    oriole_end = 0
    interval = START_MS
    next_upd = now + interval
    next_step = now + STEP_MS
    flash_end = 0
    parts = []
    pop = ""
    pop_end = 0
    over_at = 0


def oriole_on():
    return now < oriole_end


def burst(c, r, n):
    x = GX + c * P + 3
    y = GY + r * P + 3
    for _ in range(n):
        parts.append([x, y, (rnd(9) - 4) * 0.02, -(rnd(5) + 2) * 0.02, 450])


def step_parts(dt):
    global parts
    for p in parts:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[3] += 0.0003 * dt
        p[4] -= dt
    parts = [p for p in parts if p[4] > 0]


def update_row():
    global xid, mode, best, over_at
    xid += 1
    if oriole_on():
        return  # OrioleDB updates in place: nothing left behind
    lives = [i for i in range(N) if grid[i] == 1]
    empties = [i for i in range(N) if grid[i] == 0]
    if not empties:
        mode = 2
        over_at = now
        if vac > best:
            best = vac
        return
    if lives:
        grid[lives[rnd(len(lives))]] = 2
    grid[empties[rnd(len(empties))]] = 1


def title():
    global strip_next
    if now >= strip_next:
        strip_next = now + 180
        i = rnd(COLS)
        strip[i] = (strip[i] + 1) % 3
    screen.pen = BG
    screen.clear()
    screen.pen = GREEN
    screen.text("DEAD TUPLES", 8, 6, 2)
    screen.pen = color.white
    screen.text("every UPDATE leaves", 8, 32)
    screen.text("a dead row behind.", 8, 44)
    screen.text("VACUUM them before", 8, 60)
    screen.text("the table fills up.", 8, 72)
    for c in range(COLS):
        v = strip[c]
        screen.pen = GREEN if v == 1 else (DEAD if v == 2 else EMPTY)
        screen.rectangle(GX + c * P, 86, S, S)
    if (now // 400) % 2 == 0:
        screen.pen = AMBER
        screen.text("press A to start", 8, 99)
    if best > 0:
        screen.pen = DIM
        screen.text("best " + str(best), 112, 99)
    screen.pen = DIM
    screen.text("A vacuum  C oriole  B reset", 8, 110)


def game_over():
    ox = (rnd(5) - 2) if now - over_at < 450 else 0
    screen.pen = BG
    screen.clear()
    screen.pen = RED
    screen.text("WRAPAROUND", 8 + ox, 6, 2)
    screen.pen = color.white
    screen.text("database is read-only", 8 + ox, 30)
    screen.pen = GREEN
    screen.text("vacuumed " + str(vac), 8, 48)
    screen.text("survived " + str(xid) + " XIDs", 8, 60)
    screen.pen = DIM
    screen.text("best " + str(best), 8, 72)
    screen.pen = AMBER
    screen.text("should've used OrioleDB", 8, 90)
    if (now // 400) % 2 == 0:
        screen.pen = DIM
        screen.text("A to play again", 8, 106)


def play(dt):
    global cur, vac, meter, oriole_end, interval, next_upd, next_step
    global flash_end, pop, pop_end

    if now >= next_step:
        cur = (cur + 1) % COLS
        next_step = now + STEP_MS

    if badge.pressed(BUTTON_A):
        flash_end = now + 100
        cleared = 0
        for r in range(ROWS):
            i = r * COLS + cur
            if grid[i] == 2:
                grid[i] = 0
                cleared += 1
                burst(cur, r, 3)
        vac += cleared
        if not oriole_on():
            meter = min(CHARGE, meter + cleared + (2 if cleared >= 3 else 0))
        if cleared >= 3:
            pop = "+" + str(cleared) + " CLEAN!"
            pop_end = now + 700
        elif cleared > 0:
            pop = "+" + str(cleared)
            pop_end = now + 500

    if badge.pressed(BUTTON_C) and meter >= CHARGE and not oriole_on():
        oriole_end = now + ORIOLE_MS
        meter = 0
        flash_end = now + 150
        for i in range(N):
            if grid[i] == 2:
                grid[i] = 0
                vac += 1
                burst(i % COLS, i // COLS, 1)
        pop = "64-BIT XIDs"
        pop_end = now + 1200

    if now >= next_upd:
        update_row()
        if xid % 12 == 0 and interval > MIN_MS:
            interval -= 15
        next_upd = now + interval

    step_parts(dt)

    # draw
    oo = oriole_on()
    screen.pen = BG
    screen.clear()

    if oo:
        screen.pen = AMBER
        screen.text("ORIOLEDB ON", 8, 6)
    else:
        screen.pen = GREEN
        screen.text("DEAD TUPLES", 8, 6)
    if now < pop_end:
        screen.pen = AMBER if oo or "CLEAN" in pop else color.white
        screen.text(pop, 88, 6)

    screen.pen = color.white if now < flash_end else LANE
    screen.rectangle(GX + cur * P - 1, GY - 1, S + 2, ROWS * P + 1)

    live = AMBER if oo else GREEN
    for r in range(ROWS):
        for c in range(COLS):
            v = grid[r * COLS + c]
            if v == 1:
                screen.pen = live
            elif v == 2:
                screen.pen = DEAD
            else:
                screen.pen = EMPTY
            screen.rectangle(GX + c * P, GY + r * P, S, S)

    screen.pen = SPARK
    for p in parts:
        screen.rectangle(int(p[0]), int(p[1]), 2, 2)

    screen.pen = color.white
    screen.text("VAC " + str(vac), 8, 80)
    screen.pen = DIM
    screen.text("XID " + str(xid), 88, 80)

    screen.pen = EMPTY
    screen.rectangle(8, 94, 144, 6)
    if oo:
        screen.pen = AMBER
        screen.rectangle(8, 94, int(144 * (oriole_end - now) / ORIOLE_MS), 6)
        screen.pen = DIM
        screen.text("no vacuum needed", 8, 106)
    elif meter >= CHARGE:
        if (now // 200) % 2 == 0:
            screen.pen = AMBER
            screen.rectangle(8, 94, 144, 6)
        screen.pen = AMBER
        screen.text("press C for OrioleDB", 8, 106)
    else:
        screen.pen = AMBER
        screen.rectangle(8, 94, int(144 * meter / CHARGE), 6)
        screen.pen = DIM
        screen.text("vacuum to charge OrioleDB", 8, 106)


def update():
    global mode, now, last, seed
    now = badge.ticks
    dt = now - last if last else 16
    if dt > 50:
        dt = 50
    last = now
    seed += now & 0xFF

    if mode == 0:
        if badge.pressed(BUTTON_A):
            reset()
            mode = 1
        title()
    elif mode == 1:
        if badge.pressed(BUTTON_B):
            reset()
        play(dt)
    else:
        if now - over_at > 600 and (badge.pressed(BUTTON_A) or badge.pressed(BUTTON_B)):
            reset()
            mode = 1
        game_over()


reset()
print("DEAD TUPLES: A vacuum, C OrioleDB, B restart.")
run(update)
