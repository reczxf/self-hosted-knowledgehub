import { createRouter, createWebHashHistory } from "vue-router";

import ChatPage from "../views/ChatPage.vue";
import ImportPage from "../views/ImportPage.vue";
import LibraryPage from "../views/LibraryPage.vue";
import OperationsPage from "../views/OperationsPage.vue";

export const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", redirect: "/chat" },
    { path: "/chat", name: "chat", component: ChatPage },
    { path: "/library", name: "library", component: LibraryPage },
    { path: "/operations", name: "operations", component: OperationsPage },
    { path: "/import", name: "import", component: ImportPage }
  ]
});
