import {defineConfig} from "vite";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/postcss";
import {createRequire} from "node:module";
import {dirname,resolve} from "node:path";
const require=createRequire(import.meta.url);
export default defineConfig({
  plugins:[react()],publicDir:"../public",
  resolve:{alias:[
    {find:/^react$/,replacement:require.resolve("react")},
    {find:/^react\/jsx-runtime$/,replacement:require.resolve("react/jsx-runtime")},
    {find:/^react\/jsx-dev-runtime$/,replacement:require.resolve("react/jsx-dev-runtime")},
    {find:/^react-dom\/client$/,replacement:require.resolve("react-dom/client")},
    {find:/^react-dom$/,replacement:require.resolve("react-dom")},
    {find:"lucide-react",replacement:require.resolve("lucide-react")},
    {find:"tailwindcss",replacement:resolve(dirname(require.resolve("tailwindcss/package.json")),"index.css")}
  ]},
  css:{postcss:{plugins:[tailwind()]}},
  build:{outDir:"dist",emptyOutDir:true}
});
