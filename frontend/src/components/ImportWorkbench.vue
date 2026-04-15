<script setup>
defineProps({
  importKind: { type: String, default: "webpage" },
  importPayload: { type: String, default: "" },
  uploadTitle: { type: String, default: "" },
  uploadOccurredAt: { type: String, default: "" },
  uploadFile: { type: Object, default: null },
  busy: { type: Boolean, default: false }
});

const emit = defineEmits([
  "update:importKind",
  "update:importPayload",
  "update:uploadTitle",
  "update:uploadOccurredAt",
  "update:uploadFile",
  "submit-structured",
  "submit-upload"
]);

/**
 * @param {Event} event
 * @returns {void}
 */
function onKindChange(event) {
  emit("update:importKind", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onPayloadInput(event) {
  emit("update:importPayload", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onTitleInput(event) {
  emit("update:uploadTitle", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onOccurredAtInput(event) {
  emit("update:uploadOccurredAt", event.target.value);
}

/**
 * @param {Event} event
 * @returns {void}
 */
function onFileChange(event) {
  const file = event.target.files?.[0] || null;
  emit("update:uploadFile", file);
}
</script>

<template>
  <section class="dual-grid">
    <article class="glass-card operations-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Structured Import</p>
          <h3>直接写入 ingest 接口</h3>
        </div>
      </div>

      <div class="composer-tools">
        <select :value="importKind" @change="onKindChange">
          <option value="webpage">webpage</option>
          <option value="bookmark">bookmark</option>
          <option value="search">search</option>
          <option value="chat">chat</option>
        </select>
        <button class="primary-button" :disabled="busy" @click="emit('submit-structured')">
          提交结构化导入
        </button>
      </div>

      <textarea
        :value="importPayload"
        rows="20"
        class="code-area"
        @input="onPayloadInput"
      />
    </article>

    <article class="glass-card operations-card">
      <div class="panel-heading">
        <div>
          <p class="eyebrow">Upload</p>
          <h3>本地文件上传</h3>
        </div>
      </div>

      <div class="upload-zone">
        <input type="file" @change="onFileChange" />
        <p>{{ uploadFile ? uploadFile.name : "选择一个本地文件" }}</p>
      </div>

      <div class="form-stack">
        <input
          :value="uploadTitle"
          placeholder="文件标题"
          @input="onTitleInput"
        />
        <input
          :value="uploadOccurredAt"
          placeholder="occurred_at"
          @input="onOccurredAtInput"
        />
      </div>

      <button class="primary-button" :disabled="busy" @click="emit('submit-upload')">
        上传文件
      </button>
    </article>
  </section>
</template>
