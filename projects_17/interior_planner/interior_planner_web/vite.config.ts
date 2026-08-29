import { defineConfig ***REMOVED*** from 'vite';
***REMOVED***act from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()***REMOVED***,
  resolve: {
    alias: {
      'react-native': 'react-native-web',
    ***REMOVED***,
    extensions: ['.web.tsx', '.web.ts', '.tsx', '.ts', '.jsx', '.js'***REMOVED***,
  ***REMOVED***,
  server: {
    host: '0.0.0.0',
    port: 5173,
  ***REMOVED***,
***REMOVED***);
