# Attribution and Acknowledgments

This project builds upon and is inspired by the excellent work of Pollen Robotics and the open-source community.

## Derived Works

The following files contain code derived from the [reachy_mini_conversation_app](https://github.com/pollen-robotics/reachy_mini_conversation_app) project:

### 1. `reachy_mini_elevenlabs/moves.py`
**Original Source:** `reachy_mini_conversation_app/moves.py`  
**Copyright:** (c) Pollen Robotics  
**License:** Apache License 2.0  
**Modifications:** Adapted for ElevenLabs integration, added attribution header

**Description:** Movement system with sequential primary moves and additive secondary moves. Implements the MovementManager class that coordinates robot movements at 100Hz.

### 2. `reachy_mini_elevenlabs/dance_emotion_moves.py`
**Original Source:** `reachy_mini_conversation_app/dance_emotion_moves.py`  
**Copyright:** (c) Pollen Robotics  
**License:** Apache License 2.0  
**Modifications:** Copied for ElevenLabs integration, added attribution header

**Description:** Wrapper classes (DanceQueueMove, EmotionQueueMove, GotoQueueMove) that adapt dance and emotion moves to work with the MovementManager queue system.

### 3. Emotion Detection Approach
**Inspired by:** `reachy_mini_conversation_app/tools/play_emotion.py`  
**Copyright:** (c) Pollen Robotics  
**License:** Apache License 2.0  
**Modifications:** New implementation with text-based emotion detection, but uses the same emotion library and triggering mechanism

**Description:** The approach of using RecordedMoves from the "pollen-robotics/reachy-mini-emotions-library" and wrapping them in EmotionQueueMove objects is derived from the conversation app's play_emotion tool.

## Original Works

The following components are original contributions to this project:

### 1. `reachy_mini_elevenlabs/emotion_detector.py`
**Authors:** mindmodel.ai & ageai.io  
**License:** Apache License 2.0

**Description:** Text-based emotion detection system that analyzes agent responses for emotional content using keyword matching and pattern recognition. This is a new implementation not present in the original conversation app.

### 2. `reachy_mini_elevenlabs/elevenlabs_handler.py`
**Authors:** mindmodel.ai & ageai.io  
**License:** Apache License 2.0

**Description:** ElevenLabs Conversational AI integration with emotion detection callbacks.

### 3. `reachy_mini_elevenlabs/audio_interface.py`
**Authors:** mindmodel.ai & ageai.io  
**License:** Apache License 2.0

**Description:** Custom audio interface bridging ElevenLabs SDK with Reachy Mini hardware.

## Third-Party Libraries

This project uses the following third-party libraries:

- **ElevenLabs Python SDK** - ElevenLabs conversational AI integration
- **Reachy Mini SDK** - Pollen Robotics robot control
- **reachy-mini-emotions-library** - Pollen Robotics emotion animations
- **reachy-mini-dances-library** - Pollen Robotics dance moves

## License

This project is licensed under the Apache License 2.0, consistent with the original reachy_mini_conversation_app project.

```
Copyright 2025 mindmodel.ai & ageai.io

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

## Acknowledgments

Special thanks to:

- **Pollen Robotics** - For creating the Reachy Mini platform and open-sourcing the conversation app architecture
- **ElevenLabs** - For their powerful Conversational AI technology
- **Hugging Face** - For hosting the Reachy Mini ecosystem and emotion libraries
- **The Open Source Community** - For making collaborative robotics development possible

## Contact

- **Project**: [hf.mindmodel.ai](https://hf.mindmodel.ai)
- **mindmodel.ai**: [https://mindmodel.ai](https://mindmodel.ai)
- **ageai.io**: [https://ageai.io](https://ageai.io)

---

**Note:** If you use this code in your own projects, please maintain these attributions and comply with the Apache 2.0 license terms.
