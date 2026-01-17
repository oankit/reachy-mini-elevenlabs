---
title: Reachy Mini ElevenLabs Conversation
emoji: 🤖💬
colorFrom: blue
colorTo: purple
sdk: static
pinned: false
license: apache-2.0
tags:
  - reachy-mini
  - elevenlabs
  - conversational-ai
  - robotics
  - voice-assistant
  - mindmodel
  - ageai
short_description: Natural voice conversations for Reachy Mini by mindmodel.ai
---

# 🤖💬 Reachy Mini ElevenLabs Conversation

**By [mindmodel.ai](https://mindmodel.ai) & [ageai.io](https://ageai.io)**

Transform your Reachy Mini into an intelligent conversational companion using ElevenLabs' advanced Conversational AI platform.

> 🌟 **Open source project** from the teams at [mindmodel.ai](https://mindmodel.ai) and [ageai.io](https://ageai.io) - building the future of AI-powered robotics.

## ✨ Features

- 🎙️ **Natural Voice Conversations** - Speak naturally with your robot using ElevenLabs' state-of-the-art speech recognition
- 🗣️ **Expressive Speech Synthesis** - High-quality, natural-sounding voice responses
- 🎭 **Animated Responses** - Synchronized head movements and lip-sync animations during conversation
- ⚙️ **Easy Configuration** - Simple web-based settings interface for agent setup
- 🔌 **One-Click Install** - Install directly from the Reachy Mini Control app

## 🎬 Demo

[Add a demo video or GIF here showing the robot having a conversation]

## 🚀 Quick Start

### 1. Install the App

From the Reachy Mini Control application:
1. Navigate to the **Apps** section
2. Find **"ElevenLabs Conversation"** in the app list
3. Click **Install**
4. Wait for installation to complete

### 2. Get Your ElevenLabs Agent

You'll need an ElevenLabs Conversational AI agent:

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Navigate to the [Conversational AI](https://elevenlabs.io/app/conversational-ai) section
3. Create a new agent or use an existing one
4. Copy your **Agent ID** (starts with `agent_`)
5. (Optional) Copy your **API Key** if using a private agent

### 3. Configure the App

1. Start the **ElevenLabs Conversation** app from Reachy Mini Control
2. Open the settings page at `http://localhost:7861/`
3. Enter your **Agent ID**
4. (Optional) Enter your **API Key** for private agents
5. Click **Save Settings**

### 4. Start Conversing!

Once configured, the app will automatically:
- Connect to your ElevenLabs agent
- Start listening through the robot's microphone
- Respond through the robot's speaker
- Animate the robot's head during speech

Just speak naturally to your Reachy Mini and it will respond!

## 🎯 Use Cases

- **Personal Assistant** - Schedule reminders, answer questions, control smart home devices
- **Educational Companion** - Interactive learning experiences for students
- **Customer Service** - Automated reception and information desk
- **Entertainment** - Storytelling, jokes, and interactive games
- **Accessibility** - Voice-controlled interface for users with mobility challenges

## ⚙️ Configuration Options

### Agent ID (Required)
Your ElevenLabs Conversational AI agent identifier. This determines the personality, voice, and capabilities of your robot.

### API Key (Optional)
Only required for private agents. Public agents can be used without an API key.

## 🛠️ Technical Details

### Audio Processing
- **Input**: Robot microphone at 44.1kHz (stereo) → resampled to 16kHz mono
- **Output**: ElevenLabs audio at 16kHz → played through robot speaker
- **Format**: 16-bit PCM audio for optimal quality

### Animation System
- **Lip Sync**: Real-time mouth animation synchronized with speech
- **Head Movements**: Natural head wobbling during conversation
- **Interruption Handling**: Smooth transitions when user interrupts the robot

### Supported Platforms
- ✅ Windows (Reachy Mini Control app)
- ✅ Linux (Reachy Mini Control app)
- ✅ Raspberry Pi (Reachy Mini Wireless)

## 📋 Requirements

- Reachy Mini robot (Lite or Wireless version)
- Internet connection for ElevenLabs API
- ElevenLabs account with Conversational AI agent
- Microphone and speaker (built into Reachy Mini)

## 🤝 Contributing

Contributions are welcome! This app is open source under the Apache 2.0 license.

**Developed by**: [mindmodel.ai](https://mindmodel.ai) & [ageai.io](https://ageai.io)

### Development Setup

```bash
# Clone the repository
git clone https://huggingface.co/spaces/mindmodel-ai/reachy_mini_elevenlabs
cd reachy_mini_elevenlabs

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

Visit [mindmodel.ai](https://mindmodel.ai) and [ageai.io](https://ageai.io) to learn more about our AI projects.

## 📝 License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- **[mindmodel.ai](https://mindmodel.ai)** - AI solutions and robotics innovation
- **[ageai.io](https://ageai.io)** - Advanced AI applications and research
- **Pollen Robotics** - For creating the amazing Reachy Mini platform
- **ElevenLabs** - For their powerful Conversational AI technology
- **Hugging Face** - For hosting and supporting the Reachy Mini ecosystem

## 🔗 Links

- **[mindmodel.ai](https://mindmodel.ai)** - Explore our AI solutions
- **[ageai.io](https://ageai.io)** - Advanced AI research and applications
- [ElevenLabs Conversational AI](https://elevenlabs.io/conversational-ai)
- [Reachy Mini Documentation](https://docs.pollen-robotics.com/sdk/reachy-mini/)
- [Reachy Mini Apps](https://huggingface.co/reachy-mini-apps)

## 💬 Support

- **Website**: [mindmodel.ai](https://mindmodel.ai) | [ageai.io](https://ageai.io)
- **Issues**: Report bugs or request features on the [GitHub repository](https://github.com/mindmodel-ai/reachy_mini_elevenlabs)
- **Community**: Join the [Reachy Mini Discord](https://discord.gg/pollen-robotics)

---

**Built with ❤️ by [mindmodel.ai](https://mindmodel.ai) & [ageai.io](https://ageai.io)**

*Empowering robots with natural conversation - open source, community-driven, and built for the future.*
