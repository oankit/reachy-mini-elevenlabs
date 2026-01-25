# Emotion Detection Feature

## Overview

The ElevenLabs conversation app now includes automatic emotion detection that analyzes the agent's text responses and triggers appropriate robot expressions and movements. This creates a more engaging and expressive conversational experience.

## How It Works

### Text Analysis
When the agent responds, the system analyzes the text for:
- **Emotion keywords** (e.g., "happy", "sad", "excited", "sorry")
- **Punctuation patterns** (e.g., "!!!", "...", "???")
- **Contextual cues** (e.g., "I'm so glad", "unfortunately")

### Confidence Scoring
Each detected emotion receives a confidence score (0.0 to 1.0) based on:
- Number of matching keywords
- Strength of patterns
- Keyword specificity (longer keywords = higher weight)

### Action Triggering
When an emotion is detected with sufficient confidence, the robot:
- Plays emotion animations (happy, sad, etc.)
- Moves its head (thinking, greeting, etc.)
- Queues movements through the existing MovementManager

## Supported Emotions

### Happy
**Triggers:** Positive keywords, exclamation marks, happy emojis
**Keywords:** happy, glad, great, wonderful, excellent, fantastic, excited, thrilled, delighted, pleased, joy, cheerful, awesome, amazing, perfect, love
**Action:** Plays "happy" emotion animation

### Sad
**Triggers:** Negative keywords, apologies, sad emojis
**Keywords:** sad, sorry, unfortunately, regret, apologize, disappointed, unhappy, upset, down, blue, gloomy
**Action:** Plays "sad" emotion animation

### Thinking
**Triggers:** Contemplative words, ellipsis, thinking emoji
**Keywords:** hmm, let me think, considering, analyzing, processing, evaluating, pondering, wondering, curious, interesting
**Action:** Moves head up (looking up while thinking)

### Confused
**Triggers:** Uncertainty words, multiple question marks
**Keywords:** confused, unclear, not sure, don't understand, puzzled, perplexed, baffled, uncertain, unsure
**Action:** Tilts head left

### Surprised
**Triggers:** Surprise words, multiple exclamation marks
**Keywords:** wow, oh, really, surprising, unexpected, amazing, incredible, unbelievable, astonishing, shocking
**Action:** Moves head up (looking up in surprise)

### Greeting
**Triggers:** Greeting words
**Keywords:** hello, hi, hey, greetings, good morning, good afternoon, good evening, welcome, howdy
**Action:** Faces forward (attentive greeting posture)

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Enable/disable emotion detection
ENABLE_EMOTION_DETECTION=true

# Minimum confidence threshold (0.0-1.0)
# Lower = more sensitive, Higher = only strong emotions
EMOTION_CONFIDENCE_THRESHOLD=0.3

# Cooldown between actions (seconds)
# Prevents constant movement from multiple emotions
EMOTION_COOLDOWN_SECONDS=3.0
```

### Runtime Configuration

You can also adjust settings programmatically:

```python
# Enable/disable
handler.emotion_detector.enable()
handler.emotion_detector.disable()

# Adjust sensitivity
handler.emotion_detector.set_confidence_threshold(0.5)  # Less sensitive

# Adjust cooldown
handler.emotion_detector.set_cooldown(5.0)  # 5 second cooldown
```

## Examples

### Example 1: Happy Response
**Agent says:** "I'm so excited to help you today!"
**Detection:** `happy` emotion with confidence ~0.7
**Robot action:** Plays happy emotion animation

### Example 2: Apologetic Response
**Agent says:** "I'm sorry, unfortunately I can't help with that."
**Detection:** `sad` emotion with confidence ~0.6
**Robot action:** Plays sad emotion animation

### Example 3: Thinking Response
**Agent says:** "Hmm, let me think about that for a moment..."
**Detection:** `thinking` emotion with confidence ~0.8
**Robot action:** Looks up (thinking pose)

### Example 4: Greeting
**Agent says:** "Hello! How can I help you today?"
**Detection:** `greeting` emotion with confidence ~0.5
**Robot action:** Faces forward (attentive)

## Tuning Recommendations

### For More Expressive Robot
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.2  # More sensitive
EMOTION_COOLDOWN_SECONDS=2.0      # Faster reactions
```

### For Subtle Expressions
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.5  # Less sensitive
EMOTION_COOLDOWN_SECONDS=5.0      # Slower reactions
```

### For Demonstration/Testing
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.1  # Very sensitive
EMOTION_COOLDOWN_SECONDS=0.5      # Rapid reactions
```

## Technical Details

### Architecture
- **EmotionDetector** class in `emotion_detector.py`
- Integrated into `ElevenLabsHandler._on_agent_response()` callback
- Uses existing `MovementManager` for action execution
- No external API calls (all processing is local)

### Performance
- Negligible CPU overhead (simple text pattern matching)
- No network latency (local processing)
- Non-blocking (actions queued asynchronously)

### Cooldown System
Prevents the robot from constantly moving when multiple emotions are detected in quick succession. The cooldown timer starts after an action is triggered.

### Confidence Calculation
```
confidence = (keyword_matches * keyword_weight + pattern_matches * pattern_weight) / total_matches
```

Normalized to 0.0-1.0 range, capped at 1.0.

## Limitations

### Current Limitations
1. **English only** - Emotion keywords are currently English-only
2. **No context memory** - Each response analyzed independently
3. **Simple pattern matching** - Not using ML/NLP models
4. **Fixed emotion set** - Limited to predefined emotions

### Future Enhancements
- Multi-language support
- Context-aware emotion detection
- ML-based sentiment analysis
- Custom emotion mappings
- User-defined emotion patterns

## Troubleshooting

### Robot Not Responding to Emotions

**Check logs for emotion detection:**
```
INFO reachy_mini_elevenlabs.elevenlabs_handler:237 | Agent: I'm so happy!
INFO reachy_mini_elevenlabs.emotion_detector:XXX | Emotion detected: happy (confidence: 0.75) -> Action: play_emotion
```

**Common issues:**
1. **Emotion detection disabled** - Check `ENABLE_EMOTION_DETECTION=true`
2. **Confidence too low** - Lower `EMOTION_CONFIDENCE_THRESHOLD`
3. **In cooldown period** - Wait or reduce `EMOTION_COOLDOWN_SECONDS`
4. **Movement manager not initialized** - Check robot connection

### Too Many Movements

**Solution:** Increase cooldown or confidence threshold
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.5
EMOTION_COOLDOWN_SECONDS=5.0
```

### Not Enough Movements

**Solution:** Decrease confidence threshold
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.2
```

## Testing

Run the emotion detection tests:

```bash
pytest tests/test_emotion_detector.py -v
```

Test specific emotions:
```bash
pytest tests/test_emotion_detector.py::test_detect_happy_emotion -v
```

## Contributing

To add new emotions:

1. Add emotion pattern to `EMOTION_PATTERNS` in `emotion_detector.py`
2. Define keywords, patterns, and action
3. Add test case in `test_emotion_detector.py`
4. Update this documentation

Example:
```python
"angry": {
    "keywords": ["angry", "mad", "furious", "rage"],
    "patterns": [r"😠|😡"],
    "action": "play_emotion",
    "action_param": "angry",
}
```

## License

Apache 2.0 - Same as the main project
