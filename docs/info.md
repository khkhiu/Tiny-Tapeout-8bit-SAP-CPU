<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

An 8-bit accumulator CPU in the style of the SAP-1 ("Simple As Possible") computer, made popular by Ben Eater's breadboard computer. The CPU is on the chip. The 16 bytes of memory are on the demo board, where the RP2040 plays the memory.

Registers use an 8-bit accumulator `A`, a 4-bit program counter, an 8-bit instruction register, and carry (`C`) and zero (`Z`) flags. Each instruction is one byte, a 4-bit opcode followed by a 4-bit operand (an address or an immediate value).

| Opcode | Mnemonic | Operation | Cycles |
|---|---|---|---|
| `0x0-` | `NOP` | – | 2 |
| `0x1a` | `LDA a` | A ← mem[a] | 2 |
| `0x2a` | `ADD a` | A ← A + mem[a]; sets C, Z | 2 |
| `0x3a` | `SUB a` | A ← A − mem[a]; sets C (1 = no borrow), Z | 2 |
| `0x4a` | `STA a` | mem[a] ← A | 3 |
| `0x5n` | `LDI n` | A ← n | 2 |
| `0x6a` | `JMP a` | PC ← a | 2 |
| `0x7a` | `JC a` | if C: PC ← a | 2 |
| `0x8a` | `JZ a` | if Z: PC ← a | 2 |
| `0xD-` | `IN` | A ← ui_in | 2 |
| `0xE-` | `OUT` | put A on the bus with the out strobe | 3 |
| `0xF-` | `HLT` | stop until reset | 2 |

### Memory bus

- `uo[3:0]` is the address: the PC during a fetch, the operand otherwise. `uo[6]` is high during a fetch.
- When `uo[4]` (STA) and `uo[5]` (OUT) are both low, the memory must drive `uio[7:0]` with `mem[addr]`.
- When either strobe goes high, the memory must release `uio`. On the following cycle the chip drives `A` onto `uio` (`uio_oe = 0xFF`). The memory stores it (STA) or treats it as output (OUT). Because of that one-cycle gap, the chip and the memory never drive the bus at the same time.
- `uo[7]` goes high when the CPU executes `HLT`.

## How to test

Use the RP2040 on the demo board as the memory and the clock. Load a 16-byte program into a Python list, then step the project clock in a loop:

1. Read `uo_out`. Take `addr = uo & 0xF`, `we = uo>>4 & 1`, `out = uo>>5 & 1`.
2. If `we` and `out` are both 0, drive `uio` with `mem[addr]`. Otherwise stop driving `uio`.
3. If the chip is driving `uio` (the cycle after a strobe rises): on `we`, store `uio` into `mem[addr]`; on `out`, print it.
4. Pulse the clock once. Stop when `uo[7]` (halted) is high.

Fibonacci program (prints 0 1 1 2 3 5 … 233, then starts again):

```
50 4E E0 51 4F E0 2E 70 4E E0 2F 70 4F 65 00 00
```

Set the DIP switches and run `IN` / `OUT` to read them.

## External hardware

None beyond the demo board. The RP2040 provides the memory and the clock.
