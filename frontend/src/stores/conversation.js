import { defineStore } from "pinia";

import { api } from "../services/api";

export const useConversationStore = defineStore("conversation", {
  state: () => ({
    sessionId: "",
    mode: "hybrid",
    question: "",
    answer: null,
    turns: [],
    busy: false
  }),
  getters: {
    hasConversation(state) {
      return state.turns.length > 0;
    }
  },
  actions: {
    /**
     * @returns {void}
     */
    resetSession() {
      this.sessionId = "";
      this.question = "";
      this.answer = null;
      this.turns = [];
    },

    /**
     * @returns {Promise<any>}
     */
    async ask() {
      this.busy = true;
      try {
        const response = await api.answerConversation({
          question: this.question,
          session_id: this.sessionId || null,
          search_mode: this.mode,
          limit: 5
        });
        this.answer = response;
        this.turns = response.conversation_turns || [];
        this.sessionId = response.session_id;
        return response;
      } finally {
        this.busy = false;
      }
    }
  }
});
