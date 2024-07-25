from cpu import CPU

def main():
    # set graphics
    # set input

    chip8_cpu = CPU()
    # chip8_cpu.load_game("tests/1-chip8-logo.ch8")
    chip8_cpu.load_game("tests/3-corax+.ch8")
    while True:
        chip8_cpu.cycle()

        if chip8_cpu.drawFlag:
            on_pixel = '█'
            off_pixel = ' '
            for y in range(32):
                line = ''
                for x in range(64):
                    line += on_pixel if chip8_cpu.gfx[y * 64 + x] else off_pixel
                print(line)

        # set keys

if __name__ == "__main__":
    main()