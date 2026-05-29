// vite.config.mts
import { basename } from "path";
import fs from "fs";
import { defineConfig, loadEnv } from "file:///usr/src/app/play/node_modules/vite/dist/node/index.js";
import { svelte } from "file:///usr/src/app/play/node_modules/@sveltejs/vite-plugin-svelte/src/index.js";
import { sveltePreprocess } from "file:///usr/src/app/play/node_modules/svelte-preprocess/dist/index.js";
import { sentryVitePlugin } from "file:///usr/src/app/node_modules/@sentry/vite-plugin/dist/esm/index.mjs";
import Icons from "file:///usr/src/app/node_modules/unplugin-icons/dist/vite.js";
import tsconfigPaths from "file:///usr/src/app/play/node_modules/vite-tsconfig-paths/dist/index.mjs";
import { nodePolyfills } from "file:///usr/src/app/node_modules/vite-plugin-node-polyfills/dist/index.js";
var vite_config_default = defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const config = {
    server: {
      host: "0.0.0.0",
      port: 8080,
      allowedHosts: true,
      hmr: {
        // workaround for development in docker
        clientPort: 80
      },
      watch: {
        ignored: ["./src/pusher"]
      }
    },
    build: {
      sourcemap: env.GENERATE_SOURCEMAP !== "false",
      outDir: "./dist/public",
      rollupOptions: {
        plugins: [mediapipe_workaround()]
        // external: ["@mediapipe/tasks-vision"],
        //plugins: [inject({ Buffer: ["buffer/", "Buffer"] })],
      },
      assetsInclude: ["**/*.tflite", "**/*.wasm"]
    },
    plugins: [
      nodePolyfills({
        include: ["events", "buffer"],
        globals: {
          Buffer: true
        }
      }),
      svelte({
        preprocess: sveltePreprocess(),
        onwarn(warning, defaultHandler) {
          if (warning.code === "a11y-click-events-have-key-events") return;
          if (warning.code === "security-anchor-rel-noreferrer") return;
          if (warning.code === "Unknown at rule @container (css)") return;
          if (warning.message.includes("Unknown at rule @container")) return;
          if (defaultHandler) {
            defaultHandler(warning);
          }
        }
      }),
      Icons({
        compiler: "svelte"
      }),
      tsconfigPaths()
    ],
    resolve: {
      alias: {
        events: "events"
      }
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup/vitest.setup.ts"],
      coverage: {
        all: true,
        include: ["src/*.ts", "src/**/*.ts"],
        exclude: ["src/i18n", "src/enum"]
      }
    },
    optimizeDeps: {
      include: ["olm"],
      exclude: ["svelte-modals"],
      esbuildOptions: {
        define: {
          global: "globalThis"
        }
      }
    }
  };
  if (env.SENTRY_ORG && env.SENTRY_PROJECT && env.SENTRY_AUTH_TOKEN && env.SENTRY_RELEASE && env.SENTRY_ENVIRONMENT) {
    console.info("Sentry plugin enabled");
    config.plugins.push(
      sentryVitePlugin({
        url: env.SENTRY_URL || "https://sentry.io/",
        org: env.SENTRY_ORG,
        project: env.SENTRY_PROJECT,
        // Specify the directory containing build artifacts
        sourcemaps: {
          assets: "./dist/public/**"
        },
        // Auth tokens can be obtained from https://sentry.io/settings/account/api/auth-tokens/
        // and needs the `project:releases` and `org:read` scopes
        authToken: env.SENTRY_AUTH_TOKEN,
        // Optionally uncomment the line below to override automatic release name detection
        release: {
          name: env.SENTRY_RELEASE,
          deploy: {
            env: env.SENTRY_ENVIRONMENT
          },
          finalize: true
        }
      })
    );
  } else {
    console.info("Sentry plugin disabled");
  }
  return config;
});
function mediapipe_workaround() {
  return {
    name: "mediapipe_workaround",
    load(id) {
      if (basename(id) === "selfie_segmentation.js") {
        let code = fs.readFileSync(id, "utf-8");
        code += "exports.SelfieSegmentation = SelfieSegmentation;";
        return { code };
      } else {
        return null;
      }
    }
  };
}
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcubXRzIl0sCiAgInNvdXJjZXNDb250ZW50IjogWyJjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZGlybmFtZSA9IFwiL3Vzci9zcmMvYXBwL3BsYXlcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIi91c3Ivc3JjL2FwcC9wbGF5L3ZpdGUuY29uZmlnLm10c1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vdXNyL3NyYy9hcHAvcGxheS92aXRlLmNvbmZpZy5tdHNcIjtpbXBvcnQgeyBiYXNlbmFtZSB9IGZyb20gXCJwYXRoXCI7XG5pbXBvcnQgZnMgZnJvbSBcImZzXCI7XG5pbXBvcnQgeyBkZWZpbmVDb25maWcsIGxvYWRFbnYgfSBmcm9tIFwidml0ZVwiO1xuaW1wb3J0IHsgc3ZlbHRlIH0gZnJvbSBcIkBzdmVsdGVqcy92aXRlLXBsdWdpbi1zdmVsdGVcIjtcbmltcG9ydCB7IHN2ZWx0ZVByZXByb2Nlc3MgfSBmcm9tIFwic3ZlbHRlLXByZXByb2Nlc3NcIjtcbmltcG9ydCB7IHNlbnRyeVZpdGVQbHVnaW4gfSBmcm9tIFwiQHNlbnRyeS92aXRlLXBsdWdpblwiO1xuaW1wb3J0IEljb25zIGZyb20gXCJ1bnBsdWdpbi1pY29ucy92aXRlXCI7XG5pbXBvcnQgdHNjb25maWdQYXRocyBmcm9tIFwidml0ZS10c2NvbmZpZy1wYXRoc1wiO1xuaW1wb3J0IHsgbm9kZVBvbHlmaWxscyB9IGZyb20gXCJ2aXRlLXBsdWdpbi1ub2RlLXBvbHlmaWxsc1wiO1xuXG4vLyBodHRwczovL3ZpdGVqcy5kZXYvY29uZmlnL1xuZXhwb3J0IGRlZmF1bHQgZGVmaW5lQ29uZmlnKCh7IG1vZGUgfSkgPT4ge1xuICAgIC8vIExvYWQgZW52IGZpbGUgYmFzZWQgb24gYG1vZGVgIGluIHRoZSBjdXJyZW50IHdvcmtpbmcgZGlyZWN0b3J5LlxuICAgIC8vIFNldCB0aGUgdGhpcmQgcGFyYW1ldGVyIHRvICcnIHRvIGxvYWQgYWxsIGVudiByZWdhcmRsZXNzIG9mIHRoZSBgVklURV9gIHByZWZpeC5cbiAgICBjb25zdCBlbnYgPSBsb2FkRW52KG1vZGUsIHByb2Nlc3MuY3dkKCksIFwiXCIpO1xuICAgIGNvbnN0IGNvbmZpZyA9IHtcbiAgICAgICAgc2VydmVyOiB7XG4gICAgICAgICAgICBob3N0OiBcIjAuMC4wLjBcIixcbiAgICAgICAgICAgIHBvcnQ6IDgwODAsXG4gICAgICAgICAgICBhbGxvd2VkSG9zdHM6IHRydWUsXG4gICAgICAgICAgICBobXI6IHtcbiAgICAgICAgICAgICAgICAvLyB3b3JrYXJvdW5kIGZvciBkZXZlbG9wbWVudCBpbiBkb2NrZXJcbiAgICAgICAgICAgICAgICBjbGllbnRQb3J0OiA4MCxcbiAgICAgICAgICAgIH0sXG4gICAgICAgICAgICB3YXRjaDoge1xuICAgICAgICAgICAgICAgIGlnbm9yZWQ6IFtcIi4vc3JjL3B1c2hlclwiXSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICAgIGJ1aWxkOiB7XG4gICAgICAgICAgICBzb3VyY2VtYXA6IGVudi5HRU5FUkFURV9TT1VSQ0VNQVAgIT09IFwiZmFsc2VcIixcbiAgICAgICAgICAgIG91dERpcjogXCIuL2Rpc3QvcHVibGljXCIsXG4gICAgICAgICAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICAgICAgICAgICAgcGx1Z2luczogW21lZGlhcGlwZV93b3JrYXJvdW5kKCldLFxuICAgICAgICAgICAgICAgIC8vIGV4dGVybmFsOiBbXCJAbWVkaWFwaXBlL3Rhc2tzLXZpc2lvblwiXSxcbiAgICAgICAgICAgICAgICAvL3BsdWdpbnM6IFtpbmplY3QoeyBCdWZmZXI6IFtcImJ1ZmZlci9cIiwgXCJCdWZmZXJcIl0gfSldLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIGFzc2V0c0luY2x1ZGU6IFtcIioqLyoudGZsaXRlXCIsIFwiKiovKi53YXNtXCJdLFxuICAgICAgICB9LFxuICAgICAgICBwbHVnaW5zOiBbXG4gICAgICAgICAgICBub2RlUG9seWZpbGxzKHtcbiAgICAgICAgICAgICAgICBpbmNsdWRlOiBbXCJldmVudHNcIiwgXCJidWZmZXJcIl0sXG4gICAgICAgICAgICAgICAgZ2xvYmFsczoge1xuICAgICAgICAgICAgICAgICAgICBCdWZmZXI6IHRydWUsXG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgc3ZlbHRlKHtcbiAgICAgICAgICAgICAgICBwcmVwcm9jZXNzOiBzdmVsdGVQcmVwcm9jZXNzKCksXG4gICAgICAgICAgICAgICAgb253YXJuKHdhcm5pbmcsIGRlZmF1bHRIYW5kbGVyKSB7XG4gICAgICAgICAgICAgICAgICAgIC8vIGRvbid0IHdhcm4gb246XG4gICAgICAgICAgICAgICAgICAgIGlmICh3YXJuaW5nLmNvZGUgPT09IFwiYTExeS1jbGljay1ldmVudHMtaGF2ZS1rZXktZXZlbnRzXCIpIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHdhcm5pbmcuY29kZSA9PT0gXCJzZWN1cml0eS1hbmNob3ItcmVsLW5vcmVmZXJyZXJcIikgcmV0dXJuO1xuICAgICAgICAgICAgICAgICAgICBpZiAod2FybmluZy5jb2RlID09PSBcIlVua25vd24gYXQgcnVsZSBAY29udGFpbmVyIChjc3MpXCIpIHJldHVybjtcbiAgICAgICAgICAgICAgICAgICAgaWYgKHdhcm5pbmcubWVzc2FnZS5pbmNsdWRlcyhcIlVua25vd24gYXQgcnVsZSBAY29udGFpbmVyXCIpKSByZXR1cm47XG5cbiAgICAgICAgICAgICAgICAgICAgLy8gaGFuZGxlIGFsbCBvdGhlciB3YXJuaW5ncyBub3JtYWxseVxuICAgICAgICAgICAgICAgICAgICBpZiAoZGVmYXVsdEhhbmRsZXIpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGRlZmF1bHRIYW5kbGVyKHdhcm5pbmcpO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIH0pLFxuICAgICAgICAgICAgSWNvbnMoe1xuICAgICAgICAgICAgICAgIGNvbXBpbGVyOiBcInN2ZWx0ZVwiLFxuICAgICAgICAgICAgfSksXG4gICAgICAgICAgICB0c2NvbmZpZ1BhdGhzKCksXG4gICAgICAgIF0sXG4gICAgICAgIHJlc29sdmU6IHtcbiAgICAgICAgICAgIGFsaWFzOiB7XG4gICAgICAgICAgICAgICAgZXZlbnRzOiBcImV2ZW50c1wiLFxuICAgICAgICAgICAgfSxcbiAgICAgICAgfSxcbiAgICAgICAgdGVzdDoge1xuICAgICAgICAgICAgZW52aXJvbm1lbnQ6IFwianNkb21cIixcbiAgICAgICAgICAgIGdsb2JhbHM6IHRydWUsXG4gICAgICAgICAgICBzZXR1cEZpbGVzOiBbXCIuL3Rlc3RzL3NldHVwL3ZpdGVzdC5zZXR1cC50c1wiXSxcbiAgICAgICAgICAgIGNvdmVyYWdlOiB7XG4gICAgICAgICAgICAgICAgYWxsOiB0cnVlLFxuICAgICAgICAgICAgICAgIGluY2x1ZGU6IFtcInNyYy8qLnRzXCIsIFwic3JjLyoqLyoudHNcIl0sXG4gICAgICAgICAgICAgICAgZXhjbHVkZTogW1wic3JjL2kxOG5cIiwgXCJzcmMvZW51bVwiXSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICAgIG9wdGltaXplRGVwczoge1xuICAgICAgICAgICAgaW5jbHVkZTogW1wib2xtXCJdLFxuICAgICAgICAgICAgZXhjbHVkZTogW1wic3ZlbHRlLW1vZGFsc1wiXSxcbiAgICAgICAgICAgIGVzYnVpbGRPcHRpb25zOiB7XG4gICAgICAgICAgICAgICAgZGVmaW5lOiB7XG4gICAgICAgICAgICAgICAgICAgIGdsb2JhbDogXCJnbG9iYWxUaGlzXCIsXG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgfTtcblxuICAgIGlmIChlbnYuU0VOVFJZX09SRyAmJiBlbnYuU0VOVFJZX1BST0pFQ1QgJiYgZW52LlNFTlRSWV9BVVRIX1RPS0VOICYmIGVudi5TRU5UUllfUkVMRUFTRSAmJiBlbnYuU0VOVFJZX0VOVklST05NRU5UKSB7XG4gICAgICAgIGNvbnNvbGUuaW5mbyhcIlNlbnRyeSBwbHVnaW4gZW5hYmxlZFwiKTtcbiAgICAgICAgY29uZmlnLnBsdWdpbnMucHVzaChcbiAgICAgICAgICAgIHNlbnRyeVZpdGVQbHVnaW4oe1xuICAgICAgICAgICAgICAgIHVybDogZW52LlNFTlRSWV9VUkwgfHwgXCJodHRwczovL3NlbnRyeS5pby9cIixcbiAgICAgICAgICAgICAgICBvcmc6IGVudi5TRU5UUllfT1JHLFxuICAgICAgICAgICAgICAgIHByb2plY3Q6IGVudi5TRU5UUllfUFJPSkVDVCxcbiAgICAgICAgICAgICAgICAvLyBTcGVjaWZ5IHRoZSBkaXJlY3RvcnkgY29udGFpbmluZyBidWlsZCBhcnRpZmFjdHNcbiAgICAgICAgICAgICAgICBzb3VyY2VtYXBzOiB7XG4gICAgICAgICAgICAgICAgICAgIGFzc2V0czogXCIuL2Rpc3QvcHVibGljLyoqXCIsXG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAvLyBBdXRoIHRva2VucyBjYW4gYmUgb2J0YWluZWQgZnJvbSBodHRwczovL3NlbnRyeS5pby9zZXR0aW5ncy9hY2NvdW50L2FwaS9hdXRoLXRva2Vucy9cbiAgICAgICAgICAgICAgICAvLyBhbmQgbmVlZHMgdGhlIGBwcm9qZWN0OnJlbGVhc2VzYCBhbmQgYG9yZzpyZWFkYCBzY29wZXNcbiAgICAgICAgICAgICAgICBhdXRoVG9rZW46IGVudi5TRU5UUllfQVVUSF9UT0tFTixcbiAgICAgICAgICAgICAgICAvLyBPcHRpb25hbGx5IHVuY29tbWVudCB0aGUgbGluZSBiZWxvdyB0byBvdmVycmlkZSBhdXRvbWF0aWMgcmVsZWFzZSBuYW1lIGRldGVjdGlvblxuICAgICAgICAgICAgICAgIHJlbGVhc2U6IHtcbiAgICAgICAgICAgICAgICAgICAgbmFtZTogZW52LlNFTlRSWV9SRUxFQVNFLFxuICAgICAgICAgICAgICAgICAgICBkZXBsb3k6IHtcbiAgICAgICAgICAgICAgICAgICAgICAgIGVudjogZW52LlNFTlRSWV9FTlZJUk9OTUVOVCxcbiAgICAgICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICAgICAgZmluYWxpemU6IHRydWUsXG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIH0pXG4gICAgICAgICk7XG4gICAgfSBlbHNlIHtcbiAgICAgICAgY29uc29sZS5pbmZvKFwiU2VudHJ5IHBsdWdpbiBkaXNhYmxlZFwiKTtcbiAgICB9XG4gICAgcmV0dXJuIGNvbmZpZztcbn0pO1xuXG4vLyB1c2UgdG8gZml4IHRoZSBidWlsZCBpc3N1ZSB3aXRoIG1lZGlhcGlwZSA9PT4gaHR0cHM6Ly9naXRodWIuY29tL3RlbnNvcmZsb3cvdGZqcy9pc3N1ZXMvNzE2NVxuLy8gVE9ETzogcmVtb3ZlIHRoaXMgd2hlbiB3ZSBtaWdyYXRlIHRvIG1lZGlhcGlwZS90YXNrcy12aXNpb25cbmZ1bmN0aW9uIG1lZGlhcGlwZV93b3JrYXJvdW5kKCkge1xuICAgIHJldHVybiB7XG4gICAgICAgIG5hbWU6IFwibWVkaWFwaXBlX3dvcmthcm91bmRcIixcbiAgICAgICAgbG9hZChpZDogc3RyaW5nKSB7XG4gICAgICAgICAgICBpZiAoYmFzZW5hbWUoaWQpID09PSBcInNlbGZpZV9zZWdtZW50YXRpb24uanNcIikge1xuICAgICAgICAgICAgICAgIGxldCBjb2RlID0gZnMucmVhZEZpbGVTeW5jKGlkLCBcInV0Zi04XCIpO1xuICAgICAgICAgICAgICAgIGNvZGUgKz0gXCJleHBvcnRzLlNlbGZpZVNlZ21lbnRhdGlvbiA9IFNlbGZpZVNlZ21lbnRhdGlvbjtcIjtcbiAgICAgICAgICAgICAgICByZXR1cm4geyBjb2RlIH07XG4gICAgICAgICAgICB9IGVsc2Uge1xuICAgICAgICAgICAgICAgIHJldHVybiBu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
