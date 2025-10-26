"""
Gesture-Controlled Angry Balls Game - Simplified Stable Version
Improved version based on test version, providing reliable gesture control experience
"""

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import cv2
import numpy as np
import mediapipe as mp
import math

# Initialize MediaPipe
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

@st.cache_resource
def get_hand_detector():
    """Get hand detector"""
    return mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5
    )

class SimpleBird:
    """Simplified bird class"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.radius = 15
        self.vel_x = 0
        self.vel_y = 0
        self.is_flying = False
        self.trail = []  # Flight trajectory
        
    def reset(self):
        """Reset bird to initial position"""
        self.x = self.start_x
        self.y = self.start_y
        self.vel_x = 0
        self.vel_y = 0
        self.is_flying = False
        self.trail = []
    
    def update(self):
        """Update bird physics"""
        if self.is_flying:
            self.vel_y += 0.3  # Gravity
            self.vel_x *= 0.995  # Air resistance
            self.x += self.vel_x
            self.y += self.vel_y
            
            # Record trajectory
            if len(self.trail) < 20:
                self.trail.append((int(self.x), int(self.y)))
    
    def launch(self, vel_x, vel_y):
        """Launch bird"""
        self.vel_x = vel_x
        self.vel_y = vel_y
        self.is_flying = True
        self.trail = [(int(self.x), int(self.y))]
    
    def draw(self, frame):
        """Draw bird and trajectory"""
        # Draw flight trajectory
        for i in range(1, len(self.trail)):
            alpha = i / len(self.trail)
            color = (int(255 * alpha), int(255 * alpha), 0)
            cv2.line(frame, self.trail[i-1], self.trail[i], color, 2)
        
        # Draw bird body
        cv2.circle(frame, (int(self.x), int(self.y)), self.radius, (0, 255, 255), -1)
        
        # Draw eyes
        eye_offset = self.radius // 3
        cv2.circle(frame, (int(self.x - eye_offset), int(self.y - eye_offset)), 3, (0, 0, 0), -1)
        cv2.circle(frame, (int(self.x + eye_offset), int(self.y - eye_offset)), 3, (0, 0, 0), -1)

class SimpleTarget:
    """Simplified target class"""
    def __init__(self, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius
        self.is_destroyed = False
        
    def check_collision(self, bird):
        """Check collision with bird"""
        if self.is_destroyed:
            return False
        distance = math.sqrt((self.x - bird.x)**2 + (self.y - bird.y)**2)
        if distance < (self.radius + bird.radius):
            self.is_destroyed = True
            return True
        return False
    
    def draw(self, frame):
        """Draw target"""
        if not self.is_destroyed:
            cv2.circle(frame, (int(self.x), int(self.y)), self.radius, (0, 255, 0), -1)
            # Draw eyes
            eye_offset = self.radius // 3
            cv2.circle(frame, (int(self.x - eye_offset), int(self.y - eye_offset)), 3, (0, 0, 0), -1)
            cv2.circle(frame, (int(self.x + eye_offset), int(self.y - eye_offset)), 3, (0, 0, 0), -1)

class SimpleGame:
    """Simplified game class"""
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pulling = False
        self.pull_x = 0
        self.pull_y = 0
        self.score = 0
        self.game_won = False
        
        # Pause system
        self.is_paused = False
        self.fist_detected = False  # Whether fist is detected in current frame
        self.last_fist_state = False  # Fist state of previous frame
        self.pause_message_timer = 0  # Pause message display timer
        
        # Game area centering settings
        self.game_area_width = min(width * 0.8, 800)  # Game area width, max 800 pixels
        self.game_area_height = min(height * 0.8, 600)  # Game area height, max 600 pixels
        self.game_offset_x = (width - self.game_area_width) // 2  # Horizontal center offset
        self.game_offset_y = (height - self.game_area_height) // 2  # Vertical center offset
        
        # Level system
        self.current_level = 1
        self.max_level = 5
        
        # Animation system
        self.is_transitioning = False
        self.transition_progress = 0  # 0-100
        self.transition_direction = 'left'  # 'left' or 'right'
        self.old_game_surface = None
        
        # Restart button - optimized position to left-center for easier access
        self.reset_button = {
            'x': 10,  # Left margin
            'y': height // 2 + 130,  # Move further down from +100 to +130
            'width': 110,
            'height': 40,
            'clicked': False,
            'hover': False,
            'progress': 0.0,  # Progress bar progress (0.0 - 1.0)
            'max_progress': 60,  # Required hover frames (about 1 second)
            'active': False,  # Whether progress is active
            # Expand detection area
            'detection_padding': 20,  # Expand detection area by 20 pixels
            'fallback_activated': False,  # Fallback activation method
            # Single trigger control
            'has_triggered': False,  # Whether already triggered
            'was_in_area': False,  # Whether in button area last frame
            'trigger_cooldown': 30  # Brief cooldown after trigger (frames, about 0.5 seconds)
        }
        
        self.init_level()
    
    def init_level(self):
        """Initialize current level"""
        self.bird = SimpleBird(self.game_offset_x + 100, self.game_offset_y + self.game_area_height - 150)
        
        # Generate different target configurations based on level
        if self.current_level == 1:
            self.targets = [
                SimpleTarget(self.game_offset_x + self.game_area_width - 100, self.game_offset_y + self.game_area_height - 100),
                SimpleTarget(self.game_offset_x + self.game_area_width - 150, self.game_offset_y + self.game_area_height - 150),
                SimpleTarget(self.game_offset_x + self.game_area_width - 200, self.game_offset_y + self.game_area_height - 100),
            ]
        elif self.current_level == 2:
            self.targets = [
                SimpleTarget(self.game_offset_x + self.game_area_width - 80, self.game_offset_y + self.game_area_height - 80),
                SimpleTarget(self.game_offset_x + self.game_area_width - 120, self.game_offset_y + self.game_area_height - 120),
                SimpleTarget(self.game_offset_x + self.game_area_width - 160, self.game_offset_y + self.game_area_height - 160),
                SimpleTarget(self.game_offset_x + self.game_area_width - 200, self.game_offset_y + self.game_area_height - 80),
            ]
        elif self.current_level == 3:
            self.targets = [
                SimpleTarget(self.game_offset_x + self.game_area_width - 70, self.game_offset_y + self.game_area_height - 70),
                SimpleTarget(self.game_offset_x + self.game_area_width - 110, self.game_offset_y + self.game_area_height - 110),
                SimpleTarget(self.game_offset_x + self.game_area_width - 150, self.game_offset_y + self.game_area_height - 150),
                SimpleTarget(self.game_offset_x + self.game_area_width - 190, self.game_offset_y + self.game_area_height - 110),
                SimpleTarget(self.game_offset_x + self.game_area_width - 230, self.game_offset_y + self.game_area_height - 70),
            ]
        elif self.current_level == 4:
            # Pyramid shape
            self.targets = [
                SimpleTarget(self.game_offset_x + self.game_area_width - 100, self.game_offset_y + self.game_area_height - 60),
                SimpleTarget(self.game_offset_x + self.game_area_width - 140, self.game_offset_y + self.game_area_height - 60),
                SimpleTarget(self.game_offset_x + self.game_area_width - 180, self.game_offset_y + self.game_area_height - 60),
                SimpleTarget(self.game_offset_x + self.game_area_width - 120, self.game_offset_y + self.game_area_height - 100),
                SimpleTarget(self.game_offset_x + self.game_area_width - 160, self.game_offset_y + self.game_area_height - 100),
                SimpleTarget(self.game_offset_x + self.game_area_width - 140, self.game_offset_y + self.game_area_height - 140),
            ]
        else:  # Level 5 and beyond
            # Complex layout
            self.targets = [
                SimpleTarget(self.game_offset_x + self.game_area_width - 80, self.game_offset_y + self.game_area_height - 60),
                SimpleTarget(self.game_offset_x + self.game_area_width - 120, self.game_offset_y + self.game_area_height - 100),
                SimpleTarget(self.game_offset_x + self.game_area_width - 160, self.game_offset_y + self.game_area_height - 140),
                SimpleTarget(self.game_offset_x + self.game_area_width - 200, self.game_offset_y + self.game_area_height - 100),
                SimpleTarget(self.game_offset_x + self.game_area_width - 240, self.game_offset_y + self.game_area_height - 60),
                SimpleTarget(self.game_offset_x + self.game_area_width - 130, self.game_offset_y + self.game_area_height - 180),
                SimpleTarget(self.game_offset_x + self.game_area_width - 170, self.game_offset_y + self.game_area_height - 180),
            ]
        
        self.pulling = False
        
    def update(self):
        """Update game state"""
        # Priority handling of transition animation
        if self.is_transitioning:
            self.update_transition()
            return
        
        self.bird.update()
        
        # Check collisions
        for target in self.targets:
            if target.check_collision(self.bird):
                self.score += 100
        
        # Check boundaries (based on game area)
        if (self.bird.x > self.game_offset_x + self.game_area_width or 
            self.bird.y > self.game_offset_y + self.game_area_height or 
            self.bird.x < self.game_offset_x):
            if self.bird.is_flying:
                self.bird.reset()
        
        # Check victory condition
        self.game_won = all(target.is_destroyed for target in self.targets)
    
    def start_pull(self, x, y):
        """Start pulling slingshot"""
        if not self.bird.is_flying and not self.game_won:
            distance = math.sqrt((x - self.bird.x)**2 + (y - self.bird.y)**2)
            if distance < 40:  # Near the bird
                self.pulling = True
    
    def update_pull(self, x, y):
        """Update slingshot pull position"""
        if self.pulling:
            # Limit slingshot pulling distance
            max_distance = 100
            distance = math.sqrt((x - self.bird.start_x)**2 + (y - self.bird.start_y)**2)
            if distance > max_distance:
                # Limit within maximum distance
                direction_x = (x - self.bird.start_x) / distance
                direction_y = (y - self.bird.start_y) / distance
                x = self.bird.start_x + direction_x * max_distance
                y = self.bird.start_y + direction_y * max_distance
            
            self.pull_x = x
            self.pull_y = y
            self.bird.x = x
            self.bird.y = y
    
    def release(self):
        """Release slingshot"""
        if self.pulling:
            vel_x = (self.bird.start_x - self.bird.x) * 0.15
            vel_y = (self.bird.start_y - self.bird.y) * 0.15
            self.bird.launch(vel_x, vel_y)
            self.pulling = False
    
    def reset_game(self):
        """Reset game"""
        self.bird.reset()
        for target in self.targets:
            target.is_destroyed = False
        self.score = 0
        self.game_won = False
        self.pulling = False
    
    def next_level(self):
        """Enter next level"""
        if not self.is_transitioning and self.current_level < self.max_level:
            self.start_transition('left')
            self.current_level += 1
    
    def start_transition(self, direction='left'):
        """Start level transition animation"""
        self.is_transitioning = True
        self.transition_progress = 0
        self.transition_direction = direction
        # Here we can save current screen state for animation
    
    def update_transition(self):
        """Update transition animation"""
        if self.is_transitioning:
            self.transition_progress += 3  # Animation speed
            
            if self.transition_progress >= 100:
                # Animation complete
                self.is_transitioning = False
                self.transition_progress = 0
                self.init_level()  # Initialize new level
                return True  # Return True indicates animation complete
        return False
    
    def check_button_hover(self, x, y):
        """Check button hover - can only retrigger after leaving and entering again"""
        button = self.reset_button
        padding = button['detection_padding']
        
        # Expanded detection area
        expanded_x1 = button['x'] - padding
        expanded_y1 = button['y'] - padding
        expanded_x2 = button['x'] + button['width'] + padding
        expanded_y2 = button['y'] + button['height'] + padding
        
        # Check if in expanded detection area
        in_expanded_area = (expanded_x1 <= x <= expanded_x2 and 
                           expanded_y1 <= y <= expanded_y2)
        
        # Check if in actual button area
        in_button_area = (button['x'] <= x <= button['x'] + button['width'] and
                         button['y'] <= y <= button['y'] + button['height'])
        
        # Current frame status
        current_in_area = in_expanded_area
        
        # Detect enter event: currently in area but not in area last frame
        just_entered = current_in_area and not button['was_in_area']
        
        # Detect leave event: currently not in area but was in area last frame
        just_left = not current_in_area and button['was_in_area']
        
        # If just left button area, reset trigger flag
        if just_left:
            button['has_triggered'] = False
            button['progress'] = 0
            button['active'] = False
            button['hover'] = False
        
        # If in area and not triggered yet
        if current_in_area and not button['has_triggered']:
            button['hover'] = True
            button['active'] = True
            
            # Increase progress
            if in_button_area:
                button['progress'] += 2  # Faster progress in actual button area
            else:
                button['progress'] += 1  # Normal progress in expanded area
            
            # Check if trigger condition reached
            if button['progress'] >= button['max_progress']:
                # Trigger restart
                self.reset_game()
                button['has_triggered'] = True  # Mark as triggered
                button['progress'] = button['max_progress']  # Keep full progress display
                button['active'] = False
                
                # Record current state and return
                button['was_in_area'] = current_in_area
                return True
        
        # If in area but already triggered, maintain state but don't increase progress
        elif current_in_area and button['has_triggered']:
            button['hover'] = True
            button['active'] = False  # No longer in active state
            # Progress stays at max value, shows completed state
        
        # If not in area, reset hover state
        elif not current_in_area:
            button['hover'] = False
            button['active'] = False
            # Only decay progress if not triggered yet
            if not button['has_triggered']:
                button['progress'] = max(0, button['progress'] - 3)  # Fast decay
        
        # Record current frame state for next frame use
        button['was_in_area'] = current_in_area
        
        return False
    
    def update_pause_state(self):
        """Update pause state management"""
        # Detect fist state change
        if self.fist_detected and not self.last_fist_state:
            # Just started making fist, enter pause state
            self.is_paused = True
            self.pause_message_timer = 120  # 2 seconds message display time (assuming 60fps)
        elif not self.fist_detected and self.last_fist_state:
            # Released fist, exit pause state
            self.is_paused = False
            self.pause_message_timer = 60  # 1 second unpause message
        
        # Update last frame fist state
        self.last_fist_state = self.fist_detected
        
        # Decrease pause message timer
        if self.pause_message_timer > 0:
            self.pause_message_timer -= 1
    
    def draw(self, frame):
        """Draw game screen"""
        # If transitioning, draw animation effect
        if self.is_transitioning:
            self.draw_transition(frame)
            return
        
        # Draw game area background
        overlay = frame.copy()
        cv2.rectangle(overlay, (int(self.game_offset_x), int(self.game_offset_y)), 
                     (int(self.game_offset_x + self.game_area_width), 
                      int(self.game_offset_y + self.game_area_height)), 
                     (240, 248, 255), -1)  # Light blue background
        cv2.addWeighted(overlay, 0.1, frame, 0.9, 0, frame)
        
        # Draw game area border
        cv2.rectangle(frame, (int(self.game_offset_x), int(self.game_offset_y)), 
                     (int(self.game_offset_x + self.game_area_width), 
                      int(self.game_offset_y + self.game_area_height)), 
                     (200, 200, 200), 2)
        
        # Draw semi-transparent ground (within game area)
        overlay = frame.copy()
        cv2.rectangle(overlay, (int(self.game_offset_x), int(self.game_offset_y + self.game_area_height - 50)), 
                     (int(self.game_offset_x + self.game_area_width), int(self.game_offset_y + self.game_area_height)), 
                     (34, 139, 34), -1)
        cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
        
        # Draw slingshot (within game area)
        sling_x, sling_y = self.game_offset_x + 100, self.game_offset_y + self.game_area_height - 100
        cv2.rectangle(frame, (int(sling_x - 10), int(sling_y - 60)), (int(sling_x + 10), int(sling_y)), (139, 69, 19), -1)
        
        if self.pulling:
            # Pulled slingshot state
            cv2.line(frame, (int(sling_x - 10), int(sling_y - 30)), (int(self.bird.x), int(self.bird.y)), (0, 0, 255), 3)
            cv2.line(frame, (int(sling_x + 10), int(sling_y - 30)), (int(self.bird.x), int(self.bird.y)), (0, 0, 255), 3)
            
            # Show tension line
            cv2.line(frame, (int(self.bird.start_x), int(self.bird.start_y)), 
                    (int(self.bird.x), int(self.bird.y)), (255, 255, 0), 2)
        else:
            # Normal slingshot
            cv2.line(frame, (int(sling_x - 10), int(sling_y - 30)), (int(sling_x + 10), int(sling_y - 30)), (0, 0, 255), 3)
        
        # Draw targets
        for target in self.targets:
            target.draw(frame)
        
        # Draw bird
        self.bird.draw(frame)
        
        # Draw UI
        self.draw_ui(frame)
    
    def draw_transition(self, frame):
        """Draw level transition animation"""
        # Create sliding effect
        progress = self.transition_progress / 100.0
        
        if self.transition_direction == 'left':
            # Current screen slides left
            offset_x = int(self.width * progress)
            
            # Draw sliding current screen
            if offset_x < self.width:
                # Create sub-region to draw current level
                current_roi = frame[:, offset_x:]
                if current_roi.shape[1] > 0:
                    self.draw_current_level(current_roi, -offset_x)
            
            # Draw sliding in new screen
            if offset_x > 0:
                new_roi = frame[:, :offset_x]
                if new_roi.shape[1] > 0:
                    self.draw_next_level_preview(new_roi, self.width - offset_x)
        
        # Draw transition progress
        cv2.putText(frame, f"Level {self.current_level}", 
                   (self.width//2 - 50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    def draw_current_level(self, roi, offset_x):
        """Draw current level to specified area"""
        # Simplified processing here, draw some basic elements
        height, width = roi.shape[:2]
        
        # Draw ground
        cv2.rectangle(roi, (0, height - 50), (width, height), (34, 139, 34), -1)
        
        # Draw some targets as indication
        for i, target in enumerate(self.targets):
            if not target.is_destroyed:
                x = int(target.x + offset_x)
                y = int(target.y)
                if 0 <= x < width:
                    cv2.circle(roi, (x, y), target.radius, (0, 255, 0), -1)
    
    def draw_next_level_preview(self, roi, offset_x):
        """Draw next level preview"""
        height, width = roi.shape[:2]
        
        # Draw ground
        cv2.rectangle(roi, (0, height - 50), (width, height), (34, 139, 34), -1)
        
        # Draw "Next Level" text
        cv2.putText(roi, f"LEVEL {self.current_level}", 
                   (offset_x + 10, height//2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
    
    def draw_ui(self, frame):
        """Draw user interface"""
        # Status background (expanded to show level info)
        cv2.rectangle(frame, (5, 5), (300, 100), (0, 0, 0), -1)
        
        # Status text
        status = "PULLING" if self.pulling else ("FLYING" if self.bird.is_flying else "READY")
        cv2.putText(frame, f"Status: {status}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Score: {self.score}", (10, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Level info
        cv2.putText(frame, f"Level: {self.current_level}/{self.max_level}", (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
        
        # Target count
        remaining = sum(1 for target in self.targets if not target.is_destroyed)
        cv2.putText(frame, f"Targets: {remaining}", (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Draw restart button
        button = self.reset_button
        
        # Button color changes based on state
        if button['has_triggered']:
            # Triggered state - green, indicates completed
            button_color = (0, 200, 0)  # Green, triggered
            text_color = (255, 255, 255)
        elif button['active']:
            button_color = (0, 200, 255)  # Bright blue, activating
            text_color = (255, 255, 255)
        elif button['hover']:
            button_color = (0, 150, 255)  # Blue, hovering
            text_color = (255, 255, 255)
        else:
            button_color = (100, 100, 100)  # Gray, normal state
            text_color = (255, 255, 255)
        
        # Draw button background
        cv2.rectangle(frame, 
                     (button['x'], button['y']), 
                     (button['x'] + button['width'], button['y'] + button['height']), 
                     button_color, -1)
        
        # Draw progress bar (if there's progress)
        if button['progress'] > 0:
            progress_ratio = button['progress'] / button['max_progress']
            progress_width = int(button['width'] * progress_ratio)
            
            # Progress bar color: from yellow to green
            if progress_ratio < 0.5:
                # Yellow to orange
                progress_color = (0, int(255 * progress_ratio * 2), 255)
            else:
                # Orange to green
                progress_color = (0, 255, int(255 * (2 - progress_ratio * 2)))
            
            # Draw progress bar
            cv2.rectangle(frame,
                         (button['x'], button['y'] + button['height'] - 8),
                         (button['x'] + progress_width, button['y'] + button['height']),
                         progress_color, -1)
            
            # Draw progress percentage
            progress_text = f"{int(progress_ratio * 100)}%"
            cv2.putText(frame, progress_text,
                       (button['x'] + button['width'] + 10, button['y'] + 25),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, progress_color, 2)
        
        # Draw button border
        cv2.rectangle(frame, 
                     (button['x'], button['y']), 
                     (button['x'] + button['width'], button['y'] + button['height']), 
                     (255, 255, 255), 2)
        
        # Draw button text
        if button['has_triggered']:
            # Show completed state
            cv2.putText(frame, "DONE", 
                       (button['x'] + 25, button['y'] + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
            # Add hint text
            cv2.putText(frame, "Leave to reset", 
                       (button['x'] + 5, button['y'] + button['height'] + 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)
        else:
            cv2.putText(frame, "RESTART", 
                       (button['x'] + 15, button['y'] + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, text_color, 2)
        
        # Draw expanded detection area (semi-transparent) - only show when not triggered
        if (button['hover'] or button['active']) and not button['has_triggered']:
            padding = button['detection_padding']
            overlay = frame.copy()
            # Draw expanded area border
            cv2.rectangle(overlay,
                         (button['x'] - padding, button['y'] - padding),
                         (button['x'] + button['width'] + padding, button['y'] + button['height'] + padding),
                         (0, 255, 255), 2)  # Cyan border
            # Semi-transparent effect
            cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
            
            # Add hint text
            cv2.putText(frame, "Extended Area", 
                       (button['x'] - padding, button['y'] - padding - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)
        
        # Victory message
        if self.game_won:
            cv2.rectangle(frame, (self.width//2 - 100, self.height//2 - 30), 
                         (self.width//2 + 100, self.height//2 + 30), (0, 255, 0), -1)
            cv2.putText(frame, "YOU WIN!", (self.width//2 - 80, self.height//2 + 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
        
        # Pause state display
        if self.is_paused:
            # Draw semi-transparent overlay
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (self.width, self.height), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
            
            # Draw pause symbol
            cv2.rectangle(frame, (self.width//2 - 150, self.height//2 - 60), 
                         (self.width//2 + 150, self.height//2 + 60), (255, 255, 255), -1)
            cv2.rectangle(frame, (self.width//2 - 150, self.height//2 - 60), 
                         (self.width//2 + 150, self.height//2 + 60), (0, 0, 255), 3)
            
            # Pause text
            cv2.putText(frame, "GAME PAUSED", (self.width//2 - 120, self.height//2 - 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3)
            cv2.putText(frame, "Release fist to continue", (self.width//2 - 140, self.height//2 + 20), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
        
        # Pause state change message (brief display)
        elif self.pause_message_timer > 0:
            if self.pause_message_timer > 30:  # Message when pausing
                cv2.putText(frame, "GAME RESUMED", (self.width//2 - 100, self.height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            else:  # Message when resuming
                cv2.putText(frame, "GAME RESUMED", (self.width//2 - 100, self.height//2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)

# Global game instance
game = None

def detect_pinch(hand_landmarks, width, height):
    """Detect pinch gesture"""
    if not hand_landmarks:
        return False, (0, 0), 0
    
    # Thumb tip and index finger tip
    thumb_tip = hand_landmarks.landmark[4]
    index_tip = hand_landmarks.landmark[8]
    
    # Calculate distance
    thumb_x = thumb_tip.x * width
    thumb_y = thumb_tip.y * height
    index_x = index_tip.x * width
    index_y = index_tip.y * height
    
    distance = math.sqrt((thumb_x - index_x)**2 + (thumb_y - index_y)**2)
    
    # Pinch center point
    center_x = (thumb_x + index_x) / 2
    center_y = (thumb_y + index_y) / 2
    
    # Check if pinching (distance less than 40 pixels)
    is_pinching = distance < 40
    
    return is_pinching, (center_x, center_y), distance

def detect_pointing(hand_landmarks, width, height):
    """Detect pointing gesture"""
    if not hand_landmarks:
        return False, (0, 0)
    
    landmarks = hand_landmarks.landmark
    
    # Detect finger states
    fingers_up = []
    
    # Thumb - improved detection logic
    thumb_tip = landmarks[4]
    thumb_mcp = landmarks[2]
    if abs(thumb_tip.x - thumb_mcp.x) > 0.02:  # Whether thumb is extended (more relaxed condition)
        fingers_up.append(1)
    else:
        fingers_up.append(0)
    
    # Other four fingers (compare y coordinates)
    finger_tips = [8, 12, 16, 20]  # Index, middle, ring, pinky finger tips
    finger_pips = [6, 10, 14, 18]  # Corresponding PIP joints
    
    for tip, pip in zip(finger_tips, finger_pips):
        if landmarks[tip].y < landmarks[pip].y:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
    
    # More relaxed pointing gesture detection: index up, at least 2 other fingers down
    index_up = fingers_up[1] == 1  # Index finger up
    other_fingers_down = sum(fingers_up[2:]) <= 1  # Middle, ring, pinky: at most 1 up
    
    is_pointing = index_up and other_fingers_down
    
    # Get index finger tip position
    index_tip = landmarks[8]
    point_x = index_tip.x * width
    point_y = index_tip.y * height
    
    return is_pointing, (point_x, point_y)

def detect_left_swipe(hand_landmarks, width, height):
    """Detect left swipe gesture"""
    if not hand_landmarks:
        return False, (0, 0)
    
    # Get wrist and middle finger tip positions
    wrist = hand_landmarks.landmark[0]
    middle_tip = hand_landmarks.landmark[12]
    
    wrist_x = wrist.x * width
    middle_x = middle_tip.x * width
    
    # Detect open palm (multiple fingers extended)
    landmarks = hand_landmarks.landmark
    fingers_up = []
    
    # Thumb
    if landmarks[4].x > landmarks[3].x:
        fingers_up.append(1)
    else:
        fingers_up.append(0)
    
    # Other four fingers
    finger_tips = [8, 12, 16, 20]
    finger_pips = [6, 10, 14, 18]
    
    for tip, pip in zip(finger_tips, finger_pips):
        if landmarks[tip].y < landmarks[pip].y:
            fingers_up.append(1)
        else:
            fingers_up.append(0)
    
    # At least 3 fingers extended indicates open palm
    open_palm = sum(fingers_up) >= 3
    
    # Middle finger tip far left of wrist (extended left)
    is_left_extended = middle_x < wrist_x - 50
    
    swipe_center_x = (wrist_x + middle_x) / 2
    swipe_center_y = (wrist.y + middle_tip.y) / 2 * height
    
    return open_palm and is_left_extended, (swipe_center_x, swipe_center_y)

def detect_fist(hand_landmarks):
    """Detect fist gesture - improved version with stricter detection"""
    if not hand_landmarks:
        return False
    
    landmarks = hand_landmarks.landmark
    
    # Get palm center point (midpoint of wrist and middle finger MCP joint)
    wrist = landmarks[0]
    middle_mcp = landmarks[9]
    palm_center_x = (wrist.x + middle_mcp.x) / 2
    palm_center_y = (wrist.y + middle_mcp.y) / 2
    
    # Check if all fingers are bent and close to palm
    fingers_properly_bent = []
    
    # Thumb: stricter detection
    thumb_tip = landmarks[4]
    thumb_ip = landmarks[3]
    thumb_mcp = landmarks[2]
    
    # Thumb bent: tip to palm center distance less than MCP to palm center distance
    thumb_to_palm_dist = ((thumb_tip.x - palm_center_x)**2 + (thumb_tip.y - palm_center_y)**2)**0.5
    thumb_mcp_to_palm_dist = ((thumb_mcp.x - palm_center_x)**2 + (thumb_mcp.y - palm_center_y)**2)**0.5
    thumb_bent = thumb_to_palm_dist < thumb_mcp_to_palm_dist * 0.95  # Relaxed from 90% to 95%
    fingers_properly_bent.append(thumb_bent)
    
    # Other four fingers: stricter bending + distance detection
    finger_tips = [8, 12, 16, 20]  # Index, middle, ring, pinky finger tips
    finger_pips = [6, 10, 14, 18]  # Corresponding PIP joints
    finger_mcps = [5, 9, 13, 17]   # Corresponding MCP joints
    
    for tip_idx, pip_idx, mcp_idx in zip(finger_tips, finger_pips, finger_mcps):
        # Condition 1: fingertip below PIP joint (basic bending)
        basic_bent = landmarks[tip_idx].y > landmarks[pip_idx].y
        
        # Condition 2: fingertip to palm center distance less than 90% of MCP to palm center distance (relaxed by 5%)
        tip_to_palm_dist = ((landmarks[tip_idx].x - palm_center_x)**2 + 
                           (landmarks[tip_idx].y - palm_center_y)**2)**0.5
        mcp_to_palm_dist = ((landmarks[mcp_idx].x - palm_center_x)**2 + 
                           (landmarks[mcp_idx].y - palm_center_y)**2)**0.5
        close_to_palm = tip_to_palm_dist < mcp_to_palm_dist * 0.9  # Relaxed from 85% to 90%
        
        # Both conditions must be met for proper bending
        finger_properly_bent = basic_bent and close_to_palm
        fingers_properly_bent.append(finger_properly_bent)
    
    # Relaxed requirement: at least 4 fingers properly bent (instead of 5)
    most_fingers_bent = sum(fingers_properly_bent) >= 4
    
    # Additional check: finger proximity (optional, stricter)
    # Check if adjacent fingertips are close enough together
    finger_tips_coords = [(landmarks[tip_idx].x, landmarks[tip_idx].y) for tip_idx in finger_tips]
    max_finger_distance = 0
    for i in range(len(finger_tips_coords) - 1):
        dist = ((finger_tips_coords[i][0] - finger_tips_coords[i+1][0])**2 + 
                (finger_tips_coords[i][1] - finger_tips_coords[i+1][1])**2)**0.5
        max_finger_distance = max(max_finger_distance, dist)
    
    # Finger distance should not be too large (relative to palm size)
    hand_size = ((wrist.x - middle_mcp.x)**2 + (wrist.y - middle_mcp.y)**2)**0.5
    fingers_close_together = max_finger_distance < hand_size * 0.5  # Relaxed to 50% of palm size
    
    # Final decision: most fingers bent and fingers close together
    fist_detected = most_fingers_bent and fingers_close_together
    
    return fist_detected

# Global variables - wave detection
swipe_history = []

# Global variables - fist detection stability
fist_history = []

# Global variables - fist detection stability
fist_history = []

def update_fist_detection(is_fist_detected):
    """Update fist detection history for stability check"""
    global fist_history
    
    # Keep record of recent 3 frames (reduced requirement)
    fist_history.append(is_fist_detected)
    if len(fist_history) > 3:
        fist_history.pop(0)
    
    # Need 2+ consecutive frames detecting fist to confirm (lowered requirement)
    if len(fist_history) >= 2:
        recent_fists = fist_history[-2:]
        consecutive_fists = sum(1 for fist in recent_fists if fist)
        # If 1+ frames in recent 2 frames detected fist, confirm fist state
        return consecutive_fists >= 1
    
    return is_fist_detected  # If history insufficient, return current detection result

def update_swipe_detection(is_swiping, position):
    """Update swipe detection history"""
    global swipe_history
    
    # Keep record of recent 10 frames
    swipe_history.append((is_swiping, position))
    if len(swipe_history) > 10:
        swipe_history.pop(0)
    
    # Detect continuous left swipe
    if len(swipe_history) >= 5:
        recent_swipes = swipe_history[-5:]
        consecutive_swipes = sum(1 for swipe, pos in recent_swipes if swipe)
        
        # If 3+ frames in recent 5 frames detected swipe, trigger transition
        return consecutive_swipes >= 3
    
    return False

def video_frame_callback(frame):
    """Process video frames"""
    global game
    
    try:
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        height, width = img.shape[:2]
        
        # Initialize game
        if game is None:
            game = SimpleGame(width, height)
        
        # Gesture detection
        hands = get_hand_detector()
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_img)
        
        # Process gestures
        is_pinching = False
        pinch_center = (0, 0)
        pinch_distance = 0
        is_pointing = False
        point_position = (0, 0)
        is_swiping = False
        swipe_position = (0, 0)
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw hand landmarks
                mp_drawing.draw_landmarks(img, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Detect pinch
                pinching, center, distance = detect_pinch(hand_landmarks, width, height)
                if pinching:
                    is_pinching = True
                    pinch_center = center
                    pinch_distance = distance
                    
                    # Draw pinch point
                    cv2.circle(img, (int(center[0]), int(center[1])), 15, (0, 255, 0), -1)
                    cv2.circle(img, (int(center[0]), int(center[1])), 20, (255, 255, 255), 2)
                    cv2.putText(img, f"PINCH: {distance:.1f}", (int(center[0]) + 25, int(center[1])), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                # Detect pointing
                pointing, point_pos = detect_pointing(hand_landmarks, width, height)
                if pointing:
                    is_pointing = True
                    point_position = point_pos
                    
                    # Draw pointing point
                    cv2.circle(img, (int(point_pos[0]), int(point_pos[1])), 10, (255, 0, 0), -1)
                    cv2.circle(img, (int(point_pos[0]), int(point_pos[1])), 15, (255, 255, 255), 2)
                    cv2.putText(img, "POINT", (int(point_pos[0]) + 20, int(point_pos[1])), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                    
                    # Check button hover
                    game.check_button_hover(point_pos[0], point_pos[1])
                
                # Detect left swipe
                swiping, swipe_pos = detect_left_swipe(hand_landmarks, width, height)
                if swiping:
                    is_swiping = True
                    swipe_position = swipe_pos
                    
                    # Draw swipe hint
                    cv2.circle(img, (int(swipe_pos[0]), int(swipe_pos[1])), 20, (255, 255, 0), -1)
                    cv2.circle(img, (int(swipe_pos[0]), int(swipe_pos[1])), 25, (255, 255, 255), 2)
                    cv2.putText(img, "SWIPE LEFT", (int(swipe_pos[0]) + 30, int(swipe_pos[1])), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                
                # Detect fist - using improved algorithm and stability check
                raw_fist_detected = detect_fist(hand_landmarks)
                stable_fist_detected = update_fist_detection(raw_fist_detected)
                
                if stable_fist_detected:
                    # Update game's fist state
                    game.fist_detected = True
                    
                    # Draw fist hint
                    wrist = hand_landmarks.landmark[0]
                    fist_x = int(wrist.x * width)
                    fist_y = int(wrist.y * height)
                    cv2.circle(img, (fist_x, fist_y), 25, (0, 0, 255), -1)
                    cv2.circle(img, (fist_x, fist_y), 30, (255, 255, 255), 2)
                    cv2.putText(img, "FIST - PAUSE", (fist_x + 35, fist_y), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                else:
                    game.fist_detected = False
        
        # Pause state management
        game.update_pause_state()
        
        # Game logic - only execute when not paused
        if not game.is_paused:
            if is_pinching and not game.pulling:
                game.start_pull(pinch_center[0], pinch_center[1])
            elif is_pinching and game.pulling:
                game.update_pull(pinch_center[0], pinch_center[1])
            elif not is_pinching and game.pulling:
                game.release()
        
            # Button progress detection
            if is_pointing:
                # Check button hover and update progress
                game_reset = game.check_button_hover(point_position[0], point_position[1])
                if game_reset:
                    # Show restart confirmation message
                    cv2.putText(img, "GAME RESET!", (width//2 - 100, height//2), 
                               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
            else:
                # Not in pointing state, let button progress decay
                game.check_button_hover(-1, -1)  # Pass invalid coordinates to decay progress
        
        # Fallback activation mechanism: if no hands detected but game inactive for long time, show restart hint
        if not results.multi_hand_landmarks:
            # No hands detected
            cv2.putText(img, "No hands detected - Try moving closer to camera", 
                       (10, height - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
            cv2.putText(img, "Or use spacebar to restart", 
                       (10, height - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        
        # Swipe detection - level switching
        level_switched = update_swipe_detection(is_swiping, swipe_position)
        if level_switched and game.game_won and not game.is_transitioning:
            # Only switch level when won and not in transition animation
            if game.current_level < game.max_level:
                game.next_level()
                cv2.putText(img, f"NEXT LEVEL! ({game.current_level})", 
                           (width//2 - 120, height//2 + 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 3)
            else:
                cv2.putText(img, "ALL LEVELS COMPLETED!", 
                           (width//2 - 150, height//2 + 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 3)
        
        # Show swipe hint (only when won)
        if game.game_won and not game.is_transitioning and game.current_level < game.max_level:
            cv2.putText(img, "Swipe LEFT for next level!", 
                       (width//2 - 150, height - 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
        
        pointing_last_frame = is_pointing
        
        # Update and draw game - only update game logic when not paused
        if not game.is_paused:
            game.update()
        game.draw(img)
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")
    
    except Exception as e:
        # Error handling
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        cv2.putText(img, f"Error: {str(e)}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

def main():
    """Main function"""
    st.set_page_config(
        page_title="Angry \"Balls\"",
        page_icon="🎮",
        layout="wide"
    )
    
    st.title("🎮 Angry \"Balls\"")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Game Control")
        
        # Reset button
        if st.button("🔄 Reset Game", use_container_width=True):
            global game
            if game:
                game.reset_game()
            st.success("Game Reset!")
        
        st.markdown("---")
        
        st.header("🕹️ Controls")
        st.markdown("""
        **Gesture Controls:**
        - 🤏 **Pinch Gesture**: Two fingers close to bird
        - 🎯 **Drag & Aim**: Drag to adjust angle and power
        - 🚀 **Release to Shoot**: Release fingers to launch bird
        - 👆 **Point Gesture**: Index finger extended alone
        - 🔄 **Progress Restart**: Point at left RESTART button, auto restart when progress bar fills
        - 👋 **Swipe to Switch**: Swipe left after winning to next level
        - ✊ **Fist Pause**: Make fist to pause game, release to continue
        - 🎯 **Game Objective**: Hit all green targets to win
        """)
        
        st.warning("""🚨 **Restart Mechanism**: 
        - Point at RESTART button and hold for 1 second to activate restart
        - Button turns green showing "DONE" after completion
        - Need to move finger away from button area before next use
        - This design prevents repeated triggering from prolonged hovering""")
        
        st.success("""✊ **Fist Pause Instructions**: 
        - 💪 **Strict Detection**: Requires all 5 fingers bent and close to palm center
        - 🎯 **Distance Constraint**: Fingertips must be close enough to palm to avoid loose gesture triggers
        - ⏱️ **Stability Check**: Continuous frames of fist detection required for confirmation, reducing false positives
        - ⏸️ **Instant Pause**: Game pauses immediately upon confirmed fist, shows semi-transparent pause interface
        - ▶️ **Instant Resume**: Game resumes immediately when fist is released, briefly shows "GAME RESUMED" message
        - 🔒 **Complete Pause**: All game logic stops during pause, including bird flight and collision detection""")
    
    # Main interface
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.header("📹 Game Screen")
        
        # WebRTC configuration
        RTC_CONFIGURATION = RTCConfiguration({
            "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
        })
        
        # WebRTC stream
        webrtc_streamer(
            key="gesture-angry-birds-simple",
            mode=WebRtcMode.SENDRECV,
            rtc_configuration=RTC_CONFIGURATION,
            video_frame_callback=video_frame_callback,
            media_stream_constraints={"video": True, "audio": False}
        )
    
    with col2:
        st.header("🎨 Visual Guide")
        st.markdown("""
        **Color Meanings:**
        - 🟡 Yellow: Player
        - 🟢 Green Circle: Pinch detection point
        - 🟢 Green: Target
        - 🔴 Red Line: Slingshot band
        - 🟤 Brown: Slingshot frame
        - 🟢 Semi-transparent: Ground
        """)
        
        st.markdown("---")
        
        st.header("⚙️ Technical Features")
        st.markdown("""
        - **MediaPipe Gesture Recognition**
        - **Real-time Physics Simulation**
        - **Collision Detection System**
        - **Flight Trajectory Display**
        """)
        
        st.markdown("---")
        
        st.header("💡 Game Tips")
        st.markdown("""
        - Pull farther for more power
        - Consider gravity's effect on trajectory
        - Aim above the target
        - Keep gestures stable
        """)

if __name__ == "__main__":
    main()