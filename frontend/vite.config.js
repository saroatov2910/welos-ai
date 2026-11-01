import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// npm run dev    -> http://localhost:5173 with live reload
// npm run build  -> static files in dist/, which Vercel serves
export default defineConfig({
  plugins: [react()],
});
