import random
import logging

logging.basicConfig(filename="output.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

logging.info("Running CPU")

logger = logging.getLogger('Chip8CPU')

FONTSET = [
        0xF0, 0x90, 0x90, 0x90, 0xF0, # 0
        0x20, 0x60, 0x20, 0x20, 0x70, # 1
        0xF0, 0x10, 0xF0, 0x80, 0xF0, # 2
        0xF0, 0x10, 0xF0, 0x10, 0xF0, # 3
        0x90, 0x90, 0xF0, 0x10, 0x10, # 4
        0xF0, 0x80, 0xF0, 0x10, 0xF0, # 5
        0xF0, 0x80, 0xF0, 0x90, 0xF0, # 6
        0xF0, 0x10, 0x20, 0x40, 0x40, # 7
        0xF0, 0x90, 0xF0, 0x90, 0xF0, # 8
        0xF0, 0x90, 0xF0, 0x10, 0xF0, # 9
        0xF0, 0x90, 0xF0, 0x90, 0x90, # A
        0xE0, 0x90, 0xE0, 0x90, 0xE0, # B
        0xF0, 0x80, 0x80, 0x80, 0xF0, # C
        0xE0, 0x90, 0x90, 0x90, 0xE0, # D
        0xF0, 0x80, 0xF0, 0x80, 0xF0, # E
        0xF0, 0x80, 0xF0, 0x80, 0x80  # F
    ]

class CPU:
    def __init__(self):
        self.opcode = 0
        self.memory = bytearray(4096)
        self.registers = bytearray(16)
        self.I = 0
        self.pc = 0x200
        self.gfx = bytearray(64 * 32)
        self.delay_timer = 0
        self.sound_timer = 0
        self.stack = [0] * 16
        self.sp = 0
        self.key = [0] * 16
        self.drawFlag = False

        for i in range(len(FONTSET)):
            self.memory[i] = FONTSET[i]

        self.operations_table = {
            0x0: self.execute_zero,
            0x1: self.jump_to_addr,
            0x2: self.call_addr,
            0x3: self.skip_next_instruction_if_registers_and_val_equal,
            0x4: self.skip_next_instruction_if_registers_and_val_not_equal,
            0x5: self.skip_next_instruction_if_registers_equal,
            0x6: self.set_register_value,
            0x7: self.add_register_value,
            0x8: self.execute_logic_operations,
            0x9: self.skip_if_registers_neq,
            0xA: self.load_index_reg_with_value,
            0xB: self.jump_to_addr_plus_v0,
            0xC: self.set_random_register_and_kk,
            0xD: self.draw_sprite,
            0xE: self.not_implemented,
            0xF: self.execute_misc,
        }

        self.logic_operations_table = {
            0x0: self.set_register_to_register,
            0x1: self.or_registers,
            0x2: self.and_registers,
            0x3: self.xor_registers,
            0x4: self.add_registers,
            0x5: self.sub_registers,
            0x6: self.shift_right,
            0x7: self.subn_registers,
            0xE: self.shift_left
        }

        self.misc_table = {
            0x07: self.set_vx_to_delay_timer,
            0x0A: self.wait_for_keypress,
            0x15: self.set_delay_timer_to_register,
            0x18: self.set_sound_timer_to_register,
            0x1E: self.add_register_to_index,
            0x29: self.set_i_to_sprite_address,
            0x33: self.set_bcd_of_register,
            0x55: self.store_registers,
            0x65: self.load_registers
        }

    def load_game(self, game_title: str):
        with open(game_title, "rb") as f:
            rom = f.read()
            for index, data in enumerate(rom):
                self.memory[self.pc + index] = data
                            
    def cycle(self):
        # we can collapse this line into execute instruction itself, probably.
        self.opcode = (self.memory[self.pc] << 8) | (self.memory[self.pc + 1])
        

        # switches are too inefficient in python
        # we instead create a hashmap
        # here we define a function to, look up the hashmap?
        
        self.execute_instruction()

        if self.delay_timer > 0:
            self.delay_timer -= 1
        
        if self.sound_timer > 0:
            if self.sound_timer == 1:
                print("BEEP")
            self.sound_timer -= 1


    def execute_instruction(self):
        operation = (self.opcode & 0xF000) >> 12
        logger.info("OPCODE LOGGED: " + hex(self.opcode))
        self.pc += 2
        if operation in self.operations_table:
            self.operations_table[operation]()
            logger.info("Running opcode: " + hex(self.opcode))
        else:
            logger.info(f"Operation {operation} does not exist.")
    
    def execute_zero(self):
        """
        Handles 00E0 and 00EE
        """
        operation = self.opcode & 0x00FF
        if operation == 0xE0:
            self.clear_display()
        elif operation == 0xEE:
            self.return_from_subroutine()

    def execute_misc(self):
        operation = self.opcode & 0x00FF
        if operation in self.misc_table:
            self.misc_table[operation]()
        else:
            self.not_implemented()
        

    def clear_display(self):
        """
        00E0 - CLS
        Clear the display.
        """
        self.gfx = bytearray(64 * 32)
        self.drawFlag = True


    def return_from_subroutine(self):
        """
        00EE - RET
        Return from a subroutine.

        The interpreter sets the program counter to the address at the top of the stack, then subtracts 1 from the stack pointer.
        """
        self.pc = self.stack[self.sp]
        self.sp -= 1

    def jump_to_addr(self):
        self.pc = self.opcode & 0x0FFF
    
    def call_addr(self):
        """
        Call subroutine at nnn.

        The interpreter increments the stack pointer, then puts the current PC on the top of the stack. The PC is then set to nnn.
        """
        self.sp += 1
        self.stack[self.sp] = self.pc
        self.pc = self.opcode & 0x0FFF

    def skip_next_instruction_if_registers_and_val_equal(self):
        """
        Skip next instruction if Vx = kk.

        The interpreter compares register Vx to kk, and if they are equal, increments the program counter by 2.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        kk = self.opcode & 0x00FF
        if self.registers[Vx] == kk:
            self.pc += 2

    def skip_next_instruction_if_registers_and_val_not_equal(self):
        """
        Skip next instruction if Vx != kk.

        The interpreter compares register Vx to kk, and if they are not equal, increments the program counter by 2.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        kk = self.opcode & 0x00FF
        if self.registers[Vx] != kk:
            self.pc += 2

    def skip_next_instruction_if_registers_equal(self):
        """
        Skip next instruction if Vx == Vy.

        The interpreter compares register Vx to Vy, and if they are equal, increments the program counter by 2.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        if self.registers[Vx] == self.registers[Vy]:
            self.pc += 2
        
    def set_register_value(self):
        Vx = (self.opcode & 0x0F00) >> 8
        kk = self.opcode & 0x00FF
        self.registers[Vx] = kk

    def add_register_value(self):
        Vx = (self.opcode & 0x0F00) >> 8
        kk = self.opcode & 0x00FF
        self.registers[Vx] = (self.registers[Vx] + kk) & 0xFF

    def execute_logic_operations(self):
        operation = self.opcode & 0x000F
        if operation in self.logic_operations_table:
            self.logic_operations_table[operation]()
        else:
            self.not_implemented()
    
    def set_register_to_register(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        self.registers[Vx] = self.registers[Vy]

    def or_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        self.registers[Vx] |= self.registers[Vy]
    
    def and_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        self.registers[Vx] &= self.registers[Vy]
    
    def xor_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        self.registers[Vx] ^= self.registers[Vy]
    
    def add_registers(self):
        """
        Set Vx = Vx + Vy, set VF = carry.

        The values of Vx and Vy are added to    her. If the result is greater than 8 bits (i.e., > 255,) VF is set to 1, otherwise 0. Only the lowest 8 bits of the result are kept, and stored in Vx.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        if (self.registers[Vx] + self.registers[Vy]) > 255:
            self.registers[0xF] = 1
        else:
            self.registers[0xF] = 0
        self.registers[Vx] = (self.registers[Vx] + self.registers[Vy]) & 0xFF

    def sub_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        if self.registers[Vx] > self.registers[Vy]:
            self.registers[0xF] = 1
        else:
            self.registers[0xF] = 0
        self.registers[Vx] = (self.registers[Vx] - self.registers[Vy]) & 0xFF

    def shift_right(self):  
        Vx = (self.opcode & 0x0F00) >> 8
        self.registers[0xF] = self.registers[Vx] & 0x1
        self.registers[Vx] = (self.registers[Vx] >> 1) & 0xFF
    

    def subn_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        if self.registers[Vx] < self.registers[Vy]:
            self.registers[0xF] = 0
        else:
            self.registers[0xF] = 1
        self.registers[Vx] = (self.registers[Vx] - self.registers[Vy]) & 0xFF

    def shift_left(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.registers[0xF] = (self.registers[Vx] & 0x80) >> 7
        self.registers[Vx] = (self.registers[Vx] << 1) & 0xFF

    def skip_if_registers_neq(self):
        """
        Skip next instruction if Vx != Vy.

        The interpreter compares register Vx to Vy, and if they are not qual, increments the program counter by 2.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        if self.registers[Vx] != self.registers[Vy]:
            self.pc += 2


    def load_index_reg_with_value(self):
        """
        Set I = nnn.

        The value of register I is set to nnn.
        """
        self.I = self.opcode & 0x0FFF
    
    def jump_to_addr_plus_v0(self):
        """
        Jump to location nnn + V0.

        The program counter is set to nnn plus the value of V0.
        """
        nnn = self.opcode & 0x0FFF
        self.pc = self.registers[0] + nnn
        
    def set_random_register_and_kk(self):
        """
        Set Vx = random byte AND kk.

        The interpreter generates a random number from 0 to 255, which is then ANDed with the value kk. The results are stored in Vx.
        """
        Vx = (self.opcode & 0x0F00) >> 8
        kk = self.opcode & 0x00FF
        result = random.randint(0, 255) & kk
        self.registers[Vx] = result & 0xFF

    def draw_sprite(self):
        """
        Display n-byte sprite starting at memory location I at (Vx, Vy), set VF = collision.

        The interpreter reads n bytes from memory, starting at the address stored in I. These bytes are then displayed as sprites on screen at coordinates (Vx, Vy). Sprites are XORed onto the existing screen. If this causes any pixels to be erased, VF is set to 1, otherwise it is set to 0. If the sprite is positioned so part of it is outside the coordinates of the display, it wraps around to the opposite side of the screen. See instruction 8xy3 for more information on XOR, and section 2.4, Display, for more information on the Chip-8 screen and sprites.        
        """
        Vx = (self.opcode & 0x0F00) >> 8
        Vy = (self.opcode & 0x00F0) >> 4
        n = self.opcode & 0x000F
        self.registers[0xF] = 0
        for yline in range(n):
            sprite = self.memory[self.I + yline]
            for xline in range(8):
                if sprite & (0x80 >> xline):
                    if self.gfx[(self.registers[Vy] + yline) * 64 + (self.registers[Vx]+ xline)] == 1:
                        self.registers[0xF] = 1
                    self.gfx[(self.registers[Vy] + yline) * 64 + (self.registers[Vx] + xline)] ^= 1
        self.drawFlag = True

    def set_vx_to_delay_timer(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.registers[Vx] = self.delay_timer

    def wait_for_keypress(self):
        self.not_implemented()

    def set_delay_timer_to_register(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.delay_timer = self.registers[Vx]

    def set_sound_timer_to_register(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.sound_timer = self.registers[Vx]

    def add_register_to_index(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.I += self.registers[Vx]
    
    def set_i_to_sprite_address(self):
        Vx = (self.opcode & 0x0F00) >> 8
        self.I = self.registers[Vx] * 5

    def set_bcd_of_register(self):
        Vx = (self.opcode & 0x0F00) >> 8
        value = self.registers[Vx]
        self.memory[self.I] = value // 100
        self.memory[self.I + 1] = (value // 10) % 10
        self.memory[self.I + 2] = value % 10

    def store_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        for i in range(Vx + 1):
            self.memory[self.I + i] = self.registers[i]

    def load_registers(self):
        Vx = (self.opcode & 0x0F00) >> 8
        for i in range(Vx + 1):
            self.registers[i] = self.memory[self.I + i]

    def not_implemented(self):
        logger.error("Running UNIMPLEMENTED opcode: " + hex(self.opcode))