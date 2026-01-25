# Quick Start: Emotion Detection

## What You Get

Your Reachy Mini robot now automatically responds to emotions in the agent's speech with expressive movements!

## How to Enable

### Option 1: Already Enabled by Default! 🎉

If you're using the latest version, emotion detection is already enabled with sensible defaults. Just start talking to your robot and watch it respond expressively!

### Option 2: Configure Settings (Optional)

Create or edit `.env` file in the `reachy_mini_elevenlabs` directory:

```bash
# Enable emotion detection (default: true)
ENABLE_EMOTION_DETECTION=true

# Sensitivity: 0.0 (very sensitive) to 1.0 (only strong emotions)
# Default: 0.3 (balanced)
EMOTION_CONFIDENCE_THRESHOLD=0.3

# Cooldown between movements in seconds
# Default: 3.0 (prevents constant movement)
EMOTION_COOLDOWN_SECONDS=3.0
```

## What Emotions Are Detected?

| Emotion | Agent Says | Robot Does |
|---------|-----------|------------|
| **Happy** | "I'm excited to help!" | Happy animation |
| **Sad** | "I'm sorry about that" | Sad expression |
| **Thinking** | "Hmm, let me think..." | Looks up |
| **Confused** | "I'm not sure..." | Tilts head |
| **Surprised** | "Wow! That's amazing!" | Looks up surprised |
| **Greeting** | "Hello! Welcome!" | Faces forward |

## Examples

### Example 1: Happy Response
**You:** "Can you help me?"  
**Agent:** "I'm so excited to help you today!"  
**Robot:** 🤖 *plays happy animation*

### Example 2: Apologetic
**You:** "That didn't work"  
**Agent:** "I'm sorry to hear that. Unfortunately, I can't help with that."  
**Robot:** 🤖 *shows sad expression*

### Example 3: Thinking
**You:** "What's the best approach?"  
**Agent:** "Hmm, let me think about that for a moment..."  
**Robot:** 🤖 *looks up thoughtfully*

## Adjusting Sensitivity

### Too Many Movements?
Make it less sensitive:
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.5  # Higher = less sensitive
EMOTION_COOLDOWN_SECONDS=5.0      # Longer cooldown
```

### Not Enough Movements?
Make it more sensitive:
```bash
EMOTION_CONFIDENCE_THRESHOLD=0.2  # Lower = more sensitive
EMOTION_COOLDOWN_SECONDS=2.0      # Shorter cooldown
```

### Disable Completely
```bash
ENABLE_EMOTION_DETECTION=false
```

## Checking If It's Working

Look for these log messages:
```
INFO reachy_mini_elevenlabs.elevenlabs_handler | Agent: I'm so excited!
INFO reachy_mini_elevenlabs.emotion_detector | Emotion detected: happy (confidence: 0.75) -> Action: play_emotion
```

If you don't see emotion detection logs, check:
1. Is `ENABLE_EMOTION_DETECTION=true` in your `.env`?
2. Is the agent using emotional language?
3. Is the confidence threshold too high?

## Tips for Best Results

1. **Use expressive agents** - Configure your ElevenLabs agent to use emotional language
2. **Start with defaults** - The default settings work well for most cases
3. **Adjust gradually** - Change one setting at a time to find your sweet spot
4. **Watch the logs** - They show exactly what emotions are detected

## Need More Help?

- Full documentation: [EMOTION_DETECTION.md](EMOTION_DETECTION.md)
- Implementation details: [EMOTION_DETECTION_IMPLEMENTATION.md](../EMOTION_DETECTION_IMPLEMENTATION.md)
- Report issues: [GitHub Discussions](https://huggingface.co/spaces/mindmodelai/reachy-mini-elevenlabs/discussions)

---

**Built by [mindmodel.ai](https://mindmodel.ai) & [ageai.io](https://ageai.io)**
