# 🎮 Angry "Balls"

A gesture-controlled Angry "Balls" game based on MediaPipe hand tracking, simplified and optimized to provide a stable and reliable gaming experience.

## 🚀 Quick Start

### Install Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Run the Game
```bash
# Run the game
streamlit run main.py
```

### Game Controls
1. 🤏 **Pinch Gesture**: Bring thumb and index finger close together
2. 🎯 **Aim**: Make pinch gesture near the bird
3. 🎮 **Drag**: Keep pinching while dragging to adjust angle and power
4. 🚀 **Launch**: Release fingers to launch the bird
5. 🎯 **Objective**: Hit all green targets

## 🎯 Game Features

### ✅ Implemented Features
- **Gesture Recognition**: Precise two-finger pinch detection
- **Physics Engine**: Gravity, air resistance, trajectory calculation
- **Collision Detection**: Accurate collision between bird and targets
- **Visual Feedback**: Flight trajectory, pinch point display
- **Game Logic**: Scoring system, victory conditions
- **Transparent Background**: See your own camera feed
- **Real-time Status**: Game state and statistics

### 🎨 Visual Elements
- 🟡 **Yellow Ball**: Main character, can be dragged and launched
- 🟢 **Green Ball**: Targets to hit
- 🟤 **Brown Slingshot**: Launch device
- 🔴 **Red Slingshot Band**: Shows power when stretched
- 🟢 **Green Circle**: Gesture detection point
- 🌟 **Yellow Trail**: Ball flight path
- 🟢 **Semi-transparent Ground**: Game boundary

## 🔧 Technical Architecture

### Core Class Structure
```python
SimpleBird      # Bird class - physics state and rendering
SimpleTarget    # Target class - collision detection
SimpleGame      # Game class - overall logic control
```

### Key Function Modules
- `detect_pinch()`: Gesture recognition algorithm
- `video_frame_callback()`: Video frame processing
- `game.update()`: Game state update
- `game.draw()`: Game rendering

## 📝 Update Log

### v1.5 - Stable Base Version
- v1.1 ✅ Basic gesture control
-      ✅ Physics engine
-      ✅ Collision detection
-      ✅ Transparent background, players can see themselves
- v1.2 ✅ Scoring system
-      ✅ Designed restart button interaction to improve accidental touch issues (changed from tap-to-restart to long-press required)
- v1.3 ✅ Added left swipe gesture to enter next level
- v1.4 ✅ Added fist pause gesture and adjusted detection thresholds

### Planned Updates
- v1.6: More level systems and balls with special abilities
- v1.7: Sound effects and animations
- v1.8: More advanced gesture controls

- v1.9: AI functionality integration
