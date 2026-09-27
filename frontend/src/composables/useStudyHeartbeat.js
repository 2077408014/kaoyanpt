import { ref, onMounted, onUnmounted, watch } from "vue";
import { useRoute } from "vue-router";
import { sendHeartbeat, trackStudyEvent } from "../api/study_tracker";
const HEARTBEAT_INTERVAL = 30;
const STUDY_PATHS = [
  "/dashboard/mistakes",
  "/dashboard/recommend",
  "/dashboard/words",
  "/dashboard/ai",
  "/dashboard/resources",
  "/dashboard/report",
  "/dashboard/supervision"
];
function isStudyPath(path) {
  return STUDY_PATHS.some((p) => path === p || path.startsWith(p + "/"));
}
function useStudyHeartbeat() {
  const route = useRoute();
  const isStudying = ref(false);
  const lastTickAt = ref(0);
  const accumulatedSeconds = ref(0);
  let timer = null;
  let stopWatch = null;
  function resetAccumulator() {
    accumulatedSeconds.value = 0;
    lastTickAt.value = Date.now();
  }
  async function flushHeartbeat(force = false) {
    const now = Date.now();
    const elapsed = Math.floor((now - lastTickAt.value) / 1e3);
    lastTickAt.value = now;
    if (elapsed <= 0) return;
    if (!force && elapsed < HEARTBEAT_INTERVAL) {
      accumulatedSeconds.value += elapsed;
      return;
    }
    const total = accumulatedSeconds.value + elapsed;
    accumulatedSeconds.value = 0;
    const seconds = Math.min(total, 30 * 60);
    if (seconds <= 0) return;
    try {
      await sendHeartbeat(seconds);
    } catch {
    }
  }
  function startTicking() {
    if (isStudying.value) return;
    isStudying.value = true;
    lastTickAt.value = Date.now();
    accumulatedSeconds.value = 0;
    timer = window.setInterval(() => {
      flushHeartbeat(false).catch(() => {
      });
    }, HEARTBEAT_INTERVAL * 1e3);
  }
  function stopTicking() {
    if (!isStudying.value) return;
    isStudying.value = false;
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
    flushHeartbeat(true).catch(() => {
    });
  }
  function onVisibilityChange() {
    if (document.hidden) {
      stopTicking();
    } else if (isStudyPath(route.path)) {
      lastTickAt.value = Date.now();
      startTicking();
    }
  }
  function onBeforeUnload() {
    if (!isStudying.value) return;
    const now = Date.now();
    const elapsed = Math.floor((now - lastTickAt.value) / 1e3);
    const total = accumulatedSeconds.value + elapsed;
    const seconds = Math.min(total, 30 * 60);
    if (seconds <= 0) return;
    try {
      const token = localStorage.getItem("token") || "";
      fetch("/api/study/heartbeat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ seconds }),
        keepalive: true
      }).catch(() => {
      });
    } catch {
    }
  }
  async function trackEvent(eventType, count = 1) {
    try {
      await trackStudyEvent(eventType, count);
    } catch {
    }
  }
  function handleRouteChange(to) {
    const path = to.path;
    if (isStudyPath(path)) {
      if (!isStudying.value) {
        resetAccumulator();
        startTicking();
      }
    } else {
      if (isStudying.value) {
        stopTicking();
      }
    }
  }
  onMounted(() => {
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("beforeunload", onBeforeUnload);
    handleRouteChange(route);
    stopWatch = watch(
      () => route.path,
      () => handleRouteChange(route)
    );
  });
  onUnmounted(() => {
    stopTicking();
    document.removeEventListener("visibilitychange", onVisibilityChange);
    window.removeEventListener("beforeunload", onBeforeUnload);
    if (stopWatch) {
      stopWatch();
      stopWatch = null;
    }
  });
  return {
    isStudying,
    trackEvent
  };
}
export {
  useStudyHeartbeat
};
