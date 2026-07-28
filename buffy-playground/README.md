# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react***REMOVED***(https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc***REMOVED***(https://oxc.rs)
- [@vitejs/plugin-react-swc***REMOVED***(https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC***REMOVED***(https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation***REMOVED***(https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist'***REMOVED***),
  {
    files: ['**/*.{ts,tsx***REMOVED***'***REMOVED***,
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ***REMOVED***,
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'***REMOVED***,
        tsconfigRootDir: import.meta.dirname,
      ***REMOVED***,
      // other options...
    ***REMOVED***,
  ***REMOVED***,
***REMOVED***)

```

You can also install [eslint-plugin-react-x***REMOVED***(https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom***REMOVED***(https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
***REMOVED***actX from 'eslint-plugin-react-x'
***REMOVED***actDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist'***REMOVED***),
  {
    files: ['**/*.{ts,tsx***REMOVED***'***REMOVED***,
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'***REMOVED***,
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ***REMOVED***,
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'***REMOVED***,
        tsconfigRootDir: import.meta.dirname,
      ***REMOVED***,
      // other options...
    ***REMOVED***,
  ***REMOVED***,
***REMOVED***)

```
