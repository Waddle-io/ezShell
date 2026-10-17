import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(__dirname) } },
  test: { environment: "node", testTimeout: 20000, hookTimeout: 20000, fileParallelism: false },
});
