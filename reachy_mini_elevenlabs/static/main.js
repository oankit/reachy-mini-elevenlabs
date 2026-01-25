/**
 * ElevenLabs Settings UI - Main JavaScript
 * 
 * Handles configuration of ElevenLabs API key and Agent ID
 * for the Reachy Mini ElevenLabs conversation app.
 */

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function fetchWithTimeout(url, options = {}, timeoutMs = 2000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(id);
  }
}

async function fetchStatus() {
  try {
    const url = new URL("/status", window.location.origin);
    url.searchParams.set("_", Date.now().toString());
    const resp = await fetchWithTimeout(url, {}, 2000);
    if (!resp.ok) throw new Error("status error");
    return await resp.json();
  } catch (e) {
    return { 
      has_api_key: false, 
      has_agent_id: false, 
      enable_emotion_detection: true,
      enable_idle_emotions: true,
      emotion_confidence_threshold: 0.3,
      emotion_cooldown_seconds: 3.0,
      idle_emotion_min_delay: 3.0,
      idle_emotion_max_delay: 8.0,
      error: true 
    };
  }
}

async function waitForStatus(timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (true) {
    try {
      const url = new URL("/status", window.location.origin);
      url.searchParams.set("_", Date.now().toString());
      const resp = await fetchWithTimeout(url, {}, 2000);
      if (resp.ok) return await resp.json();
    } catch (e) {}
    if (Date.now() >= deadline) return null;
    await sleep(500);
  }
}

async function saveConfig(apiKey, agentId) {
  const body = { 
    elevenlabs_api_key: apiKey,
    elevenlabs_agent_id: agentId
  };
  const resp = await fetch("/elevenlabs_config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.error || "save_failed");
  }
  return await resp.json();
}

async function saveEmotionConfig(config) {
  const resp = await fetch("/emotion_config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.error || "save_failed");
  }
  return await resp.json();
}

function show(el, flag) {
  el.classList.toggle("hidden", !flag);
}

