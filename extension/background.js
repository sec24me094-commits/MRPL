/**
 * ADA Workbench Browser Extension - Service Worker
 * Manages zero-egress local communication with ADA FastAPI Core on localhost:8000
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log("ADA Workbench Intranet RAG Extension initialized (Air-gap LAN Mode).");
});
