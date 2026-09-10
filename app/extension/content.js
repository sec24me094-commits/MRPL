/**
 * ADA Workbench - Intranet Document & SOP Extractor
 * Operates purely client-side inside the local intranet tab.
 */

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "extract_document") {
    try {
      const title = (document.querySelector("h1")?.innerText || document.title || "Intranet Operating Standard").trim();
      
      // Target meaningful content containers if available
      const container = document.querySelector("article, main, .content, .document-body, #content") || document.body;
      let text = container ? container.innerText : document.body.innerText;
      
      // Clean excessive whitespace
      text = text.replace(/\n{3,}/g, "\n\n").trim();
      
      // Extract visible equipment tags
      const equipmentMatches = text.match(/\b([A-Z]{1,3}-\d{2,4}[A-Z]?)\b/g) || [];
      const uniqueEquipment = Array.from(new Set(equipmentMatches)).slice(0, 10);

      sendResponse({
        success: true,
        title: title,
        content: text,
        url: window.location.href,
        equipment: uniqueEquipment
      });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }
  return true;
});