async function init() {
  const loading = document.getElementById("loading");
  show(loading, true);
  
  const statusEl = document.getElementById("status");
  const formPanel = document.getElementById("form-panel");
  const configuredPanel = document.getElementById("configured");
  const emotionPanel = document.getElementById("emotion-panel");
  const saveBtn = document.getElementById("save-btn");
  const changeConfigBtn = document.getElementById("change-config-btn");
  const apiKeyInput = document.getElementById("api-key");
  const agentIdInput = document.getElementById("agent-id");

  // Emotion controls
  const saveEmotionBtn = document.getElementById("save-emotion-btn");
  const emotionStatusEl = document.getElementById("emotion-status");
  const enableEmotionDetection = document.getElementById("enable-emotion-detection");
  const enableIdleEmotions = document.getElementById("enable-idle-emotions");
  const confidenceThreshold = document.getElementById("confidence-threshold");
  const confidenceValue = document.getElementById("confidence-value");
  const cooldownSeconds = document.getElementById("cooldown-seconds");
  const cooldownValue = document.getElementById("cooldown-value");
  const idleMinDelay = document.getElementById("idle-min-delay");
  const idleMinValue = document.getElementById("idle-min-value");
  const idleMaxDelay = document.getElementById("idle-max-delay");
  const idleMaxValue = document.getElementById("idle-max-value");

  statusEl.textContent = "Checking configuration...";
  show(formPanel, false);
  show(configuredPanel, false);
  show(emotionPanel, false);

  const st = (await waitForStatus()) || { 
    has_api_key: false, 
    has_agent_id: false,
    api_key_display: "",
    agent_id_display: "",
    enable_emotion_detection: true,
    enable_idle_emotions: true,
    emotion_confidence_threshold: 0.3,
    emotion_cooldown_seconds: 3.0,
    idle_emotion_min_delay: 3.0,
    idle_emotion_max_delay: 8.0,
  };
  
  // Check if Agent ID is configured (API key is optional)
  const isConfigured = st.has_agent_id;
  
  if (isConfigured) {
    statusEl.textContent = "";
    show(configuredPanel, true);
    show(emotionPanel, true);
    
    // Display current credentials
    const displayAgentId = document.getElementById("display-agent-id");
    const displayApiKey = document.getElementById("display-api-key");
    if (displayAgentId) {
      displayAgentId.textContent = st.agent_id_display || "—";
    }
    if (displayApiKey) {
      displayApiKey.textContent = st.api_key_display || "Not set";
    }
  } else {
    statusEl.textContent = "";
    show(formPanel, true);
  }

  // Initialize emotion controls with current values
  enableEmotionDetection.checked = st.enable_emotion_detection;
  enableIdleEmotions.checked = st.enable_idle_emotions;
  confidenceThreshold.value = st.emotion_confidence_threshold;
  confidenceValue.textContent = st.emotion_confidence_threshold.toFixed(2);
  cooldownSeconds.value = st.emotion_cooldown_seconds;
  cooldownValue.textContent = st.emotion_cooldown_seconds.toFixed(1) + "s";
  idleMinDelay.value = st.idle_emotion_min_delay;
  idleMinValue.textContent = st.idle_emotion_min_delay.toFixed(1) + "s";
  idleMaxDelay.value = st.idle_emotion_max_delay;
  idleMaxValue.textContent = st.idle_emotion_max_delay.toFixed(1) + "s";

  // Update slider value displays
  confidenceThreshold.addEventListener("input", (e) => {
    confidenceValue.textContent = parseFloat(e.target.value).toFixed(2);
  });
  cooldownSeconds.addEventListener("input", (e) => {
    cooldownValue.textContent = parseFloat(e.target.value).toFixed(1) + "s";
  });
  idleMinDelay.addEventListener("input", (e) => {
    idleMinValue.textContent = parseFloat(e.target.value).toFixed(1) + "s";
  });
  idleMaxDelay.addEventListener("input", (e) => {
    idleMaxValue.textContent = parseFloat(e.target.value).toFixed(1) + "s";
  });

  // Handler for "Change configuration" button
  changeConfigBtn.addEventListener("click", async () => {
    show(configuredPanel, false);
    show(emotionPanel, false);
    show(formPanel, true);
    
    // Pre-fill with current values
    const currentStatus = await fetchStatus();
    agentIdInput.value = currentStatus.agent_id_display || "";
    apiKeyInput.value = ""; // Don't pre-fill API key for security
    apiKeyInput.placeholder = currentStatus.has_api_key ? "Leave blank to keep current" : "sk_...";
    
    statusEl.textContent = "";
    statusEl.className = "status-message";
  });

  // Remove error styling when user starts typing
  apiKeyInput.addEventListener("input", () => {
    apiKeyInput.classList.remove("error");
  });
  agentIdInput.addEventListener("input", () => {
    agentIdInput.classList.remove("error");
  });

  saveBtn.addEventListener("click", async () => {
    const apiKey = apiKeyInput.value.trim();
    const agentId = agentIdInput.value.trim();
    
    // At least one field must be provided
    if (!apiKey && !agentId) {
      statusEl.textContent = "Please enter at least one field to update.";
      statusEl.className = "status-message warn";
      return;
    }
    
    statusEl.textContent = "Saving configuration...";
    statusEl.className = "status-message";
    apiKeyInput.classList.remove("error");
    agentIdInput.classList.remove("error");
    
    try {
      await saveConfig(apiKey, agentId);
      statusEl.textContent = "Configuration saved! Reloading…";
      statusEl.className = "status-message ok";
      
      // Reload after a short delay to show success message
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (e) {
      if (e.message === "agent_id_required_for_initial_setup") {
        agentIdInput.classList.add("error");
        statusEl.textContent = "Agent ID is required for initial setup.";
      } else if (e.message === "no_fields_provided") {
        statusEl.textContent = "Please enter at least one field to update.";
      } else {
        statusEl.textContent = "Failed to save configuration. Please try again.";
      }
      statusEl.className = "status-message error";
    }
  });

  // Save emotion configuration
  saveEmotionBtn.addEventListener("click", async () => {
    emotionStatusEl.textContent = "Saving emotion settings...";
    emotionStatusEl.className = "status-message";
    
    const config = {
      enable_emotion_detection: enableEmotionDetection.checked,
      enable_idle_emotions: enableIdleEmotions.checked,
      emotion_confidence_threshold: parseFloat(confidenceThreshold.value),
      emotion_cooldown_seconds: parseFloat(cooldownSeconds.value),
      idle_emotion_min_delay: parseFloat(idleMinDelay.value),
      idle_emotion_max_delay: parseFloat(idleMaxDelay.value),
    };
    
    try {
      await saveEmotionConfig(config);
      emotionStatusEl.textContent = "Emotion settings saved! Changes will apply on next restart.";
      emotionStatusEl.className = "status-message ok";
      
      // Clear success message after a few seconds
      setTimeout(() => {
        emotionStatusEl.textContent = "";
        emotionStatusEl.className = "status-message";
      }, 3000);
    } catch (e) {
      emotionStatusEl.textContent = "Failed to save emotion settings. Please try again.";
      emotionStatusEl.className = "status-message error";
    }
  });

  // Hide loading overlay
  show(loading, false);
}

window.addEventListener("DOMContentLoaded", init);
