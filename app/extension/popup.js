document.addEventListener("DOMContentLoaded", async () => {
  const titleInput = document.getElementById("docTitle");
  const contentInput = document.getElementById("docContent");
  const equipmentInput = document.getElementById("docEquipment");
  const roleSelect = document.getElementById("authorRole");
  const rbacKeyInput = document.getElementById("rbacKey");
  const pushBtn = document.getElementById("pushBtn");
  const statusArea = document.getElementById("statusArea");

  let activeTabUrl = "http://intranet.mrpl.local/sop";

  // Request extraction from content script
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.id) {
      activeTabUrl = tab.url || activeTabUrl;
      chrome.tabs.sendMessage(tab.id, { action: "extract_document" }, (response) => {
        if (chrome.runtime.lastError) {
          titleInput.value = tab.title || "Intranet Standard";
          contentInput.placeholder = "Unable to auto-extract from this page. Please paste text directly.";
          return;
        }
        if (response && response.success) {
          titleInput.value = response.title || "";
          contentInput.value = response.content || "";
          if (response.equipment && response.equipment.length) {
            equipmentInput.value = response.equipment.join(", ");
          }
        }
      });
    }
  } catch (err) {
    console.warn("Could not query active tab:", err);
  }

  pushBtn.addEventListener("click", async () => {
    const title = titleInput.value.trim();
    const content = contentInput.value.trim();
    const role = roleSelect.value;
    const rbacKey = rbacKeyInput.value.trim();
    const equipmentStr = equipmentInput.value.trim();
    const equipment = equipmentStr ? equipmentStr.split(",").map(s => s.trim()).filter(Boolean) : [];

    if (!title || !content) {
      alert("Please ensure both a Title and Content are provided.");
      return;
    }

    pushBtn.disabled = true;
    pushBtn.innerHTML = "<span>Syncing to Qdrant Core…</span>";
    statusArea.style.display = "none";
    statusArea.className = "status-area";

    try {
      const response = await fetch("http://localhost:8000/api/v1/rag/ingest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-ADA-RBAC-Key": rbacKey
        },
        body: JSON.stringify({
          title: title,
          content: content,
          source_url: activeTabUrl,
          author_role: role,
          auth_token: rbacKey,
          equipment: equipment
        })
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || `Server returned error ${response.status}`);
      }

      statusArea.className = "status-area status-success";
      statusArea.innerHTML = `
        <strong>✅ Ingestion Complete (100% Air-Gapped)</strong>
        <div><strong>SOP ID:</strong> ${data.sop_id}</div>
        <div><strong>Indexed:</strong> ${data.indexed_in_qdrant ? "Qdrant Vector DB" : "In-Memory Active RAG"}</div>
        <div><strong>SHA-256:</strong> ${data.sha256_digest.slice(0, 16)}…</div>
        <div><strong>PII Redacted:</strong> ${data.pii_redacted ? `Cleaned (${data.redaction_count} items)` : "Clean"}</div>
      `;
      statusArea.style.display = "block";
    } catch (err) {
      statusArea.className = "status-area status-error";
      statusArea.innerHTML = `
        <strong>❌ Ingestion Failed</strong>
        <div>${err.message || "Failed to connect to local ADA FastAPI on localhost:8000."}</div>
      `;
      statusArea.style.display = "block";
    } finally {
      pushBtn.disabled = false;
      pushBtn.innerHTML = "<span>🚀 Push to ADA RAG</span>";
    }
  });
});
