import { defineStore } from "pinia";

import { DEFAULT_PAYLOADS } from "../data/defaultPayloads";
import { api } from "../services/api";

/**
 * @param {unknown} value
 * @returns {string}
 */
function prettyJson(value) {
  return JSON.stringify(value ?? {}, null, 2);
}

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    busy: false,
    message: "",
    messageType: "info",
    stats: {
      sources: 0,
      events: 0,
      jobs: 0,
      knowledge: 0
    },
    sources: [],
    sourceDetail: null,
    sourceVersions: [],
    sourceVersionDetail: null,
    knowledge: [],
    knowledgeDetail: null,
    events: [],
    jobs: [],
    searchMode: "text",
    searchQuery: "",
    searchResults: [],
    importKind: "webpage",
    importPayload: prettyJson(DEFAULT_PAYLOADS.webpage),
    uploadTitle: "",
    uploadOccurredAt: new Date().toISOString(),
    uploadFile: null
  }),
  actions: {
    /**
     * @param {string} message
     * @param {string} [type="info"]
     * @returns {void}
     */
    setMessage(message, type = "info") {
      this.message = message;
      this.messageType = type;
    },

    /**
     * @returns {Promise<void>}
     */
    async bootstrap() {
      await Promise.all([
        this.loadStats(),
        this.loadSources(),
        this.loadKnowledge(),
        this.loadEvents(),
        this.loadJobs()
      ]);
    },

    /**
     * @returns {Promise<void>}
     */
    async loadStats() {
      const [sources, events, jobs, knowledge] = await Promise.all([
        api.listSources(),
        api.listEvents(),
        api.listJobs(),
        api.listKnowledge()
      ]);
      this.stats.sources = sources.items.length;
      this.stats.events = events.items.length;
      this.stats.jobs = jobs.items.length;
      this.stats.knowledge = knowledge.items.length;
    },

    /**
     * @returns {Promise<void>}
     */
    async loadSources() {
      const data = await api.listSources();
      this.sources = data.items;
      if (data.items.length) {
        await this.selectSource(data.items[0].id);
        return;
      }
      this.sourceDetail = null;
      this.sourceVersions = [];
      this.sourceVersionDetail = null;
    },

    /**
     * @param {string} sourceId
     * @returns {Promise<void>}
     */
    async selectSource(sourceId) {
      this.sourceDetail = await api.getSource(sourceId);
      const versions = await api.listSourceVersions(sourceId);
      this.sourceVersions = versions.items;
      this.sourceVersionDetail = versions.items.length
        ? await api.getSourceVersion(versions.items[0].id)
        : null;
    },

    /**
     * @param {string} versionId
     * @returns {Promise<void>}
     */
    async selectSourceVersion(versionId) {
      this.sourceVersionDetail = await api.getSourceVersion(versionId);
    },

    /**
     * @returns {Promise<void>}
     */
    async loadKnowledge() {
      const data = await api.listKnowledge();
      this.knowledge = data.items;
      this.knowledgeDetail = data.items.length
        ? await api.getKnowledge(data.items[0].id)
        : null;
    },

    /**
     * @param {string} knowledgeId
     * @returns {Promise<void>}
     */
    async selectKnowledge(knowledgeId) {
      this.knowledgeDetail = await api.getKnowledge(knowledgeId);
    },

    /**
     * @returns {Promise<void>}
     */
    async loadEvents() {
      const data = await api.listEvents();
      this.events = data.items;
    },

    /**
     * @returns {Promise<void>}
     */
    async loadJobs() {
      const data = await api.listJobs();
      this.jobs = data.items;
    },

    /**
     * @returns {Promise<void>}
     */
    async runJobs() {
      this.busy = true;
      try {
        const result = await api.runJobs();
        this.setMessage(
          `任务执行完成：processed=${result.processed}, completed=${result.completed}, failed=${result.failed}`
        );
        await Promise.all([
          this.loadStats(),
          this.loadJobs(),
          this.loadKnowledge()
        ]);
      } catch (error) {
        this.setMessage(`任务执行失败：${error.message}`, "error");
      } finally {
        this.busy = false;
      }
    },

    /**
     * @returns {Promise<void>}
     */
    async runSearch() {
      if (!this.searchQuery.trim()) {
        this.setMessage("请输入搜索词。", "error");
        return;
      }
      this.busy = true;
      try {
        const data =
          this.searchMode === "semantic"
            ? await api.searchSemantic(this.searchQuery)
            : await api.searchText(this.searchQuery);
        this.searchResults = data.items;
        this.setMessage(`已返回 ${data.items.length} 条搜索结果。`);
      } catch (error) {
        this.setMessage(`搜索失败：${error.message}`, "error");
      } finally {
        this.busy = false;
      }
    },

    /**
     * @param {string} kind
     * @returns {void}
     */
    setImportKind(kind) {
      this.importKind = kind;
      this.importPayload = prettyJson(DEFAULT_PAYLOADS[kind]);
    },

    /**
     * @returns {Promise<void>}
     */
    async submitStructuredImport() {
      this.busy = true;
      try {
        const payload = JSON.parse(this.importPayload);
        const data = await api.ingestStructured(this.importKind, payload);
        this.setMessage(
          `导入成功：source=${data.source_item_id}, version=${data.source_version_id}`
        );
        await Promise.all([
          this.loadStats(),
          this.loadSources(),
          this.loadEvents(),
          this.loadJobs()
        ]);
      } catch (error) {
        this.setMessage(`导入失败：${error.message}`, "error");
      } finally {
        this.busy = false;
      }
    },

    /**
     * @returns {Promise<void>}
     */
    async submitUpload() {
      if (!this.uploadFile) {
        this.setMessage("请先选择一个文件。", "error");
        return;
      }
      this.busy = true;
      try {
        const formData = new FormData();
        formData.append("file", this.uploadFile);
        formData.append("title", this.uploadTitle || this.uploadFile.name);
        formData.append("occurred_at", this.uploadOccurredAt);
        formData.append("capture_method", "manual_upload");
        formData.append("device_context", "desktop.browser");
        const data = await api.ingestUpload(formData);
        this.setMessage(
          `文件上传成功：source=${data.source_item_id}, version=${data.source_version_id}`
        );
        this.uploadFile = null;
        this.uploadTitle = "";
        await Promise.all([
          this.loadStats(),
          this.loadSources(),
          this.loadEvents(),
          this.loadJobs()
        ]);
      } catch (error) {
        this.setMessage(`文件上传失败：${error.message}`, "error");
      } finally {
        this.busy = false;
      }
    }
  }
});
