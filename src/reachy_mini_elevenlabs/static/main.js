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
    return { has_api_key: false, has_agent_id: false, error: true };
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

function show(el, flag) {
  el.classList.toggle("hidden", !flag);
}

async function init() {
  const loading = document.getElementById("loading");
  show(loading, true);
  
  const statusEl = document.getElementById("status");
  const formPanel = document.getElementById("form-panel");
  const configuredPanel = document.getElementById("configured");
  const saveBtn = document.getElementById("save-btn");
  const changeConfigBtn = document.getElementById("change-config-btn");
  const apiKeyInput = document.getElementById("api-key");
  const agentIdInput = document.getElementById("agent-id");

  statusEl.textContent = "Checking configuration...";
  show(formPanel, false);
  show(configuredPanel, false);

  const st = (await waitForStatus()) || { has_api_key: false, has_agent_id: false };
  
  // Check if Agent ID is configured (API key is optional)
  const isConfigured = st.has_agent_id;
  
  if (isConfigured) {
    statusEl.textContent = "";
    show(configuredPanel, true);
  } else {
    statusEl.textContent = "";
    show(formPanel, true);
  }

  // Handler for "Change configuration" button
  changeConfigBtn.addEventListener("click", () => {
    show(configuredPanel, false);
    show(formPanel, true);
    apiKeyInput.value = "";
    agentIdInput.value = "";
    statusEl.textContent = "";
    statusEl.className = "status";
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
    
    // Validate inputs - only Agent ID is required
    let hasError = false;
    
    if (!agentId) {
      agentIdInput.classList.add("error");
      hasError = true;
    }
    
    if (hasError) {
      statusEl.textContent = "Please enter your Agent ID.";
      statusEl.className = "status warn";
      return;
    }
    
    statusEl.textContent = "Saving configuration...";
    statusEl.className = "status";
    apiKeyInput.classList.remove("error");
    agentIdInput.classList.remove("error");
    
    try {
      await saveConfig(apiKey, agentId);
      statusEl.textContent = "Configuration saved! Reloading…";
      statusEl.className = "status ok";
      
      // Reload after a short delay to show success message
      setTimeout(() => {
        window.location.reload();
      }, 1000);
    } catch (e) {
      agentIdInput.classList.add("error");
      
      if (e.message === "empty_agent_id") {
        statusEl.textContent = "Agent ID cannot be empty.";
      } else {
        statusEl.textContent = "Failed to save configuration. Please try again.";
      }
      statusEl.className = "status error";
    }
  });

  // Hide loading overlay
  show(loading, false);
}

window.addEventListener("DOMContentLoaded", init);
