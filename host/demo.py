# MicroPython sketch for the Tiny Tapeout demo board's RP2040: act as the
# SAP's 16-byte memory and step its clock.
#
# NOTE: the four functions in "board adapter" use the TT MicroPython SDK
# (ttboard). Check the names against the SDK version on your board when the
# chips arrive -- the bus protocol below is what the chip actually needs.

from ttboard.demoboard import DemoBoard

tt = DemoBoard.get()
tt.shuttle.tt_um_khkhiu_sap.enable()
tt.clock_project_stop()          # we step the clock by hand

# board adapter
def read_uo():           return int(tt.uo_out.value)
def read_bus():          return int(tt.uio_out.value)
def drive_bus(value):    tt.uio_oe_pico.value = 0xFF; tt.uio_in.value = value
def release_bus():       tt.uio_oe_pico.value = 0x00

FIBONACCI = [0x50, 0x4E, 0xE0, 0x51, 0x4F, 0xE0, 0x2E, 0x70,
             0x4E, 0xE0, 0x2F, 0x70, 0x4F, 0x65, 0x00, 0x00]


def run(program, max_cycles=10_000):
    mem = list(program)
    tt.reset_project(True)
    tt.clock_project_once()
    tt.reset_project(False)
    strobe_last = False
    for _ in range(max_cycles):
        uo = read_uo()
        addr, we, out, halted = uo & 0xF, (uo >> 4) & 1, (uo >> 5) & 1, (uo >> 7) & 1
        if halted:
            break
        if we or out:
            release_bus()
            if strobe_last:              # second strobe cycle: chip is driving
                data = read_bus()
                if we:
                    mem[addr] = data
                if out:
                    print(data)
            strobe_last = True
        else:
            drive_bus(mem[addr])
            strobe_last = False
        tt.clock_project_once()
    release_bus()
    return mem


run(FIBONACCI, max_cycles=400)
