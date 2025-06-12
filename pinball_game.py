#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彈珠台遊戲系統
適用於 Raspberry Pi 4
作者: Claude AI Assistant
"""

import pygame
import RPi.GPIO as GPIO
import time
import random
import threading
from collections import defaultdict
import os

# TM1637 7段顯示器控制類
class TM1637:
    # Segment patterns for digits 0-9 and blank (for 7-segment display)
    # These define which segments (a-g) need to be lit for each number.
    #   A
    # F   B
    #   G
    # E   C
    #   D
    # The hex values correspond to the bitmask: DP, G, F, E, D, C, B, A
    SEGMENTS = {
        0: 0x3f,  # 0b00111111 (ABCDEF)
        1: 0x06,  # 0b00000110 (BC)
        2: 0x5b,  # 0b01011011 (ABGED)
        3: 0x4f,  # 0b01001111 (ABCDG)
        4: 0x66,  # 0b01100110 (FBCG)
        5: 0x6d,  # 0b01101101 (AFGCD)
        6: 0x7d,  # 0b01111101 (AFGCDE)
        7: 0x07,  # 0b00000111 (ABC)
        8: 0x7f,  # 0b01111111 (ABCDEFG)
        9: 0x6f,  # 0b01101111 (ABCFG)
        ' ': 0x00 # 0b00000000 (Blank)
    }

    def __init__(self, clk_pin, dio_pin):
        self.clk_pin = clk_pin
        self.dio_pin = dio_pin
        # Set GPIO pins as output
        GPIO.setup(self.clk_pin, GPIO.OUT)
        GPIO.setup(self.dio_pin, GPIO.OUT)
        # Initialize display to off
        self.display_number(0)

    def _start(self):
        # Start condition for TM1637 communication
        GPIO.output(self.dio_pin, GPIO.HIGH)
        GPIO.output(self.clk_pin, GPIO.HIGH)
        time.sleep(0.000001) # Small delay for clock and data setup
        GPIO.output(self.dio_pin, GPIO.LOW)
        time.sleep(0.000001) # Small delay after data goes low

    def _stop(self):
        # Stop condition for TM1637 communication
        GPIO.output(self.clk_pin, GPIO.LOW)
        time.sleep(0.000001) # Small delay after clock goes low
        GPIO.output(self.dio_pin, GPIO.LOW)
        time.sleep(0.000001) # Small delay after data goes low
        GPIO.output(self.clk_pin, GPIO.HIGH)
        time.sleep(0.000001) # Small delay after clock goes high
        GPIO.output(self.dio_pin, GPIO.HIGH)
        time.sleep(0.000001) # Small delay after data goes high

    def _write_byte(self, data):
        # Write a byte of data to the TM1637, bit by bit (LSB first)
        for i in range(8):
            GPIO.output(self.clk_pin, GPIO.LOW) # Clock low to prepare for data change
            time.sleep(0.000001) # Small delay
            
            # Set DIO based on the current bit (LSB first)
            GPIO.output(self.dio_pin, (data >> i) & 0x01) 
            time.sleep(0.000001) # Small delay for data to stabilize

            GPIO.output(self.clk_pin, GPIO.HIGH) # Clock high to latch the data
            time.sleep(0.000001) # Small delay

        # Acknowledge pulse from TM1637 (master releases DIO, slave pulls it low)
        GPIO.output(self.clk_pin, GPIO.LOW) # Clock low
        time.sleep(0.000001)
        GPIO.setup(self.dio_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Switch DIO to input mode to read ACK
        time.sleep(0.000001)
        # ack = GPIO.input(self.dio_pin) # Optional: read the ACK signal
        GPIO.output(self.clk_pin, GPIO.HIGH) # Clock high to signal ACK
        time.sleep(0.000001) # Wait for ACK pulse
        GPIO.output(self.clk_pin, GPIO.LOW) # Clock low to end ACK pulse
        time.sleep(0.000001)
        GPIO.setup(self.dio_pin, GPIO.OUT) # Switch DIO back to output mode
        GPIO.output(self.dio_pin, GPIO.HIGH) # Ensure DIO is high after switching back
        time.sleep(0.000001)


    def display_number(self, number):
        """
        Displays a number (up to 4 digits) on the 7-segment display.
        Handles leading zeros and limits to 4 digits.
        """
        # Ensure number is within valid range for 4 digits (0-9999)
        number = max(0, min(9999, int(number)))
        
        # Convert number to a 4-character string, padding with leading zeros
        num_str = str(number).zfill(4)
        
        display_data = []
        for digit_char in num_str:
            # Convert each character digit back to an integer and get its segment pattern
            digit_val = int(digit_char)
            # Use .get() with a default of blank (0x00) for robustness
            display_data.append(self.SEGMENTS.get(digit_val, self.SEGMENTS[' '])) 

        # Command 1: Data command (auto address increment, normal mode)
        self._start()
        self._write_byte(0x40) 
        self._stop()

        # Command 2: Address command (start address 0)
        self._start()
        self._write_byte(0xC0) 
        for data in display_data:
            self._write_byte(data) # Write each digit's segment data
        self._stop()

        # Command 3: Display control command (display on, max brightness)
        self._start()
        self._write_byte(0x88 | 0x07) # 0x88 = Display ON, 0x07 = 7/8 brightness (max)
        self._stop()

class PinballGame:
    def __init__(self):
        # Initialize pygame modules
        pygame.init()
        pygame.mixer.init()
        
        # Screen settings
        self.screen_width = 1024
        self.screen_height = 768
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Pinball Game System")
        
        # Font settings
        self.font_large = pygame.font.Font(None, 72)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)
        
        # Color definitions
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.BLUE = (0, 0, 255)
        self.YELLOW = (255, 255, 0)
        self.ORANGE = (255, 165, 0)
        self.PURPLE = (128, 0, 128)
        self.CYAN = (0, 255, 255)
        self.PINK = (255, 192, 203)
        
        # GPIO setup
        GPIO.setmode(GPIO.BOARD) # Use board pin numbering
        
        # LED pins - Ensure these are connected correctly on your RPi
        self.led_pins = [40, 38, 36, 18, 32, 26, 24, 22] 
        # Microswitch pins - Ensure these are connected correctly on your RPi
        self.switch_pins = [3, 5, 7, 11, 13, 15, 19, 21] 
        
        # Configure GPIO for LEDs as outputs (initially off)
        for pin in self.led_pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            
        # Configure GPIO for switches as inputs with pull-up resistors
        for pin in self.switch_pins:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
        # --- Servo Motor Setup ---
        self.servo_pin = 31 # SG90 servo control pin
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.servo_pwm = GPIO.PWM(self.servo_pin, 50) # 50Hz PWM for SG90
        self.servo_pwm.start(0) # Start with 0 duty cycle, will set to default 90 degrees in next line
        self.set_servo_angle(90) # Default position for servo
        # --- End Servo Motor Setup ---

        # 7-segment display (CLK on pin 33, DIO on pin 35)
        self.display = TM1637(33, 35)
        
        # Sound loading
        self.sounds = {}
        self.load_sounds()
        
        # Game state variables
        self.current_game = 0  # 0: Main Menu, 1: Game 1, 2: Game 2, 3: Game 3
        self.running = True
        self.clock = pygame.time.Clock()
        
        # Game variables initialization
        self.reset_game_variables()

        # --- Initialize GPIO Event Detection ---
        # Debounce time for each switch (milliseconds), using GPIO's built-in bouncetime here
        self.GPIO_DEBOUNCE_TIME_MS = 150 # Recommended value, adjust based on actual switch
        
        # Queue to store button events, for cross-thread communication
        self.event_queue = []
        # Lock to protect event_queue access
        self.queue_lock = threading.Lock() 

        for i, pin in enumerate(self.switch_pins):
            # Add GPIO event detection: Trigger when pin goes from high to low (Falling edge)
            # And use built-in bouncetime for debouncing
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._gpio_callback_wrapper, bouncetime=self.GPIO_DEBOUNCE_TIME_MS)
        # --- End of GPIO Event Detection Initialization ---

        # Game 2 specific state: True if a gambling round is actively in progress
        self.game2_round_active = False 
        self.game2_game_over = False # New flag to indicate if Game 2 is completely over

        # Start background music
        self.play_background_music()

    def set_servo_angle(self, angle):
        """
        Sets the SG90 servo motor to a specified angle.
        SG90 typically maps 0-180 degrees to 2-12.5% duty cycle at 50Hz.
        A duty cycle of 2.5% is 0 degrees, 7.5% is 90 degrees, 12.5% is 180 degrees.
        The formula (angle / 18) + 2 is derived from this.
        """
        # Calculate duty cycle based on the provided formula
        duty = 2 + (angle / 18)
        self.servo_pwm.ChangeDutyCycle(duty)
        # This sleep is to allow the servo to physically move to the position.
        # It will block the main game loop for 0.5 seconds.
        # For fluid gameplay, this might be too long and could be optimized
        # by managing movement over multiple frames or in a separate thread.
        time.sleep(0.5)
        
    def _gpio_callback_wrapper(self, channel):
        """Wrapper for GPIO event callback, adds triggered event to queue."""
        # Find the switch_index corresponding to the triggered channel
        try:
            switch_index = self.switch_pins.index(channel)
            with self.queue_lock:
                self.event_queue.append(switch_index)
        except ValueError:
            print(f"Error: Unknown GPIO channel {channel} triggered callback.")

    def process_gpio_events(self):
        """Processes GPIO events from the queue."""
        with self.queue_lock:
            events_to_process = list(self.event_queue)
            self.event_queue.clear()
        
        for switch_index in events_to_process:
            self.on_switch_pressed(switch_index)


    def load_sounds(self):
        """Loads sound files for the game."""
        sound_files = {
            'background': 'sounds/background.wav',
            'hit': 'sounds/hit.wav',
            'score': 'sounds/score.wav',
            'jackpot': 'sounds/jackpot.wav'
        }
        
        for name, file_path in sound_files.items():
            try:
                if os.path.exists(file_path):
                    self.sounds[name] = pygame.mixer.Sound(file_path)
                    print(f"Loaded sound effect: {name}")
                else:
                    print(f"Sound file does not exist: {file_path}")
            except Exception as e:
                print(f"Failed to load sound {name}: {e}")
                
    def play_background_music(self):
        """Plays the background music in a loop."""
        try:
            if 'background' in self.sounds:
                pygame.mixer.music.load('sounds/background.wav')
                pygame.mixer.music.play(-1)  # Play indefinitely
                pygame.mixer.music.set_volume(0.3) # Set volume
        except Exception as e:
            print(f"Failed to play BGM: {e}")
            
    def play_sound(self, sound_name):
        """Plays a specific sound effect."""
        if sound_name in self.sounds:
            self.sounds[sound_name].play()
            
    def reset_game_variables(self):
        """Resets all game-specific variables."""
        self.score = 0
        self.game_time = 0
        self.game_duration = 30  # Game duration in seconds (still applies to Game 1 and 3)
        self.game_active = False # Overall game activity for Game 1 and 3. For Game 2, only for initial entry.
        self.led_states = [False] * 8 # All LEDs off
        self.switch_states = [False] * 8 # Current state of switches (unused for primary detection)
        self.last_switch_states = [False] * 8 # Previous state of switches (no longer needed, but kept for robustness)
        
        # Game 2 specific variables (reset when entering Game 2 or restarting Game 2)
        self.points = 100  # Starting points for gambling game
        self.bet_amount = 10  # Default bet amount
        self.multiplier = 2  # Default multiplier
        self.target_leds = []  # LEDs that grant a win in Game 2
        self.game2_round_active = False # Reset round active state when overall game variables are reset
        self.game2_game_over = False # Reset Game 2 specific game over flag
            
    def update_leds(self):
        """Updates the physical LEDs based on their boolean states."""
        for i, state in enumerate(self.led_pins):
            GPIO.output(self.led_pins[i], GPIO.HIGH if self.led_states[i] else GPIO.LOW)
            
    def on_switch_pressed(self, switch_index):
        """Handles logic when a microswitch is pressed. (Now as a GPIO event callback)"""
        self.play_sound('hit') # Play a generic hit sound
        print(f"Switch {switch_index+1} pressed!") # Add print for detected press
        
        # Delegate to specific game handler
        if self.current_game == 1:
            self.handle_game1_switch(switch_index)
        elif self.current_game == 2:
            self.handle_game2_switch(switch_index)
        elif self.current_game == 3:
            self.handle_game3_switch(switch_index)
            
    def handle_game1_switch(self, switch_index):
        """Logic for Game 1 (Lighting Up) when a switch is pressed."""
        if self.game_active:
            if not self.led_states[switch_index]: # If LED is not already lit
                self.led_states[switch_index] = True # Light it up
                self.score += 10 # Increase score
                self.play_sound('score') # Play score sound
                self.update_leds() # Update physical LEDs
                
    def handle_game2_switch(self, switch_index):
        """Logic for Game 2 (Gambling) when a switch is pressed."""
        # Only process if a round is actually active and game is not over
        if self.game2_round_active and not self.game2_game_over: 
            if switch_index in self.target_leds:
                win_amount = self.bet_amount * self.multiplier
                self.points += win_amount
                self.play_sound('jackpot') # Play jackpot sound
                print(f"Jackpot! You win {win_amount} points!")
            else:
                # Deducting bet already happened at start of round. No further deduction for miss.
                print(f"Miss! No points gained for hitting switch {switch_index+1}.")
            
            # --- Servo Motor Action for Game 2 Sensor Press ---
            self.set_servo_angle(90) # Set motor to 90 degrees when sensor is pressed
            # --- End Servo Motor Action ---

            # End the current round
            self.game2_round_active = False
            self.led_states = [False] * len(self.led_pins) # Turn off all LEDs after round
            self.update_leds()
            self.display.display_number(self.points) # Update display with current points

            # Check for game over *after* points update
            if self.points <= 0:
                self.game2_game_over = True # Set Game 2 specific game over flag
                self.end_game() # Call end_game to show "Game Over" screen
            
    def handle_game3_switch(self, switch_index):
        """Logic for Game 3 (Toggle Lighting) when a switch is pressed."""
        if self.game_active:
            if self.led_states[switch_index]: # If LED is currently lit
                self.led_states[switch_index] = False # Turn it off
                self.score -= 10 # Deduct score
                print(f"LED {switch_index+1} turned OFF. Score: {self.score}")
            else: # If LED is currently off
                self.led_states[switch_index] = True # Turn it on
                self.score += 10 # Add score
                print(f"LED {switch_index+1} turned ON. Score: {self.score}")
            
            self.update_leds() # Update physical LEDs
            self.play_sound('score') # Play score sound for any score change
            
    # --- Removed trigger_chain_reaction as it's no longer used for Game 3 ---
    # def trigger_chain_reaction(self, start_index):
    #     """Triggers a visual and scoring chain reaction."""
    #     # ... (original chain reaction code) ...
    # --- End Removed ---
        
    def draw_main_menu(self):
        """Draws the main menu screen."""
        self.screen.fill(self.BLACK)
        
        title = self.font_large.render("Pinball Game System", True, self.WHITE)
        title_rect = title.get_rect(center=(self.screen_width//2, 100))
        self.screen.blit(title, title_rect)
        
        menu_items = [
            "1 - Lighting Up",
            "2 - Gambling", 
            "3 - Very easy mode :)", # Updated menu text
            "ESC - Exit"
        ]
        
        colors = [self.CYAN, self.YELLOW, self.PINK, self.RED]
        
        for i, item in enumerate(menu_items):
            text = self.font_medium.render(item, True, colors[i])
            text_rect = text.get_rect(center=(self.screen_width//2, 250 + i*80))
            self.screen.blit(text, text_rect)
            
        # Display instructions for each game
        instructions = [
            "Game 1: Light up as many fields as you can within the time limit.",
            "Game 2: Bet your points, choose a multiplier, and hit the target LEDs to win big!", 
            "Game 3: Toggle LEDs on/off. +10 points for ON, -10 points for OFF." # Updated instruction
        ]
        
        for i, instruction in enumerate(instructions):
            text = self.font_small.render(instruction, True, self.WHITE)
            text_rect = text.get_rect(center=(self.screen_width//2, 600 + i*30))
            self.screen.blit(text, text_rect)
            
    def draw_game1(self):
        """Draws the Game 1 (Lighting Up) interface."""
        self.screen.fill(self.BLACK)
        
        title = self.font_large.render("Lighting Up", True, self.CYAN)
        title_rect = title.get_rect(center=(self.screen_width//2, 50))
        self.screen.blit(title, title_rect)
        
        # Display current score
        score_text = self.font_medium.render(f"Score: {self.score}", True, self.WHITE)
        self.screen.blit(score_text, (50, 100))
        
        # Display remaining time
        remaining_time = max(0, self.game_duration - self.game_time)
        time_text = self.font_medium.render(f"Time: {remaining_time:.1f}s", True, self.WHITE)
        self.screen.blit(time_text, (50, 150))
        
        # Draw the LED grid representation
        self.draw_led_grid()
        
        if not self.game_active:
            if self.game_time >= self.game_duration:
                # Game over screen
                end_text = self.font_large.render("Game Over", True, self.RED)
                end_rect = end_text.get_rect(center=(self.screen_width//2, 400))
                self.screen.blit(end_text, end_rect)
                
                final_score = self.font_medium.render(f"Final Score: {self.score}", True, self.YELLOW)
                final_rect = final_score.get_rect(center=(self.screen_width//2, 450))
                self.screen.blit(final_score, final_rect)
                
                restart_text = self.font_small.render("Press R to restart, press M to go back to menu", True, self.WHITE)
                restart_rect = restart_text.get_rect(center=(self.screen_width//2, 500))
                self.screen.blit(restart_text, restart_rect)
            else:
                # Instructions before game starts
                start_text = self.font_medium.render("Press SPACE to start", True, self.GREEN)
                start_rect = start_text.get_rect(center=(self.screen_width//2, 400))
                self.screen.blit(start_text, start_rect)
                
    def draw_game2(self):
        """Draws the Game 2 (Gambling) interface."""
        self.screen.fill(self.BLACK)
        
        title = self.font_large.render("Gambling Game", True, self.YELLOW)
        title_rect = title.get_rect(center=(self.screen_width//2, 50))
        self.screen.blit(title, title_rect)
        
        # Display current points
        points_text = self.font_medium.render(f"Points: {self.points}", True, self.WHITE)
        self.screen.blit(points_text, (50, 100))
        
        # Display current bet amount and multiplier
        bet_text = self.font_medium.render(f"Bet: {self.bet_amount}", True, self.WHITE)
        self.screen.blit(bet_text, (50, 150))
        
        multiplier_text = self.font_medium.render(f"Multiplier: {self.multiplier}x", True, self.WHITE)
        self.screen.blit(multiplier_text, (50, 200))
        
        # Removed time display as requested for Game 2
        
        # Draw the LED grid representation
        self.draw_led_grid()
        
        if self.game2_game_over: 
            # Game over due to points exhausted
            end_text = self.font_large.render("Game Over - Points Exhausted!", True, self.RED)
            end_rect = end_text.get_rect(center=(self.screen_width//2, 400))
            self.screen.blit(end_text, end_rect)
            
            restart_text = self.font_small.render("Press R to restart Game 2, press M to go back to menu", True, self.WHITE)
            restart_rect = restart_text.get_rect(center=(self.screen_width//2, 500))
            self.screen.blit(restart_text, restart_rect)
        elif not self.game2_round_active: # If no round is active (player can adjust bet/multiplier or start new round)
            controls = [
                "UP/DOWN: Adjust Bet Amount",
                "LEFT/RIGHT: Select Multiplier (2x/3x/5x)",
                "SPACE: Start New Round"
            ]
            
            for i, control in enumerate(controls):
                text = self.font_small.render(control, True, self.WHITE)
                text_rect = text.get_rect(center=(self.screen_width//2, 400 + i*30))
                self.screen.blit(text, text_rect)
        else: # A gambling round is actively in progress
            round_active_text = self.font_large.render("Round Active! Hit a switch!", True, self.GREEN)
            round_active_rect = round_active_text.get_rect(center=(self.screen_width//2, 400))
            self.screen.blit(round_active_text, round_active_rect)
                
    def draw_game3(self):
        """Draws the Game 3 (Toggle Lighting) interface."""
        # No servo action needed here for smooth startup, only at game start via start_game3()
        self.screen.fill(self.BLACK)
        
        title = self.font_large.render("Toggle Lighting LOL", True, self.PINK) # Updated title
        title_rect = title.get_rect(center=(self.screen_width//2, 50))
        self.screen.blit(title, title_rect)
        
        # Display current score
        score_text = self.font_medium.render(f"Score: {self.score}", True, self.WHITE)
        self.screen.blit(score_text, (50, 100))
        
        # Display remaining time
        remaining_time = max(0, self.game_duration - self.game_time)
        time_text = self.font_medium.render(f"Time: {remaining_time:.1f}s", True, self.WHITE)
        self.screen.blit(time_text, (50, 150))
        
        # Draw the LED grid representation
        self.draw_led_grid()
        
        if not self.game_active:
            if self.game_time >= self.game_duration:
                # Game over screen
                end_text = self.font_large.render("Game Over", True, self.RED)
                end_rect = end_text.get_rect(center=(self.screen_width//2, 400))
                self.screen.blit(end_text, end_rect)
                
                final_score = self.font_medium.render(f"Final Score: {self.score}", True, self.YELLOW)
                final_rect = final_score.get_rect(center=(self.screen_width//2, 450))
                self.screen.blit(final_score, final_rect)
                
                restart_text = self.font_small.render("Press R to restart, press M to go back to menu", True, self.WHITE)
                restart_rect = restart_text.get_rect(center=(self.screen_width//2, 500))
                self.screen.blit(restart_text, restart_rect)
            else:
                # Instructions before game starts
                start_text = self.font_medium.render("Press SPACE to start", True, self.GREEN)
                start_rect = start_text.get_rect(center=(self.screen_width//2, 400))
                self.screen.blit(start_text, start_rect)
                
                # Updated instruction for Game 3
                info_text = self.font_small.render("Hit a switch to toggle LED on/off. +10 for ON, -10 for OFF.", True, self.WHITE)
                info_rect = info_text.get_rect(center=(self.screen_width//2, 450))
                self.screen.blit(info_text, info_rect)
                
    def draw_led_grid(self):
        """Draws the visual representation of the LEDs on the screen."""
        led_size = 60
        led_spacing = 80
        # Calculate starting X to center the LEDs horizontally
        start_x = (self.screen_width - (len(self.led_pins) * led_spacing - (led_spacing - led_size))) // 2
        start_y = 300
        
        # Colors for each LED (can be customized)
        colors = [self.RED, self.GREEN, self.BLUE, self.YELLOW, 
                  self.ORANGE, self.PURPLE, self.CYAN, self.PINK]
        
        for i in range(len(self.led_pins)):
            x = start_x + i * led_spacing
            y = start_y
            
            # Draw background circle for the LED (white border)
            pygame.draw.circle(self.screen, self.WHITE, (x, y), led_size//2 + 2)
            
            # Draw the LED circle (lit or unlit)
            color = colors[i] if self.led_states[i] else self.BLACK
            pygame.draw.circle(self.screen, color, (x, y), led_size//2)
            
            # Draw the LED number below it
            number = self.font_small.render(str(i+1), True, self.WHITE)
            number_rect = number.get_rect(center=(x, y + led_size//2 + 20))
            self.screen.blit(number, number_rect)
            
            # If it's Game 2, highlight target LEDs with a white ring
            if self.current_game == 2 and i in self.target_leds:
                pygame.draw.circle(self.screen, self.WHITE, (x, y), led_size//2 + 5, 3)
                
    def start_game1(self):
        """Initializes and starts Game 1."""
        self.reset_game_variables() # Reset common game variables
        self.game_active = True
        self.game_time = 0
        print("Game 1 started (Lighting Up)")
        self.display.display_number(0) # Clear display
        # --- Servo Motor Action for Game 1 Start ---
        self.set_servo_angle(0) # Set motor to 0 degrees when Game 1 starts
        # --- End Servo Motor Action ---
        
    def start_game2_round(self): # Renamed for clarity: this starts a *round* of Game 2
        """Starts a new round of Game 2 (Gambling)."""
        if self.points < self.bet_amount:
            print("Not enough points to place the bet!")
            # Display a temporary message on screen
            message_text = self.font_medium.render("Not enough points to bet!", True, self.RED)
            message_rect = message_text.get_rect(center=(self.screen_width//2, self.screen_height - 100))
            self.screen.blit(message_text, message_rect)
            pygame.display.flip()
            time.sleep(1.5) # Show message for a moment
            return # Do not start round

        self.points -= self.bet_amount # Deduct bet at the start of the round
        self.game2_round_active = True # Set round to active
        
        # --- Servo Motor Action for Game 2 Round Start ---
        self.set_servo_angle(0) # Set motor to 0 degrees when bet is confirmed
        # --- End Servo Motor Action ---

        # Determine number of target LEDs based on multiplier
        if self.multiplier == 2:
            num_targets = 4
        elif self.multiplier == 3:
            num_targets = 2
        else:  # 5x
            num_targets = 1
            
        # Select random target LEDs for this round
        self.target_leds = random.sample(range(len(self.led_pins)), num_targets)
        
        # Light up only the target LEDs
        self.led_states = [False] * len(self.led_pins)
        for led_index in self.target_leds:
            self.led_states[led_index] = True
        self.update_leds()
        
        print(f"Game 2 Round started. Bet: {self.bet_amount}, Multiplier: {self.multiplier}x, Target LEDs: {self.target_leds}")
        self.display.display_number(self.points) # Display current points on 7-segment display
            
    def start_game3(self):
        """Initializes and starts Game 3 (Toggle Lighting).""" # Updated comment
        self.reset_game_variables() # Reset common game variables
        self.game_active = True
        self.game_time = 0
        # Turn off all LEDs initially for Game 3 (Crucial for toggle logic)
        self.led_states = [False] * len(self.led_pins)
        self.update_leds()
        print("Game 3 started (Toggle Lighting)") # Updated print
        self.display.display_number(0) # Clear display
        self.set_servo_angle(0)
        
    def update_game_timer(self, dt):
        """Updates the game timer and handles game end."""
        # Timer only runs for Game 1 and 3 when active
        if self.current_game in [1, 3] and self.game_active:
            self.game_time += dt
            
            # Update the 7-segment display with remaining time (times 10 for 0.1s precision)
            remaining_time = max(0, self.game_duration - self.game_time)
            # Ensure the number is an integer for display_number
            self.display.display_number(int(remaining_time * 10)) 
            
            if self.game_time >= self.game_duration:
                self.end_game()
                
    def end_game(self):
        """Ends the current game (or signals Game 2 end if points exhausted)."""
        # For Game 1 and 3, this ends the game.
        # For Game 2, this only sets game2_game_over=True. The game_active flag stays True
        # until the user explicitly returns to the main menu or restarts Game 2.
        self.game_active = False 
        self.game2_round_active = False # Ensure Game 2 round is not active

        # Turn off all physical LEDs
        self.led_states = [False] * len(self.led_pins)
        self.update_leds()
        
        # Display final score/points on the 7-segment display
        final_value = self.score if self.current_game != 2 else self.points
        self.display.display_number(final_value)
        
        # Specific message for Game 2 end (points exhausted)
        if self.current_game == 2 and final_value <= 0:
            print("Game Over! Points exhausted in Gambling Game!")
        else:
            print(f"Game Over! Final value: {final_value}")

        # --- Servo Motor Action for Game 1 and 3 End ---
        # Only set servo to 90 degrees if Game 1 or Game 3 ended (not for Game 2 points exhaustion)
        if self.current_game in [1, 3]:
            self.set_servo_angle(90) 
        # --- End Servo Motor Action ---
        
    def handle_events(self):
        """Processes Pygame events (keyboard inputs, window close)."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False # Set flag to exit main loop
                
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.current_game == 0:
                        self.running = False # Exit if in main menu
                    else:
                        # Go back to main menu from any game
                        self.current_game = 0
                        self.reset_game_variables()
                        self.display.display_number(0) # Clear display
                        # Ensure servo is at default position when returning to main menu
                        self.set_servo_angle(90) 
                        
                elif self.current_game == 0:  # Main Menu selections
                    if event.key == pygame.K_1:
                        self.current_game = 1
                        self.reset_game_variables() # Reset for new game
                        self.display.display_number(0) # Clear display
                    elif event.key == pygame.K_2:
                        self.current_game = 2
                        self.reset_game_variables() # Reset for new game
                        # Points already reset to 100 by reset_game_variables
                        self.display.display_number(self.points) # Display starting points for Game 2
                        # Game 2 itself is "active" as long as points > 0, even if no round is
                        # currently active, so game_active can be True.
                        self.game_active = True 
                        self.game2_game_over = False # Ensure Game 2 is not in game over state on entry
                    elif event.key == pygame.K_3:
                        self.current_game = 3
                        self.reset_game_variables() # Reset for new game
                        self.display.display_number(0) # Clear display
                        
                else:  # In-game key presses
                    if event.key == pygame.K_SPACE:
                        # Game 1 or 3: Start if not active
                        if self.current_game in [1, 3]:
                            if not self.game_active:
                                if self.current_game == 1:
                                    self.start_game1()
                                elif self.current_game == 3:
                                    self.start_game3()
                        # Game 2: Start a new round if not active AND game not over
                        elif self.current_game == 2:
                            if not self.game2_round_active and not self.game2_game_over:
                                self.start_game2_round() # Call the new round-starting function
                                
                    elif event.key == pygame.K_r: # Restart current game
                        if self.current_game == 1:
                            self.start_game1() # This will call set_servo_angle(0)
                        elif self.current_game == 2:
                            # For Game 2, restart means resetting points and state
                            self.reset_game_variables() # This sets points to 100 and round_active to False
                            self.display.display_number(self.points) # Display starting points
                            self.game_active = True # Allow betting again
                            self.game2_game_over = False # Clear game over state
                            self.set_servo_angle(90) # Return servo to default when restarting Game 2
                        elif self.current_game == 3:
                            self.start_game3()
                                
                    elif event.key == pygame.K_m: # Go back to main menu
                        self.current_game = 0
                        self.reset_game_variables()
                        self.display.display_number(0) # Clear display
                        self.set_servo_angle(90) # Ensure servo is at default position when returning to main menu
                        
                    # Game 2 specific controls (only when in Game 2 AND no round is active AND game not over)
                    elif self.current_game == 2 and not self.game2_round_active and not self.game2_game_over:
                        if event.key == pygame.K_UP:
                            # Increase bet, cap at current points, min 10
                            self.bet_amount = min(self.bet_amount + 10, self.points)
                            self.bet_amount = max(self.bet_amount, 10) 
                        elif event.key == pygame.K_DOWN:
                            # Decrease bet, minimum 10
                            self.bet_amount = max(self.bet_amount - 10, 10)
                        elif event.key == pygame.K_LEFT:
                            # Cycle through multipliers (2x, 3x, 5x)
                            multipliers = [2, 3, 5]
                            current_index = multipliers.index(self.multiplier)
                            self.multiplier = multipliers[(current_index - 1) % len(multipliers)]
                        elif event.key == pygame.K_RIGHT:
                            # Cycle through multipliers (2x, 3x, 5x)
                            multipliers = [2, 3, 5]
                            current_index = multipliers.index(self.multiplier)
                            self.multiplier = multipliers[(current_index + 1) % len(multipliers)]
                            
    def run(self):
        """Main game loop."""
        try:
            while self.running:
                dt = self.clock.tick(60) / 1000.0  # Delta time for 60 FPS
                
                self.handle_events() # Process keyboard and window events
                self.process_gpio_events() # Processes GPIO events from the queue
                
                # Update timer only for Game 1 and 3 when active
                if self.current_game in [1, 3] and self.game_active:
                    self.update_game_timer(dt)
                
                # Draw the current screen based on game state
                if self.current_game == 0:
                    self.draw_main_menu()
                elif self.current_game == 1:
                    self.draw_game1()
                elif self.current_game == 2:
                    self.draw_game2()
                elif self.current_game == 3:
                    self.draw_game3()
                    
                pygame.display.flip() # Update the full display surface to the screen
                
        except KeyboardInterrupt:
            print("Game interrupted by user.")
        finally:
            self.cleanup() # Ensure cleanup even if an error occurs

    def cleanup(self):
        """Cleans up GPIO pins, stops music, and quits Pygame."""
        # Turn off all LEDs before cleanup
        for pin in self.led_pins:
            GPIO.output(pin, GPIO.LOW)
            
        # Clean up all GPIO settings (remove event detection and reset pins)
        GPIO.cleanup()
        
        # Stop any playing music
        pygame.mixer.music.stop()
        
        # --- Servo Motor Cleanup ---
        self.servo_pwm.stop() # Stop PWM signal
        # --- End Servo Motor Cleanup ---

        # Quit Pygame modules
        pygame.quit()
        
        print("Exiting game and cleaning up resources...")

if __name__ == "__main__":
    try:
        game = PinballGame()
        game.run()
    except Exception as e:
        print(f"An unexpected game error occurred: {e}")
        # Ensure GPIO is cleaned up even if game.run() itself fails
        # Attempt to stop PWM even in error case, if pwm object exists
        try:
            if 'game' in locals() and hasattr(game, 'servo_pwm'):
                game.servo_pwm.stop()
        except NameError:
            pass # game object might not have been created yet
        finally:
            GPIO.cleanup() 
            pygame.quit()
