import js from '@eslint/js'
import globals from 'globals'
***REMOVED***actHooks from 'eslint-plugin-react-hooks'
***REMOVED***actRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores ***REMOVED*** from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist'***REMOVED***),
  {
    files: ['**/*.{ts,tsx***REMOVED***'***REMOVED***,
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ***REMOVED***,
    languageOptions: {
      globals: globals.browser,
    ***REMOVED***,
  ***REMOVED***,
***REMOVED***)
