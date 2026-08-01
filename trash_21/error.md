 Created: src/components/EventStream.tsx
✅ Created: src/components/Timeline.tsx
✅ Created: src/hooks/useLiveGraph.ts
✅ Created: src/App.tsx

🎉 Successfully extracted 40 files into ./buffy-playground
~ $ cd buffy-playground
~/buffy-playground $ npm install

npm warn ERESOLVE overriding peer dependency
npm warn While resolving: buffy-playground@0.1.0
npm warn Found: react@19.2.8
npm warn node_modules/react
npm warn   react@"^18.3.1" from the root project
npm warn   3 more (react-dom, framer-motion, lucide-react)
npm warn
npm warn Could not resolve dependency:
npm warn peer react@"^19.2.8" from react-dom@19.2.8
npm warn node_modules/react-dom
npm warn   react-dom@"^18.3.1" from the root project
npm warn   1 more (framer-motion)

added 141 packages, removed 89 packages, changed 11 packages, and audited 203 packages in 1m

27 packages are looking for funding
  run `npm fund` for details

found 0 vulnerabilities
npm warn allow-scripts 1 package has install scripts not yet covered by allowScripts:
npm warn allow-scripts   esbuild@0.25.12 (postinstall: node install.js)
npm warn allow-scripts
npm warn allow-scripts Run `npm install-scripts ls` to review, or `npm install-scripts approve <pkg>` to allow.
~/buffy-playground $ npm run dev

> buffy-playground@0.1.0 dev
> vite

/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js:121
                throw new Error(
                      ^

Error: Cannot find module @rollup/rollup-android-arm64. npm has a bug related to optional dependencies (https://github.com/npm/cli/issues/4828). Please try `npm i` again after removing both package-lock.json and node_modules directory.
    at requireWithFriendlyError (/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js:121:9)
    at Object.<anonymous> (/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js:130:76)
    at Module._compile (node:internal/modules/cjs/loader:1944:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:2084:10)
    at Module.load (node:internal/modules/cjs/loader:1666:32)
    at Module._load (node:internal/modules/cjs/loader:1447:12)
    at wrapModuleLoad (node:internal/modules/cjs/loader:260:19)
    at loadCJSModuleWithModuleLoad (node:internal/modules/esm/translators:373:15)
    at ModuleWrap.<anonymous> (node:internal/modules/esm/translators:245:9)
    at ModuleJob.run (node:internal/modules/esm/module_job:447:25) {
  [cause***REMOVED***: Error: Cannot find module '@rollup/rollup-android-arm64'
  Require stack:
  - /data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js
      at Module._resolveFilename (node:internal/modules/cjs/loader:1568:15)
      at wrapResolveFilename (node:internal/modules/cjs/loader:1122:27)
      at defaultResolveImplForCJSLoading (node:internal/modules/cjs/loader:1146:10)
      at resolveForCJSWithHooks (node:internal/modules/cjs/loader:1173:12)
      at Module._load (node:internal/modules/cjs/loader:1345:5)
      at wrapModuleLoad (node:internal/modules/cjs/loader:260:19)
      at Module.require (node:internal/modules/cjs/loader:1689:12)
      at require (node:internal/modules/helpers:191:16)
      at requireWithFriendlyError (/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js:103:10)
      at Object.<anonymous> (/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js:130:76) {
    code: 'MODULE_NOT_FOUND',
    requireStack: [
      '/data/data/com.termux/files/home/buffy-playground/node_modules/rollup/dist/native.js'
    ***REMOVED***
  ***REMOVED***
***REMOVED***

Node.js v26.4.0
~/buffy-playground $